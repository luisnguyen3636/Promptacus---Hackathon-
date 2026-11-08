"""
Non-blocking Alert Dispatcher Client for Urban Safety AI-SOC.
Monitors behavioral detections, identifies suspicious actions, packages metadata & images,
and asynchronously dispatches HTTP requests to the AI Alert Server.
"""

import os
import sys
import time
import json
import base64
import logging
import threading
import queue
import urllib.request
import urllib.error
from typing import Optional, Dict, Any, List, Tuple, Callable
from datetime import datetime

import cv2
import numpy as np

from alert_models import SuspiciousActionRequest, AlertRecord
from ai_service import AIService
from rate_limiter import AIRateLimitExceededError

logger = logging.getLogger("urbansoc.alert_client")


class AlertDispatcher:
    """
    Asynchronous Alert Dispatcher Client.
    Safely dispatches suspicious action alerts to the AI Alert Server in the background
    without stalling or blocking the real-time camera/detector frame loop.
    """

    def __init__(
        self,
        server_url: Optional[str] = None,
        camera_id: Optional[str] = None,
        camera_name: Optional[str] = None,
        location: Optional[str] = None,
        cooldown_seconds: float = 3.0,
        output_dir: str = "output",
        enabled: bool = True,
        on_alert_received: Optional[Callable[[Dict[str, Any]], None]] = None,
        ai_service: Optional[AIService] = None,
    ) -> None:
        self.server_url = (
            server_url
            or os.getenv("ALERT_SERVER_URL")
            or "http://127.0.0.1:8000/api/incident"
        ).rstrip("/")

        self.camera_id = camera_id or os.getenv("CAMERA_ID", "CAM_01")
        self.camera_name = camera_name or os.getenv("CAMERA_NAME", "Surveillance Sector")
        self.location = location or os.getenv("CAMERA_LOCATION", "Zone A - Smart City")
        self.cooldown_seconds = cooldown_seconds
        self.output_dir = output_dir
        self.enabled = enabled
        self.on_alert_received = on_alert_received

        # Dedicated AI Service (Rate-limited to 40 req/min) generating alert information before endpoint dispatch
        self.ai_service = ai_service or AIService(output_dir=self.output_dir)

        os.makedirs(self.output_dir, exist_ok=True)
        self.client_log_file = os.path.join(self.output_dir, "received_alerts.jsonl")

        # Track Cooldown State: (track_id, action) -> last_dispatched_timestamp
        self._last_dispatch_time: Dict[Tuple[int, str], float] = {}
        self._lock = threading.Lock()

        # Background Queue & Worker Thread
        self._queue: queue.Queue = queue.Queue(maxsize=50)
        self._stop_event = threading.Event()
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True, name="AlertDispatcherWorker")
        self._worker_thread.start()

        self.last_dispatched_alert: Optional[Dict[str, Any]] = None

    def is_suspicious(self, action: str, threat_level: str, threat_score: float) -> bool:
        """Determines if a detected action or state qualifies as suspicious."""
        act = action.strip().upper()
        tl = threat_level.strip().upper()
        if act in ("FALLEN", "FIGHTING", "HANDS_UP", "RUNNING", "CROUCHING", "LOITERING", "WEAPON_THREAT"):
            return True
        if act != "NORMAL" and act != "WALKING" and act != "SITTING":
            return True
        if tl in ("MEDIUM", "HIGH", "CRITICAL") or threat_score >= 0.45:
            return True
        return False

    def notify_detection(
        self,
        frame: np.ndarray,
        track_id: int,
        action: str,
        threat_level: str,
        threat_score: float,
        bbox: Tuple[int, int, int, int],
        kinematics: Optional[Dict[str, float]] = None,
        notes: Optional[str] = None
    ) -> bool:
        """
        Called on every frame/detection.
        If the action is suspicious and passes cooldown, packages it and puts it onto background dispatch queue.
        Returns True if enqueued, False otherwise.
        """
        if not self.enabled:
            return False

        if not self.is_suspicious(action, threat_level, threat_score):
            return False

        now = time.time()
        cooldown_key = (track_id, action.strip().upper())

        with self._lock:
            last_time = self._last_dispatch_time.get(cooldown_key, 0.0)
            if (now - last_time) < self.cooldown_seconds:
                # Still within cooldown for this track and action
                return False
            self._last_dispatch_time[cooldown_key] = now

        # Encode image frame to JPEG in memory
        try:
            # Crop around the human or send full frame
            h, w, _ = frame.shape
            x1, y1, x2, y2 = [int(v) for v in bbox]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)

            # We create an annotated copy showing bounding box and action tag for clarity
            send_frame = frame.copy()
            cv2.rectangle(send_frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
            cv2.putText(
                send_frame,
                f"ALERT: {action} (ID #{track_id})",
                (x1, max(15, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (0, 0, 255),
                2
            )

            success, encoded_jpg = cv2.imencode(".jpg", send_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if not success:
                logger.warning("Could not encode frame to JPEG for alert dispatch.")
                return False

            image_b64 = base64.b64encode(encoded_jpg.tobytes()).decode("utf-8")
        except Exception as e:
            logger.error("Error preparing frame image for alert: %s", e)
            return False

        now_dt = datetime.utcnow()
        request = SuspiciousActionRequest(
            camera_id=self.camera_id,
            camera_name=self.camera_name,
            timestamp=now_dt.isoformat() + "Z",
            timestamp_ms=int(now_dt.timestamp() * 1000),
            track_id=track_id,
            action=action,
            threat_level=threat_level,
            threat_score=threat_score,
            bbox=[x1, y1, x2, y2],
            kinematics=kinematics or {},
            image_base64=image_b64,
            location=self.location,
            notes=notes
        )

        try:
            self._queue.put_nowait(request)
            return True
        except queue.Full:
            logger.warning("Alert dispatch queue full, dropping alert to prevent backpressure.")
            return False

    def _worker_loop(self) -> None:
        """Background worker thread: AI generates incident info from camera detection, then sends to endpoint."""
        while not self._stop_event.is_set():
            try:
                request: SuspiciousActionRequest = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue

            try:
                # 1. AI evaluates camera detection and generates the incident information (Rate-limited: 40 req/min)
                try:
                    alert_record: AlertRecord = self.ai_service.process_suspicious_action(request)
                except AIRateLimitExceededError as rle:
                    logger.warning(
                        "🚨 [AI RATE LIMIT: 40 REQ/MIN] Rate limit exceeded for AI analysis. Skipping request. Retry after %.1fs.",
                        rle.retry_after
                    )
                    continue

                # 2. After AI generates the incident information, send it to the endpoint (/api/incident)
                self._dispatch_ai_generated_alert(alert_record)

            except Exception as e:
                logger.warning("Failed in alert processing/dispatching to %s: %s", self.server_url, e)
            finally:
                self._queue.task_done()

    def _dispatch_ai_generated_alert(self, alert_record: AlertRecord) -> Optional[Dict[str, Any]]:
        """Sends the AI-generated Alert JSON to the /api/incident endpoint."""
        alert_dict = alert_record.to_dict()
        req_data = json.dumps(alert_dict, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            self.server_url,
            data=req_data,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "X-Camera-ID": alert_record.metadata.get("camera_id", self.camera_id),
                "X-Generated-By": "AI-VLM-Agent"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=8.0) as resp:
                resp_bytes = resp.read()
                resp_json = json.loads(resp_bytes.decode("utf-8"))

                self.last_dispatched_alert = alert_dict

                # Save received alert locally
                try:
                    with open(self.client_log_file, "a", encoding="utf-8") as f:
                        f.write(json.dumps(alert_dict, ensure_ascii=False) + "\n")
                except Exception:
                    pass

                logger.info(
                    "🚀 [DISPATCHED AI ALERT TO ENDPOINT] ID: %s | Action: %s | Severity: %s | Hash: %s... -> %s",
                    alert_record.alert_id,
                    alert_record.action_type,
                    alert_record.severity,
                    str(alert_record.hash)[:12],
                    self.server_url
                )

                if self.on_alert_received:
                    try:
                        self.on_alert_received(alert_dict)
                    except Exception as cb_err:
                        logger.error("Error in on_alert_received callback: %s", cb_err)

                return resp_json

        except urllib.error.URLError as e:
            logger.warning("Could not reach endpoint at %s: %s (Is server.py running?)", self.server_url, e)
            return None
        except Exception as e:
            logger.error("Error dispatching alert to endpoint: %s", e)
            return None

    def close(self) -> None:
        """Stops the worker thread cleanly."""
        self._stop_event.set()
        if self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2.0)
