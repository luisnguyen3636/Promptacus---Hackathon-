"""Multi-tenant Intermediate AI Inference Server for distributed multi-laptop camera networks."""

import base64
import json
import logging
import os
import socket
import threading
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn
from typing import Any, Dict, Optional, Tuple
from urllib.parse import unquote

import cv2
import numpy as np

from urbansoc.ai.nvidia_vlm import NvidiaVisionClient
from urbansoc.detection.yolo_pose import YOLOPoseDetector
from urbansoc.domain.webhook_models import CameraLocationConfig
from urbansoc.server.camera_context import CameraContext, CameraContextManager
from urbansoc.telemetry.webhook_dispatcher import WebhookDispatcher, compute_forensic_sha256

logger = logging.getLogger("urbansoc.server.inference_server")


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Multi-threaded HTTP server allowing concurrent frame ingestion from multiple laptops."""

    daemon_threads = True
    allow_reuse_address = True


class SOCMultiCameraHandler(SimpleHTTPRequestHandler):
    """HTTP Request Handler servicing camera registration, frame ingestion, webhooks, and SOC dashboard."""

    soc_server: "InferenceServer"

    @property
    def soc(self) -> "InferenceServer":
        """Access the parent InferenceServer instance."""
        return getattr(self, "soc_server", None) or getattr(self.server, "inference_server", None)

    def do_GET(self) -> None:
        """Route GET requests: SOC dashboard, camera status API, and live camera snapshots."""
        clean_path = self.path.split("?")[0].rstrip("/")

        # 1. API: List all camera contexts and real-time status
        if clean_path == "/api/v1/cameras":
            self._handle_get_cameras()
            return

        # 1b. Real-time HTTP MJPEG Camera Streaming (/api/v1/cameras/{camera_id}/stream or /stream.mjpg)
        if clean_path.startswith("/api/v1/cameras/") and (clean_path.endswith("/stream") or clean_path.endswith("/stream.mjpg")):
            parts = clean_path.split("/")
            if len(parts) >= 5:
                camera_id = parts[4]
                self._handle_get_camera_mjpeg_stream(camera_id)
                return

        if clean_path in ("/stream.mjpg", "/stream", "/live"):
            self._handle_get_camera_mjpeg_stream(None)
            return

        # 2. API: Get latest live visual snapshot for a specific camera
        if clean_path.startswith("/api/v1/cameras/") and clean_path.endswith("/snapshot"):
            parts = clean_path.split("/")
            if len(parts) >= 5:
                camera_id = parts[4]
                self._handle_get_camera_snapshot(camera_id)
                return

        # 2b. API: Get incident full frame or hand crop image for external AI / DeepSeek
        if clean_path.startswith("/api/v1/incidents/") and (clean_path.endswith(".jpg") or clean_path.endswith(".jpeg")):
            self._handle_get_incident_image(clean_path)
            return

        # 3. Root API information (Camera server endpoints & status)
        if clean_path in ("", "/", "/dashboard"):
            self._handle_get_root_info()
            return

        # Fallback to standard file serving
        super().do_GET()

    def do_POST(self) -> None:
        """Route POST requests: camera registration, binary frame ingestion, NVIDIA VLM analysis, and incident webhooks."""
        clean_path = self.path.split("?")[0].rstrip("/")

        if clean_path == "/api/v1/cameras/register":
            self._handle_register_camera()
            return

        if clean_path == "/api/v1/ingest/frame":
            self._handle_ingest_frame()
            return

        if clean_path in ("/api/v1/analyze/nvidia", "/api/v1/analyze"):
            self._handle_nvidia_analyze()
            return

        # Incident webhook reception endpoint (compatible with server.py)
        if clean_path in ("/api/v1/incidents", ""):
            self._handle_incident_webhook()
            return

        self._send_json_response(404, {"status": "error", "message": f"Endpoint '{clean_path}' not found."})

    def _handle_get_incident_image(self, clean_path: str) -> None:
        """Serve incident full frame or hand crop JPEG image for DeepSeek VLM consumption."""
        parts = clean_path.split("/")
        if len(parts) >= 6:
            event_id = parts[4]
            filename = parts[5]
            save_dir = os.path.abspath(os.path.join(self.soc.output_dir, "received_webhooks"))
            target_file = None
            if "hand" in filename:
                target_file = os.path.join(save_dir, f"{event_id}_hand_crop.jpg")
            else:
                target_file = os.path.join(save_dir, f"{event_id}_full_frame.jpg")

            if target_file and os.path.exists(target_file):
                try:
                    with open(target_file, "rb") as f:
                        img_bytes = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "image/jpeg")
                    self.send_header("Content-Length", str(len(img_bytes)))
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(img_bytes)
                    return
                except Exception:
                    pass

        self._send_json_response(404, {"status": "error", "message": f"Incident image not found: {clean_path}"})

    def _handle_get_cameras(self) -> None:
        """Return JSON status of all registered cameras."""
        contexts = self.soc.context_manager.get_all_contexts()
        cameras_list = [ctx.get_status_dict() for ctx in contexts.values()]
        self._send_json_response(200, {"status": "success", "count": len(cameras_list), "cameras": cameras_list})

    def _handle_get_camera_snapshot(self, camera_id: str) -> None:
        """Return latest JPEG annotated frame for the given camera."""
        ctx = self.soc.context_manager.get(camera_id)
        frame_to_serve: Optional[np.ndarray] = None

        if ctx is not None:
            with ctx._lock:
                if ctx.latest_display_frame is not None:
                    frame_to_serve = ctx.latest_display_frame.copy()
                elif ctx.latest_frame is not None:
                    frame_to_serve = ctx.latest_frame.copy()

        if frame_to_serve is None:
            # Generate placeholder image
            placeholder = np.full((360, 640, 3), 20, dtype=np.uint8)
            cv2.putText(
                placeholder,
                f"CAMERA: {camera_id} (WAITING FOR STREAM)",
                (40, 180),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 180, 255),
                2,
                cv2.LINE_AA,
            )
            frame_to_serve = placeholder

        success, encoded = cv2.imencode(".jpg", frame_to_serve, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if not success:
            self._send_json_response(500, {"status": "error", "message": "Failed to encode snapshot"})
            return

        jpeg_bytes = encoded.tobytes()
        self.send_response(200)
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Content-Length", str(len(jpeg_bytes)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(jpeg_bytes)

    def _handle_get_camera_mjpeg_stream(self, camera_id: Optional[str] = None) -> None:
        """Stream continuous multipart/x-mixed-replace MJPEG video frames for the specified camera or primary active camera."""
        target_cam_id = camera_id
        if not target_cam_id:
            all_cams = self.soc.context_manager.get_all_contexts()
            active_ids = [cid for cid, ctx in all_cams.items() if getattr(ctx, "is_active", False)]
            if active_ids:
                target_cam_id = active_ids[0]
            elif all_cams:
                target_cam_id = list(all_cams.keys())[0]
            else:
                target_cam_id = "LAPTOP_01"

        # Check if caller specified max frames (e.g. for unit testing)
        max_frames = -1
        max_hdr = self.headers.get("X-Max-Frames")
        if max_hdr and max_hdr.isdigit():
            max_frames = int(max_hdr)

        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate, pre-check=0, post-check=0, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Connection", "close")
        self.end_headers()

        sent_frames = 0
        try:
            while True:
                ctx = self.soc.context_manager.get(target_cam_id)
                frame_to_serve: Optional[np.ndarray] = None
                if ctx is not None:
                    with ctx._lock:
                        if ctx.latest_display_frame is not None:
                            frame_to_serve = ctx.latest_display_frame.copy()
                        elif ctx.latest_frame is not None:
                            frame_to_serve = ctx.latest_frame.copy()

                if frame_to_serve is None:
                    placeholder = np.full((360, 640, 3), 20, dtype=np.uint8)
                    cv2.putText(
                        placeholder,
                        f"CAM: {target_cam_id} (WAITING FOR STREAM)",
                        (30, 180),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 180, 255),
                        2,
                        cv2.LINE_AA,
                    )
                    frame_to_serve = placeholder

                success, encoded = cv2.imencode(".jpg", frame_to_serve, [cv2.IMWRITE_JPEG_QUALITY, 80])
                if success:
                    jpeg_bytes = encoded.tobytes()
                    part_header = (
                        f"--frame\r\n"
                        f"Content-Type: image/jpeg\r\n"
                        f"Content-Length: {len(jpeg_bytes)}\r\n"
                        f"\r\n"
                    ).encode("utf-8")
                    self.wfile.write(part_header)
                    self.wfile.write(jpeg_bytes)
                    self.wfile.write(b"\r\n")
                    self.wfile.flush()
                    sent_frames += 1

                if 0 < max_frames <= sent_frames:
                    break

                time.sleep(0.066)
        except (BrokenPipeError, ConnectionResetError, socket.error):
            # Client closed stream connection
            return
        except Exception as e:
            logger.debug(f"MJPEG stream ended for {target_cam_id}: {e}")
            return

    def _handle_get_root_info(self) -> None:
        """Serve JSON info about available camera streams, endpoints, and NVIDIA VLM status."""
        all_cams = self.soc.context_manager.get_all_contexts()
        cams_info = [
            {
                "camera_id": cid,
                "name": ctx.config.name,
                "status": "ONLINE" if ctx.is_active else "OFFLINE",
                "stream_url": f"/api/v1/cameras/{cid}/stream",
                "snapshot_url": f"/api/v1/cameras/{cid}/snapshot",
            }
            for cid, ctx in all_cams.items()
        ]
        info = {
            "service": "URBAN SAFETY AI-SOC Camera Server",
            "status": "online",
            "active_cameras": len(cams_info),
            "cameras": cams_info,
            "endpoints": {
                "cameras": "/api/v1/cameras",
                "ingest_frame": "POST /api/v1/ingest/frame",
                "analyze_nvidia_vlm": "POST /api/v1/analyze/nvidia",
                "live_stream": "/stream.mjpg",
            },
            "nvidia_vlm": {
                "configured": bool(self.soc.nvidia_vlm and self.soc.nvidia_vlm.is_configured),
                "model": getattr(self.soc.nvidia_vlm, "model", "meta/llama-3.2-11b-vision-instruct"),
                "base_url": getattr(self.soc.nvidia_vlm, "base_url", "https://integrate.api.nvidia.com/v1"),
            },
        }
        self._send_json_response(200, info)

    def _handle_nvidia_analyze(self) -> None:
        """Analyze a frame image directly via NVIDIA NIM Vision API and return structured JSON."""
        length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length)

        content_type = self.headers.get("Content-Type", "")
        frame_bgr: Optional[np.ndarray] = None
        camera_id = self.headers.get("X-Camera-ID", "LAPTOP_01")
        location = self.headers.get("X-Location", "Surveillance Sector")
        action_hint = self.headers.get("X-Action-Hint", None)

        if "application/json" in content_type:
            try:
                data = json.loads(raw_body.decode("utf-8"))
                camera_id = data.get("camera_id", camera_id)
                location = data.get("location", location)
                action_hint = data.get("action_hint", action_hint)
                b64_str = data.get("frame_base64") or data.get("image_base64") or data.get("image", "")
                if "," in b64_str:
                    b64_str = b64_str.split(",", 1)[1]
                if b64_str:
                    img_data = base64.b64decode(b64_str)
                    nparr = np.frombuffer(img_data, np.uint8)
                    frame_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            except Exception as e:
                self._send_json_response(400, {"status": "error", "message": f"Invalid JSON payload: {e}"})
                return
        else:
            # Raw binary JPEG
            nparr = np.frombuffer(raw_body, np.uint8)
            frame_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame_bgr is None or frame_bgr.size == 0:
            self._send_json_response(400, {"status": "error", "message": "No valid image provided for NVIDIA VLM analysis"})
            return

        if self.soc.nvidia_vlm is None:
            from urbansoc.ai.nvidia_vlm import NvidiaVisionClient
            self.soc.nvidia_vlm = NvidiaVisionClient()

        result = self.soc.nvidia_vlm.analyze_frame(
            image_input=frame_bgr,
            camera_id=camera_id,
            location=location,
            action_hint=action_hint,
        )
        response_payload = {
            "status": "success",
            "result": result,
            **result,
        }
        self._send_json_response(200, response_payload)

    def _handle_register_camera(self) -> None:
        """Handle POST /api/v1/cameras/register."""
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            data = json.loads(body.decode("utf-8"))
            camera_id = data.get("camera_id", "DEFAULT_CAM").strip()
            name = data.get("name", f"Camera {camera_id}")
            lat = float(data.get("latitude", 10.776889))
            lon = float(data.get("longitude", 106.700806))
            addr = data.get("address", "Zone")
            fps = float(data.get("fps", 15.0))

            cfg = CameraLocationConfig(
                camera_id=camera_id,
                name=name,
                latitude=lat,
                longitude=lon,
                address=addr,
            )

            ctx = self.soc.context_manager.get_or_create(camera_id, config=cfg, fps=fps)
            self._send_json_response(
                200,
                {
                    "status": "registered",
                    "camera_id": camera_id,
                    "name": name,
                    "location": {"latitude": lat, "longitude": lon, "address": addr},
                },
            )
        except Exception as e:
            logger.error("Error registering camera: %s", e)
            self._send_json_response(400, {"status": "error", "message": str(e)})

    def _handle_ingest_frame(self) -> None:
        """Handle POST /api/v1/ingest/frame with binary JPEG payload."""
        length = int(self.headers.get("Content-Length", 0))
        if length <= 0:
            self._send_json_response(400, {"status": "error", "message": "Missing Content-Length"})
            return

        raw_bytes = self.rfile.read(length)
        camera_id = self.headers.get("X-Camera-ID", "LAPTOP_01").strip()
        raw_name = self.headers.get("X-Camera-Name")
        camera_name = unquote(raw_name) if raw_name else None
        timestamp_ms_hdr = self.headers.get("X-Timestamp-Ms")
        timestamp_ms = int(timestamp_ms_hdr) if timestamp_ms_hdr and timestamp_ms_hdr.isdigit() else int(time.time() * 1000)

        content_type = self.headers.get("Content-Type", "")

        # Decode image
        frame_bgr: Optional[np.ndarray] = None
        if "application/json" in content_type:
            try:
                data = json.loads(raw_bytes.decode("utf-8"))
                b64_str = data.get("image_base64", "")
                if "," in b64_str:
                    b64_str = b64_str.split(",", 1)[1]
                img_data = base64.b64decode(b64_str)
                nparr = np.frombuffer(img_data, np.uint8)
                frame_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                camera_id = data.get("camera_id", camera_id)
            except Exception as e:
                self._send_json_response(400, {"status": "error", "message": f"JSON decode error: {e}"})
                return
        else:
            # Raw binary JPEG
            nparr = np.frombuffer(raw_bytes, np.uint8)
            frame_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame_bgr is None or frame_bgr.size == 0:
            self._send_json_response(400, {"status": "error", "message": "Invalid JPEG image data"})
            return

        # Retrieve isolated camera context
        ctx = self.soc.context_manager.get_or_create(camera_id)
        if camera_name and ctx.config.name != camera_name:
            ctx.config.name = camera_name

        # Check if client requested a simulated behavior action via header
        test_action_hdr = self.headers.get("X-Test-Action")
        if test_action_hdr:
            from urbansoc.domain.synthetic import create_synthetic_pose

            action_name = test_action_hdr.strip().upper()
            step_idx = ctx.frame_count
            if action_name == "WEAPON_THREAT":
                sim_pose = create_synthetic_pose(track_id=1, spine_mode="upright", wrists_mode="two_handed_aim", step=step_idx)
            elif action_name in ("KNIFE_THREAT", "SHARP_OBJECT", "KNIFE", "BLADE"):
                sim_pose = create_synthetic_pose(track_id=1, spine_mode="upright", wrists_mode="knife_threat", step=step_idx)
            elif action_name == "FALLEN":
                sim_pose = create_synthetic_pose(track_id=1, spine_mode="fallen", step=step_idx)
            elif action_name == "HANDS_UP":
                sim_pose = create_synthetic_pose(track_id=1, spine_mode="upright", wrists_mode="hands_up", step=step_idx)
            elif action_name == "CROUCHING":
                sim_pose = create_synthetic_pose(track_id=1, spine_mode="crouching", step=step_idx)
            elif action_name == "FIGHTING":
                sim_pose = create_synthetic_pose(track_id=1, spine_mode="upright", wrists_mode="fighting", step=step_idx)
            elif action_name == "RUNNING":
                sim_pose = create_synthetic_pose(track_id=1, spine_mode="upright", step=step_idx, speed_offset_x=float(step_idx * 45))
            else:
                sim_pose = create_synthetic_pose(track_id=1, spine_mode="upright", wrists_mode="normal", step=step_idx)

            timestamp_sec = timestamp_ms / 1000.0
            analysis, display_frame = ctx.process_poses(
                frame_bgr=frame_bgr,
                poses=[sim_pose],
                timestamp=timestamp_sec,
            )
        else:
            # Perform centralized YOLO inference under thread lock
            detections = None
            raw_kpts = None
            raw_boxes = None
            t_infer = 0.0

            if self.soc.detector is not None:
                with self.soc.model_lock:
                    detections, raw_kpts, raw_boxes, t_infer = self.soc.detector.extract_raw_detections(frame_bgr)

            # Process detections inside isolated CameraContext (own tracker & behavior engine)
            timestamp_sec = timestamp_ms / 1000.0
            analysis, display_frame = ctx.process_detections(
                frame_bgr=frame_bgr,
                detections=detections,
                raw_kpts_data=raw_kpts,
                raw_boxes_xyxy=raw_boxes,
                t_infer=t_infer,
                timestamp=timestamp_sec,
            )

        # Dispatch webhook if incident occurs and webhook dispatcher is configured
        if self.soc.webhook_dispatcher is not None and self.soc.webhook_dispatcher.is_enabled:
            self.soc.webhook_dispatcher.dispatch_frame_event(
                frame=frame_bgr,
                annotated_frame=display_frame,
                analysis_result=analysis,
                camera_config=ctx.config,
            )

        primary_action = (
            analysis.humans[0].behavior.primary_behavior.value
            if analysis.humans
            else "NORMAL"
        )

        humans_summary = [
            {
                "track_id": h.track_id,
                "bbox": [int(h.bbox.x1), int(h.bbox.y1), int(h.bbox.x2), int(h.bbox.y2)],
                "behavior": h.behavior.primary_behavior.value,
                "threat_level": h.behavior.threat_level.value,
                "threat_score": round(h.behavior.threat_score, 2),
                "role": getattr(h.behavior, "role", "individual"),
                "interacting_with": h.behavior.interacting_with_track_id,
                "reasoning": h.behavior.reasoning,
            }
            for h in analysis.humans
        ]

        response_data = {
            "status": "processed",
            "camera_id": camera_id,
            "frame_index": ctx.frame_count,
            "human_count": analysis.human_count,
            "highest_threat": analysis.highest_threat_level.value,
            "highest_threat_score": round(analysis.highest_threat_score, 2),
            "primary_action": primary_action,
            "measured_fps": round(ctx.measured_fps, 1),
            "humans": humans_summary,
        }

        # Optional NVIDIA NIM VLM Multimodal Analysis on frame
        vlm_hdr = self.headers.get("X-Analyze-VLM", "").lower()
        should_run_vlm = vlm_hdr in ("true", "1", "yes") or analysis.highest_threat_score >= 0.75

        if self.soc.nvidia_vlm is not None and should_run_vlm:
            actors_hint = [
                {
                    "id": h["track_id"],
                    "role": h["role"],
                    "action": h["behavior"].lower(),
                    "posture": h["reasoning"],
                }
                for h in humans_summary
            ]
            response_data["nvidia_vlm_analysis"] = self.soc.nvidia_vlm.analyze_frame(
                image_input=frame_bgr,
                camera_id=camera_id,
                location=ctx.config.name or "Camera Zone",
                action_hint=primary_action,
                actors_hint=actors_hint,
            )

        self._send_json_response(200, response_data)

    def _handle_incident_webhook(self) -> None:
        """Handle incoming incident webhook payloads with forensic SHA-256 verification."""
        length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length)

        try:
            payload = json.loads(raw_body.decode("utf-8"))
            event_id = payload.get("event_id", f"EVT_{time.strftime('%Y%m%d_%H%M%S')}")
            timestamp_ms = int(payload.get("timestamp_ms", 0))
            detection = payload.get("detection", {})
            full_img = detection.get("full_image", {})
            camera = payload.get("camera", {})

            # Forensic verification
            full_b64 = full_img.get("image_base64", "")
            expected_full_hash = full_img.get("sha256_hash", "")
            hash_valid = False
            full_bytes = b""

            if full_b64 and "," in full_b64:
                raw_b64 = full_b64.split(",", 1)[1]
                full_bytes = base64.b64decode(raw_b64)
                computed = compute_forensic_sha256(full_bytes, timestamp_ms)
                hash_valid = (computed == expected_full_hash)

            save_dir = os.path.abspath(os.path.join(self.soc.output_dir, "received_webhooks"))
            os.makedirs(save_dir, exist_ok=True)

            if full_bytes:
                with open(os.path.join(save_dir, f"{event_id}_full_frame.jpg"), "wb") as f:
                    f.write(full_bytes)

            # Save zoomed hand crop if present for AI/VLM inspection
            hand_b64 = payload.get("hand_crop_base64") or payload.get("detection", {}).get("hand_crop_image_base64", "")
            if hand_b64 and "," in hand_b64:
                raw_hand = base64.b64decode(hand_b64.split(",", 1)[1])
                with open(os.path.join(save_dir, f"{event_id}_hand_crop.jpg"), "wb") as f:
                    f.write(raw_hand)

            with open(os.path.join(save_dir, f"{event_id}.json"), "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)

            print(f"\n🚨 [SERVER WEBHOOK] Received incident '{event_id}' from {camera.get('camera_id')}! Forensic SHA-256: {'✅ VALID' if hash_valid else '❌ INVALID'}")

            self._send_json_response(200, {
                "status": "success",
                "event_id": event_id,
                "forensic_hash_valid": hash_valid,
            })
        except Exception as e:
            self._send_json_response(400, {"status": "error", "message": str(e)})

    def _send_json_response(self, status_code: int, data: Dict[str, Any]) -> None:
        """Send JSON response with appropriate HTTP headers."""
        resp_bytes = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(resp_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(resp_bytes)

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress noisy frame ingestion logging unless in debug mode."""
        if "/ingest/frame" in str(args[0]):
            return
        logger.debug("%s - - [%s] %s", self.address_string(), self.log_date_time_string(), format % args)


