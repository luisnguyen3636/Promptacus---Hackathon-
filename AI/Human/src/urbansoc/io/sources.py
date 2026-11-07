"""Video ingestion sources supporting real-time camera, video files, and simulated fallback."""

import logging
import platform
import queue
import threading
import time
from typing import Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger("urbansoc.io.sources")


class SimulatedSource:
    """Simulated camera source providing a diagnostic synthetic grid canvas when no hardware webcam is present."""

    def __init__(self, resolution: Tuple[int, int] = (640, 480), fps: float = 20.0) -> None:
        self.width, self.height = resolution
        self.fps = fps
        self._frame_count = 0

    def read(self) -> Tuple[bool, np.ndarray]:
        """Generate a simulated frame with moving timestamp indicator."""
        frame = np.full((self.height, self.width, 3), 35, dtype=np.uint8)

        # Draw grid
        grid_color = (45, 45, 50)
        for x in range(0, self.width, 40):
            cv2.line(frame, (x, 0), (x, self.height), grid_color, 1)
        for y in range(0, self.height, 40):
            cv2.line(frame, (0, y), (self.width, y), grid_color, 1)

        # Synthetic banner text
        text = "SIMULATED CAMERA STREAM - NO PHYSICAL WEBCAM ATTACHED"
        cv2.putText(
            frame,
            text,
            (25, self.height // 2 - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (0, 180, 255),
            1,
            cv2.LINE_AA,
        )

        sub_text = "Operating in resilient fallback mode (CD-05)"
        cv2.putText(
            frame,
            sub_text,
            (25, self.height // 2 + 15),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.40,
            (180, 180, 180),
            1,
            cv2.LINE_AA,
        )

        self._frame_count += 1
        time.sleep(1.0 / self.fps)
        return True, frame

    def release(self) -> None:
        """No-op for simulated source."""
        pass


class CameraSource:
    """Non-blocking physical camera capture source with a background grabber thread (AGENTS.md CD-05)."""

    def __init__(
        self,
        camera_index: int = 0,
        resolution: Tuple[int, int] = (640, 480),
        fps: float = 20.0,
    ) -> None:
        self.camera_index = camera_index
        self.requested_resolution = resolution
        self.fps = fps
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_simulated = False
        self.simulated_source: Optional[SimulatedSource] = None

        self._queue: queue.Queue = queue.Queue(maxsize=2)
        self._stop_event = threading.Event()
        self._grabber_thread: Optional[threading.Thread] = None

        self._init_camera()

    def _init_camera(self) -> None:
        req_w, req_h = self.requested_resolution

        # On Windows, try DirectShow (CAP_DSHOW) first for fast webcam initialization
        if platform.system() == "Windows":
            try:
                self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
            except Exception as e:
                logger.warning("DirectShow camera open failed: %s, falling back to default API", e)
                self.cap = cv2.VideoCapture(self.camera_index)
        else:
            self.cap = cv2.VideoCapture(self.camera_index)

        if not self.cap or not self.cap.isOpened():
            logger.warning("Could not open physical camera %s. Activating SimulatedSource fallback.", self.camera_index)
            self.is_simulated = True
            self.simulated_source = SimulatedSource(self.requested_resolution, self.fps)
            self.frame_size = self.requested_resolution
            return

        # Attempt to set camera properties
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, req_w)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, req_h)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)

        actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if actual_w <= 0 or actual_h <= 0:
            actual_w, actual_h = req_w, req_h
        self.frame_size = (actual_w, actual_h)

        # Start non-blocking grabber worker thread
        self._stop_event.clear()
        self._grabber_thread = threading.Thread(target=self._grab_worker, daemon=True)
        self._grabber_thread.start()

    def _grab_worker(self) -> None:
        """Background thread constantly grabbing the latest frame and dropping older frames to prevent queue lag."""
        while not self._stop_event.is_set():
            if not self.cap or not self.cap.isOpened():
                break
            ret, frame = self.cap.read()
            if not ret or frame is None:
                time.sleep(0.01)
                continue

            # Drop oldest frame if queue full to guarantee freshest real-time feed
            if self._queue.full():
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    pass

            try:
                self._queue.put_nowait(frame)
            except queue.Full:
                pass

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Retrieve the latest frame from the non-blocking queue or fallback simulator."""
        if self.is_simulated and self.simulated_source:
            return self.simulated_source.read()

        try:
            frame = self._queue.get(timeout=0.2)
            return True, frame
        except queue.Empty:
            # If camera opened but buffer temporarily empty, grab synchronously once
            if self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                return ret, frame
            return False, None

    def release(self) -> None:
        """Stop grabber thread and release video capture."""
        self._stop_event.set()
        if self._grabber_thread and self._grabber_thread.is_alive():
            self._grabber_thread.join(timeout=0.5)

        if self.cap and self.cap.isOpened():
            self.cap.release()

        if self.simulated_source:
            self.simulated_source.release()
