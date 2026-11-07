"""Edge Camera Client designed for deployment on other laptops/PCs without GPU requirements."""

import getpass
import logging
import os
import socket
import sys
import time
from typing import Any, Dict, Optional, Tuple, Union
from urllib.parse import quote

import cv2
import numpy as np
import requests

try:
    from urbansoc.io.sources import CameraSource, SimulatedSource
except ImportError:
    CameraSource = None  # type: ignore
    SimulatedSource = None  # type: ignore

logger = logging.getLogger("urbansoc.client.edge_client")


def get_auto_camera_id() -> str:
    """Generate an automatic friendly camera ID based on machine hostname."""
    raw_host = socket.gethostname()
    clean_host = "".join(c if c.isalnum() else "_" for c in raw_host).upper().strip("_")
    clean_host = clean_host[:14] if clean_host else "DEVICE"
    return f"LAPTOP_{clean_host}"


def get_auto_camera_name() -> str:
    """Generate an automatic friendly camera name based on system user and machine."""
    try:
        user = getpass.getuser().capitalize()
        return f"Laptop {user} ({socket.gethostname()})"
    except Exception:
        return f"Laptop ({socket.gethostname()})"


class EdgeCameraClient:
    """Lightweight zero-GPU camera client streaming webcam frames to an intermediate AI-SOC server."""

    def __init__(
        self,
        server_url: str = "http://localhost:8000",
        camera_id: Optional[str] = None,
        camera_name: Optional[str] = None,
        camera_index: Union[int, str] = "auto",
        fps: float = 15.0,
        resolution: Tuple[int, int] = (640, 480),
        quality: int = 80,
        lat: float = 10.776889,
        lon: float = 106.700806,
        address: str = "Laptop Client",
        headless: bool = False,
        test_action: Optional[str] = None,
    ) -> None:
        self.server_url = server_url.rstrip("/")
        self.camera_id = camera_id if camera_id else get_auto_camera_id()
        self.camera_name = camera_name if camera_name else get_auto_camera_name()
        self.camera_index = camera_index
        self.fps = fps
        self.resolution = resolution
        self.quality = max(20, min(100, quality))
        self.lat = lat
        self.lon = lon
        self.address = address
        self.headless = headless
        self.test_action = test_action

        self._running = False
        self._source = None
        self._cap: Optional[cv2.VideoCapture] = None
        self._simulated = False
        self.frame_count = 0
        self.latest_server_result: Optional[Dict[str, Any]] = None

        self._init_source()

    def _init_source(self) -> None:
        """Initialize physical camera capture with auto-probing or fallback to synthetic diagnostic stream."""
        target_idx: Union[int, str] = self.camera_index
        if isinstance(target_idx, str) and target_idx.lower() == "auto":
            target_idx = 0

        # 1. Try CameraSource queue grabber if available
        if CameraSource is not None:
            try:
                source = CameraSource(
                    camera_index=target_idx,
                    resolution=self.resolution,
                    fps=self.fps,
                )
                if not getattr(source, "is_simulated", False):
                    self._source = source
                    logger.info("Opened physical CameraSource on device index '%s'", target_idx)
                    return
            except Exception as e:
                logger.warning("CameraSource initialization failed: %s", e)

        # 2. Try direct OpenCV VideoCapture on target index
        try:
            int_idx = int(target_idx) if str(target_idx).isdigit() else target_idx
            cap = cv2.VideoCapture(int_idx)
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
                    self._cap = cap
                    logger.info("Direct cv2.VideoCapture successfully opened physical webcam on index %s", int_idx)
                    return
                cap.release()
        except Exception as e:
            logger.warning("Direct VideoCapture error: %s", e)

        # 3. If target was 0 or auto and failed, auto-probe alternative camera indices [1, 2]
        if str(self.camera_index).lower() in ("0", "auto"):
            for alt_idx in [1, 2]:
                try:
                    cap = cv2.VideoCapture(alt_idx)
                    if cap.isOpened():
                        ret, _ = cap.read()
                        if ret:
                            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
                            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
                            self._cap = cap
                            logger.info("Auto-detected alternative physical webcam at index %d", alt_idx)
                            return
                        cap.release()
                except Exception:
                    pass

        logger.info("No physical optical webcam sensor available on this machine. Using synthetic simulation stream.")
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
            "X-Camera-Name": quote(str(self.camera_name)),
            "X-Timestamp-Ms": str(timestamp_ms),
            "Content-Length": str(len(raw_bytes)),
        }
        if self.test_action:
            headers["X-Test-Action"] = str(self.test_action)

        resp = requests.post(url, data=raw_bytes, headers=headers, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
        logger.warning("Server responded with HTTP %d: %s", resp.status_code, resp.text)
        return None

    def _draw_client_hud(self, frame: np.ndarray, current_fps: float) -> np.ndarray:
        """Render standard real-time Urban Safety AI-SOC HUD overlay onto local camera feed."""
        display = frame.copy()
        h, w = display.shape[:2]
        res = self.latest_server_result

        threat = res.get("highest_threat", "LOW") if res else "STANDBY"
        action = res.get("primary_action", "NORMAL") if res else "CONNECTING"
        score = res.get("highest_threat_score", 0.0) if res else 0.0
        humans = res.get("human_count", 0) if res else 0

        threat_colors = {
            "LOW": (70, 180, 50),       # Green
            "MEDIUM": (30, 160, 240),    # Amber
            "HIGH": (20, 100, 240),      # Orange
            "CRITICAL": (40, 40, 230),   # Red
        }
        banner_color = threat_colors.get(threat, (100, 100, 100))

        # 1. Top HUD Header Bar
        top_bar_h = 42
        overlay = display.copy()
        cv2.rectangle(overlay, (0, 0), (w, top_bar_h), (15, 20, 30), -1)
        cv2.rectangle(overlay, (0, top_bar_h - 3), (w, top_bar_h), banner_color, -1)
        cv2.addWeighted(overlay, 0.78, display, 0.22, 0, display)

        title = f"AI-SOC CLIENT | {self.camera_id}: {self.camera_name}"
        cv2.putText(display, title, (12, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2, cv2.LINE_AA)

        badge = f"{threat} | {action} ({current_fps:.1f} FPS)"
        cv2.putText(display, badge, (max(12, w - 320), 26), cv2.FONT_HERSHEY_SIMPLEX, 0.55, banner_color, 2, cv2.LINE_AA)

        # 2. Bottom Status Bar
        bot_bar_h = 28
        overlay = display.copy()
        cv2.rectangle(overlay, (0, h - bot_bar_h), (w, h), (10, 15, 25), -1)
        cv2.addWeighted(overlay, 0.82, display, 0.18, 0, display)

        bot_text = f"Server: {self.server_url} | Frame #{self.frame_count} | Humans: {humans} | [q]: Thoat | [s]: Chup anh"
        cv2.putText(display, bot_text, (10, h - 9), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (180, 200, 220), 1, cv2.LINE_AA)
        return display

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
                        self.latest_server_result = result
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
                inst_fps = frames_since_log / max(0.001, now - last_log_time) if frames_since_log > 0 else self.fps
                if now - last_log_time >= 5.0:
                    print(
                        f"📡 [{self.camera_id}] Streaming active: Frame #{self.frame_count} | ~{inst_fps:.1f} FPS -> {self.server_url}",
                        flush=True,
                    )
                    last_log_time = now
                    frames_since_log = 0

                # Local GUI camera window with SOC HUD overlay
                if not self.headless:
                    hud_frame = self._draw_client_hud(frame, inst_fps)
                    window_title = f"Urban Safety AI-SOC - Camera [{self.camera_id}]"
                    try:
                        cv2.imshow(window_title, hud_frame)
                        key = cv2.waitKey(1) & 0xFF
                        if key == 27 or key == ord("q"):
                            print(f"\nUser requested shutdown on client '{self.camera_id}'.")
                            break
                        elif key == ord("s"):
                            snap_dir = os.path.join("output", "snapshots")
                            os.makedirs(snap_dir, exist_ok=True)
                            snap_path = os.path.join(snap_dir, f"snapshot_{self.camera_id}_{int(time.time())}.jpg")
                            cv2.imwrite(snap_path, hud_frame)
                            print(f"\n📸 [SNAPSHOT SAVED]: {snap_path}")
                    except cv2.error as e:
                        # Fallback to headless if no X11/Wayland display server is available
                        self.headless = True
                        logger.info("Running in headless terminal mode (display server unavailable: %s)", e)

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