class InferenceServer:
    """Central AI-SOC Intermediate Inference Server coordinating multi-laptop camera streams."""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8000,
        model_weights: str = "yolo/yolo11n-pose.pt",
        device: Optional[str] = None,
        conf_threshold: float = 0.25,
        output_dir: str = "output",
        webhook_url: Optional[str] = None,
        webhook_min_threat: str = "ALL",
        webhook_cooldown: float = 3.0,
        webhook_filter_noise: bool = True,
        enable_tunnel: bool = True,
    ) -> None:
        self.host = host
        self.port = port
        self.model_weights = model_weights
        self.device = device
        self.conf_threshold = conf_threshold
        self.output_dir = os.path.abspath(output_dir)
        self.webhook_url = webhook_url
        self.enable_tunnel = enable_tunnel

        os.makedirs(self.output_dir, exist_ok=True)

        # Context manager for multi-tenant isolation
        self.context_manager = CameraContextManager(output_dir=self.output_dir)

        # Cloudflare Tunnel Manager for native remote external access
        self.public_tunnel_url: Optional[str] = None
        self.tunnel_manager = None
        if self.enable_tunnel:
            try:
                from urbansoc.server.tunnel import CloudflareTunnelManager
                self.tunnel_manager = CloudflareTunnelManager(local_port=self.port, local_host="127.0.0.1")
            except Exception as e:
                logger.warning(f"Could not initialize CloudflareTunnelManager: {e}")

        # Shared YOLO detector instance
        logger.info("Initializing shared YOLOv11-Pose engine on server...")
        self.detector = YOLOPoseDetector(
            model_path=self.model_weights,
            device=self.device,
            conf_threshold=self.conf_threshold,
            output_dir=self.output_dir,
        )
        self.model_lock = threading.Lock()

        # Webhook dispatcher for outgoing incident alerts
        self.webhook_dispatcher: Optional[WebhookDispatcher] = None
        if webhook_url:
            self.webhook_dispatcher = WebhookDispatcher(
                server_url=webhook_url,
                min_threat_level=webhook_min_threat,
                cooldown_seconds=webhook_cooldown,
                filter_noise=webhook_filter_noise,
            )

        # NVIDIA VLM Client for deep multimodal vision reasoning
        self.nvidia_vlm = NvidiaVisionClient()

        self._httpd: Optional[ThreadedHTTPServer] = None
        self._server_thread: Optional[threading.Thread] = None

    def get_local_ip(self) -> str:
        """Find local LAN IP address to display to user for laptop-to-laptop connectivity."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def start(self, blocking: bool = True) -> None:
        """Start the threaded intermediate inference server."""
        server_address = (self.host, self.port)

        # Create custom handler class binding this server instance
        server_instance = self

        class BoundHandler(SOCMultiCameraHandler):
            soc_server = server_instance

        self._httpd = ThreadedHTTPServer(server_address, BoundHandler)
        self._httpd.inference_server = self
        local_ip = self.get_local_ip()

        # Start Cloudflare Tunnel if enabled
        if self.tunnel_manager is not None:
            print("🌐 [Cloudflare Tunnel] Đang tự động kết nối Quick Tunnel...")
            self.public_tunnel_url = self.tunnel_manager.start(timeout_seconds=12.0)

        vlm_key_status = "Đã cấu hình (NVIDIA_API_KEY)" if self.nvidia_vlm.api_key else "Chưa có key (Fallback MOCK mode)"

        print("=" * 78)
        print("📹 [URBAN SAFETY AI-SOC] CENTRAL CAMERA INFERENCE & NVIDIA VLM SERVER")
        print("=" * 78)
        print(f"• Server Listening:   http://{self.host}:{self.port}")
        print(f"• LAN Status URL:     http://{local_ip}:{self.port}/api/v1/cameras")
        print(f"• Frame Ingestion:    POST http://{local_ip}:{self.port}/api/v1/ingest/frame")
        print(f"• NVIDIA VLM API:     POST http://{local_ip}:{self.port}/api/v1/analyze/nvidia")
        print(f"• NVIDIA Model:       {self.nvidia_vlm.model} ({vlm_key_status})")
        print(f"• Live MJPEG Stream:  http://{local_ip}:{self.port}/api/v1/cameras/LAPTOP_01/stream")
        print(f"• Direct Short Stream:http://{local_ip}:{self.port}/stream.mjpg")
        if self.public_tunnel_url:
            print("------------------------------------------------------------------------------")
            print("🌍 PUBLIC CLOUDFLARE TUNNEL (TRUY CẬP TỪ MỌI NƠI QUA INTERNET):")
            print(f"• 🔗 Public Base URL:   {self.public_tunnel_url}")
            print(f"• 📹 Public Stream:     {self.public_tunnel_url}/api/v1/cameras/LAPTOP_01/stream")
            print(f"• ⚡ Direct Short Stream:{self.public_tunnel_url}/stream.mjpg")
            print(f"• 🧠 Public VLM API:    POST {self.public_tunnel_url}/api/v1/analyze/nvidia")
            print("------------------------------------------------------------------------------")
        print(f"• Local YOLO Model:   {self.model_weights} (Device: {self.detector.device})")
        print(f"• Output Directory:   {self.output_dir}/")
        if self.webhook_url:
            print(f"• Webhook Forward:    {self.webhook_url}")
        print("=" * 78)
        print(f"👉 Để khởi động camera client gửi video về server:")
        print(f"   ./start_client.sh")
        print(f"   hoặc: python3 client.py --server-url http://{local_ip}:{self.port} --camera 0 --camera-id LAPTOP_01\n")

        if blocking:
            try:
                self._httpd.serve_forever()
            except KeyboardInterrupt:
                print("\nServer stopping upon keyboard interrupt...")
            finally:
                self.stop()
        else:
            self._server_thread = threading.Thread(
                target=self._httpd.serve_forever,
                name="SOCInferenceServerThread",
                daemon=True,
            )
            self._server_thread.start()

    def stop(self) -> None:
        """Gracefully shut down the server and worker threads."""
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None
        if self.tunnel_manager is not None:
            self.tunnel_manager.stop()
        if self.webhook_dispatcher is not None:
            self.webhook_dispatcher.close()
        logger.info("InferenceServer shut down cleanly.")
