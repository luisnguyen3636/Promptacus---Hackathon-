"""Edge Camera Client designed for deployment on other laptops/PCs without GPU requirements."""

import logging
import os
import sys
import time
from typing import Any, Dict, Optional, Tuple, Union

import cv2
import numpy as np
import requests

try:
    from urbansoc.io.sources import CameraSource, SimulatedSource
except ImportError:
    CameraSource = None  # type: ignore
    SimulatedSource = None  # type: ignore

logger = logging.getLogger("urbansoc.client.edge_client")


class EdgeCameraClient:
    """Lightweight zero-GPU camera client streaming webcam frames to an intermediate AI-SOC server."""

    def __init__(
        self,
        server_url: str = "http://localhost:8000",
        camera_id: str = "LAPTOP_01",
        camera_name: str = "Laptop Client 01",
        camera_index: Union[int, str] = 0,
        fps: float = 15.0,
        resolution: Tuple[int, int] = (640, 480),
        quality: int = 80,
        lat: float = 10.776889,
        lon: float = 106.700806,
        address: str = "Laptop Client",
        headless: bool = False,
    ) -> None:
        self.server_url = server_url.rstrip("/")
        self.camera_id = camera_id
        self.camera_name = camera_name
        self.camera_index = camera_index
        self.fps = fps
        self.resolution = resolution
        self.quality = max(20, min(100, quality))
        self.lat = lat
        self.lon = lon
        self.address = address
        self.headless = headless

        self._running = False
        self._source = None
        self._cap: Optional[cv2.VideoCapture] = None
        self._simulated = False
        self.frame_count = 0

        self._init_source()

    def _init_source(self) -> None:
        """Initialize physical camera capture or fallback to synthetic diagnostic stream."""
        if CameraSource is not None:
            try:
                self._source = CameraSource(
                    camera_index=self.camera_index,
                    resolution=self.resolution,
                    fps=self.fps,
                )
                logger.info("Initialized CameraSource for device index '%s'", self.camera_index)
                return
            except Exception as e:
                logger.warning("CameraSource initialization failed: %s. Using direct OpenCV fallback.", e)

        # Direct OpenCV capture fallback
        try:
            target = int(self.camera_index) if str(self.camera_index).isdigit() else self.camera_index
            self._cap = cv2.VideoCapture(target)
            if self._cap.isOpened():
                self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
                self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
                logger.info("Direct cv2.VideoCapture opened on index %s", target)
                return
        except Exception as e:
            logger.warning("Direct VideoCapture failed: %s", e)

        logger.info("No physical webcam available. Using synthetic simulation stream.")
        self._simulated = True

    def _read_frame(self) -> Tuple[bool, np.ndarray]:
        """Read next frame from CameraSource, OpenCV cap, or synthetic generator."""
        if self._source is not None:
            return self._source.read()

        if self._cap is not None and self._cap.isOpened():
            ret, frame = self._cap.read()
            if ret and frame is not None:
                if (frame.shape[1], frame.shape[0]) != self.resolution:
                    frame = cv2.resize(frame, self.resolution)
                return True, frame

        # Synthetic generator fallback
        w, h = self.resolution
        frame = np.full((h, w, 3), 30, dtype=np.uint8)
        # Grid lines
        for x in range(0, w, 40):
            cv2.line(frame, (x, 0), (x, h), (45, 45, 50), 1)
        for y in range(0, h, 40):
            cv2.line(frame, (0, y), (w, y), (45, 45, 50), 1)

        cv2.putText(
            frame,
            f"CLIENT FEED: {self.camera_id} [{self.camera_name}]",
            (20, h // 2 - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 200, 255),
            1,
            cv2.LINE_AA,
        )
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(
            frame,
            f"Time: {now_str} | Frame: {self.frame_count}",
            (20, h // 2 + 15),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (180, 180, 180),
            1,
            cv2.LINE_AA,
        )
        time.sleep(1.0 / max(1.0, self.fps))
        return True, frame

    def register(self, timeout: float = 3.0) -> bool:
        """Register camera profile and GPS metadata with central inference server."""
        url = f"{self.server_url}/api/v1/cameras/register"
        payload = {
            "camera_id": self.camera_id,
            "name": self.camera_name,
            "latitude": self.lat,
            "longitude": self.lon,
            "address": self.address,
            "fps": self.fps,
        }
        try:
            resp = requests.post(url, json=payload, timeout=timeout)
            if resp.status_code == 200:
                logger.info("Successfully registered camera '%s' with server at %s", self.camera_id, url)
                return True
            logger.warning("Server returned status %d on camera registration: %s", resp.status_code, resp.text)
            return False
        except Exception as e:
            logger.warning("Failed to register with server (%s): %s", url, e)
            return False

    def send_frame(self, frame_bgr: np.ndarray, timestamp_ms: int, timeout: float = 2.0) -> Optional[Dict[str, Any]]:
        """Encode raw frame to JPEG binary and send via HTTP POST to intermediate server."""
        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), self.quality]
        success, encoded_jpeg = cv2.imencode(".jpg", frame_bgr, encode_params)
        if not success:
            logger.error("Failed to compress frame to JPEG")
            return None

        raw_bytes = encoded_jpeg.tobytes()
        url = f"{self.server_url}/api/v1/ingest/frame"
        headers = {
            "Content-Type": "image/jpeg",
            "X-Camera-ID": self.camera_id,
            "X-Camera-Name": self.camera_name,
            "X-Timestamp-Ms": str(timestamp_ms),
            "Content-Length": str(len(raw_bytes)),
        }

        resp = requests.post(url, data=raw_bytes, headers=headers, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
        logger.warning("Server responded with HTTP %d: %s", resp.status_code, resp.text)
        return None

    def stream_loop(self, max_frames: Optional[int] = None) -> None:
        """Continuous streaming loop sending camera frames to server."""
        self._running = True
        logger.info(
            "Starting streaming loop for camera '%s' -> %s (Target FPS: %.1f)",
            self.camera_id,
            self.server_url,
            self.fps,
        )

        # Attempt initial registration
        self.register()

        frame_interval = 1.0 / max(1.0, self.fps)
        last_log_time = time.time()
        frames_since_log = 0

        try:
            while self._running:
                loop_start = time.time()
                ret, frame = self._read_frame()
                if not ret or frame is None:
                    time.sleep(0.05)
                    continue

                self.frame_count += 1
                frames_since_log += 1
                now_ms = int(time.time() * 1000)

                # Send frame to server
                try:
                    result = self.send_frame(frame, now_ms)
                    if result:
                        threat = result.get("highest_threat", "LOW")
                        action = result.get("primary_action", "NORMAL")
                        humans = result.get("human_count", 0)
                        if threat in ("HIGH", "CRITICAL"):
                            print(f"\r🚨 [{self.camera_id}] ALERT: {threat} | Action: {action} | Humans: {humans}", flush=True)
                except requests.exceptions.RequestException as e:
                    # Non-fatal connection drop: retry next frame
                    if frames_since_log % 30 == 0:
                        logger.warning("Server connection error: %s (retrying...)", e)

                # Log periodic status
                now = time.time()
                if now - last_log_time >= 5.0:
                    inst_fps = frames_since_log / (now - last_log_time)
                    print(
                        f"📡 [{self.camera_id}] Streaming active: Frame #{self.frame_count} | ~{inst_fps:.1f} FPS -> {self.server_url}",
                        flush=True,
                    )
                    last_log_time = now
                    frames_since_log = 0

                # Local GUI preview
                if not self.headless:
                    cv2.imshow(f"UrbanSOC Edge Camera Client - {self.camera_id}", frame)
                    key = cv2.waitKey(1) & 0xFF
                    if key == 27 or key == ord("q"):
                        print(f"\nUser requested shutdown on client '{self.camera_id}'.")
                        break

                if max_frames is not None and self.frame_count >= max_frames:
                    break

                elapsed = time.time() - loop_start
                sleep_time = frame_interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

        except KeyboardInterrupt:
            print(f"\nCtrl+C detected. Stopping client '{self.camera_id}'...")
        finally:
            self.stop()

    def stop(self) -> None:
        """Release camera hardware and close all OpenCV display windows."""
        self._running = False
        if self._source is not None:
            self._source.release()
            self._source = None
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        if not self.headless:
            try:
                cv2.destroyAllWindows()
            except Exception:
                pass
        logger.info("Client '%s' stopped cleanly.", self.camera_id)
