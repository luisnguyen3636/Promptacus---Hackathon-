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

        # 3. Web Dashboard UI
        if clean_path in ("", "/", "/dashboard"):
            self._handle_get_dashboard()
            return

        # Fallback to standard file serving
        super().do_GET()

    def do_POST(self) -> None:
        """Route POST requests: camera registration, binary frame ingestion, and incident webhooks."""
        clean_path = self.path.split("?")[0].rstrip("/")

        if clean_path == "/api/v1/cameras/register":
            self._handle_register_camera()
            return

        if clean_path == "/api/v1/ingest/frame":
            self._handle_ingest_frame()
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

    def _handle_get_dashboard(self) -> None:
        """Serve the multi-camera interactive SOC web dashboard."""
        html = self.soc.render_dashboard_html()
        html_bytes = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html_bytes)))
        self.end_headers()
        self.wfile.write(html_bytes)

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

        response_data = {
            "status": "processed",
            "camera_id": camera_id,
            "frame_index": ctx.frame_count,
            "human_count": analysis.human_count,
            "highest_threat": analysis.highest_threat_level.value,
            "highest_threat_score": round(analysis.highest_threat_score, 2),
            "primary_action": primary_action,
            "measured_fps": round(ctx.measured_fps, 1),
        }
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
    ) -> None:
        self.host = host
        self.port = port
        self.model_weights = model_weights
        self.device = device
        self.conf_threshold = conf_threshold
        self.output_dir = os.path.abspath(output_dir)
        self.webhook_url = webhook_url

        os.makedirs(self.output_dir, exist_ok=True)

        # Context manager for multi-tenant isolation
        self.context_manager = CameraContextManager(output_dir=self.output_dir)

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

    def render_dashboard_html(self) -> str:
        """Generate real-time multi-camera SOC web dashboard HTML/JS."""
        local_ip = self.get_local_ip()
        return f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>URBAN SAFETY AI-SOC | Multi-Camera Grid</title>
    <style>
        :root {{
            --bg-main: #090d16;
            --bg-card: #131b2e;
            --border-card: #202d4a;
            --text-main: #f1f5f9;
            --text-sub: #94a3b8;
            --accent-cyan: #06b6d4;
            --accent-green: #10b981;
            --accent-amber: #f59e0b;
            --accent-rose: #f43f5e;
            --accent-purple: #8b5cf6;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
        body {{ background: var(--bg-main); color: var(--text-main); min-height: 100vh; padding: 20px; }}
        header {{
            display: flex; justify-content: space-between; align-items: center;
            padding: 16px 24px; background: var(--bg-card); border: 1px solid var(--border-card);
            border-radius: 12px; margin-bottom: 24px;
        }}
        .brand {{ display: flex; align-items: center; gap: 14px; }}
        .brand-badge {{ background: var(--accent-cyan); color: #000; font-weight: 800; padding: 6px 12px; border-radius: 6px; font-size: 13px; }}
        .brand-title {{ font-size: 20px; font-weight: 700; letter-spacing: 0.5px; }}
        .header-stats {{ display: flex; align-items: center; gap: 20px; }}
        .stat-pill {{ background: #1e293b; padding: 6px 14px; border-radius: 20px; font-size: 13px; border: 1px solid #334155; }}
        .stat-pill strong {{ color: var(--accent-cyan); }}

        .instructions {{
            background: #0f172a; border-left: 4px solid var(--accent-cyan);
            padding: 14px 20px; border-radius: 8px; margin-bottom: 24px; font-size: 14px; line-height: 1.6;
        }}
        .code-block {{ background: #020617; padding: 8px 12px; border-radius: 6px; font-family: monospace; color: var(--accent-cyan); display: inline-block; margin-top: 6px; }}

        .camera-grid {{
            display: grid; grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));
            gap: 20px;
        }}
        .camera-card {{
            background: var(--bg-card); border: 1px solid var(--border-card);
            border-radius: 12px; overflow: hidden; display: flex; flex-direction: column;
            box-shadow: 0 4px 20px rgba(0,0,0,0.4); transition: transform 0.2s, border-color 0.2s;
        }}
        .camera-card:hover {{ transform: translateY(-2px); border-color: #3b82f6; }}
        .card-header {{
            padding: 12px 16px; display: flex; justify-content: space-between; align-items: center;
            background: #101726; border-bottom: 1px solid var(--border-card);
        }}
        .cam-name {{ font-weight: 600; font-size: 15px; display: flex; align-items: center; gap: 8px; }}
        .status-dot {{ width: 10px; height: 10px; border-radius: 50%; background: #64748b; }}
        .status-dot.online {{ background: var(--accent-green); box-shadow: 0 0 8px var(--accent-green); }}

        .preview-container {{
            position: relative; width: 100%; aspect-ratio: 4/3; background: #000;
            display: flex; align-items: center; justify-content: center; overflow: hidden;
        }}
        .preview-img {{ width: 100%; height: 100%; object-fit: contain; }}
        .threat-pill {{
            position: absolute; top: 12px; right: 12px;
            padding: 4px 10px; border-radius: 6px; font-weight: 700; font-size: 12px;
            text-transform: uppercase; letter-spacing: 0.5px;
        }}
        .threat-LOW {{ background: rgba(16, 185, 129, 0.25); color: #34d399; border: 1px solid #10b981; }}
        .threat-MEDIUM {{ background: rgba(245, 158, 11, 0.25); color: #fbbf24; border: 1px solid #f59e0b; }}
        .threat-HIGH {{ background: rgba(249, 115, 22, 0.25); color: #fb923c; border: 1px solid #f97316; }}
        .threat-CRITICAL {{ background: rgba(244, 63, 94, 0.35); color: #fda4af; border: 1px solid #f43f5e; animation: pulse 1s infinite; }}

        @keyframes pulse {{
            0% {{ transform: scale(1); }}
            50% {{ transform: scale(1.05); }}
            100% {{ transform: scale(1); }}
        }}

        .card-body {{ padding: 14px 16px; font-size: 13px; display: flex; flex-direction: column; gap: 8px; }}
        .info-row {{ display: flex; justify-content: space-between; }}
        .info-label {{ color: var(--text-sub); }}
        .info-value {{ font-weight: 500; }}
        .action-highlight {{ color: var(--accent-cyan); font-weight: 700; }}

        .empty-placeholder {{
            text-align: center; padding: 60px 20px; color: var(--text-sub);
            background: var(--bg-card); border-radius: 12px; border: 1px dashed var(--border-card);
        }}
    </style>
</head>
<body>
    <header>
        <div class="brand">
            <span class="brand-badge">SOC CORE</span>
            <span class="brand-title">URBAN SAFETY AI-SOC — MULTI-CAMERA CENTRAL SERVER</span>
        </div>
        <div class="header-stats">
            <div class="stat-pill">Mạng LAN IP: <strong>{local_ip}:{self.port}</strong></div>
            <div class="stat-pill">Cameras: <strong id="cam-count">0</strong></div>
            <div class="stat-pill" id="clock">--:--:--</div>
        </div>
    </header>

    <div class="instructions">
        💡 <strong>Hướng dẫn kết nối các Laptop khác làm Camera biên:</strong><br/>
        Mở Terminal trên bất kỳ chiếc laptop nào khác trong cùng mạng Wi-Fi và chạy lệnh:
        <br/>
        <div class="code-block">python3 client.py --server-url http://{local_ip}:{self.port} --camera 0 --camera-id LAPTOP_01 --camera-name "Laptop Cổng Đông"</div>
    </div>

    <div id="camera-grid" class="camera-grid">
        <div class="empty-placeholder">
            <h3>Đang quét các Camera kết nối...</h3>
            <p style="margin-top: 8px;">Chưa có chiếc Laptop nào gửi luồng video. Hãy chạy script client trên laptop khác để bắt đầu!</p>
        </div>
    </div>

    <script>
        function updateClock() {{
            document.getElementById('clock').textContent = new Date().toLocaleTimeString('vi-VN');
        }}
        setInterval(updateClock, 1000);
        updateClock();

        let knownCameras = new Set();

        async function fetchCameraStatus() {{
            try {{
                const resp = await fetch('/api/v1/cameras');
                if (!resp.ok) return;
                const data = await resp.json();
                const cameras = data.cameras || [];

                document.getElementById('cam-count').textContent = cameras.length;
                const grid = document.getElementById('camera-grid');

                if (cameras.length === 0) {{
                    grid.innerHTML = `
                        <div class="empty-placeholder" style="grid-column: 1 / -1;">
                            <h3>Đang chờ tín hiệu từ Laptop Client...</h3>
                            <p style="margin-top: 8px;">Khởi động client trên laptop khác để hiển thị trực tiếp tại đây.</p>
                        </div>`;
                    return;
                }}

                let html = '';
                const now = Date.now();

                cameras.forEach(cam => {{
                    const isOnline = (cam.status === 'ONLINE');
                    const threat = cam.highest_threat || 'LOW';
                    const snapUrl = `/api/v1/cameras/${{encodeURIComponent(cam.camera_id)}}/snapshot?t=${{now}}`;

                    html += `
                    <div class="camera-card">
                        <div class="card-header">
                            <div class="cam-name">
                                <div class="status-dot ${{isOnline ? 'online' : ''}}"></div>
                                ${{cam.name || cam.camera_id}}
                            </div>
                            <span style="font-size: 11px; color: #64748b; font-family: monospace;">${{cam.camera_id}}</span>
                        </div>
                        <div class="preview-container">
                            <img class="preview-img" src="${{snapUrl}}" alt="Camera Stream" loading="lazy">
                            <div class="threat-pill threat-${{threat}}">${{threat}}</div>
                        </div>
                        <div class="card-body">
                            <div class="info-row">
                                <span class="info-label">Hành vi chính:</span>
                                <span class="info-value action-highlight">${{cam.primary_action || 'NORMAL'}}</span>
                            </div>
                            <div class="info-row">
                                <span class="info-label">Số người trong khung:</span>
                                <span class="info-value">${{cam.human_count}}</span>
                            </div>
                            <div class="info-row">
                                <span class="info-label">Tốc độ khung hình:</span>
                                <span class="info-value">${{cam.fps}} FPS (${{cam.total_frames}} frames)</span>
                            </div>
                            <div class="info-row">
                                <span class="info-label">Vị trí:</span>
                                <span class="info-value">${{cam.location ? cam.location.address : 'N/A'}}</span>
                            </div>
                        </div>
                    </div>`;
                }});

                grid.innerHTML = html;

            }} catch (err) {{
                console.error("Error fetching camera status:", err);
            }}
        }}

        // Poll camera status and snapshots every 1.5 seconds
        setInterval(fetchCameraStatus, 1500);
        fetchCameraStatus();
    </script>
</body>
</html>
"""

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

        print("=" * 76)
        print("🌐 [URBAN SAFETY AI-SOC] CENTRAL MULTI-CAMERA INFERENCE SERVER RUNNING")
        print("=" * 76)
        print(f"• Server Listening: http://{self.host}:{self.port}")
        print(f"• LAN Dashboard:    http://{local_ip}:{self.port}")
        print(f"• Status API:       http://{local_ip}:{self.port}/api/v1/cameras")
        print(f"• Frame Ingestion:  POST http://{local_ip}:{self.port}/api/v1/ingest/frame")
        print(f"• Model Weights:    {self.model_weights} (Device: {self.detector.device})")
        print(f"• Output Directory: {self.output_dir}/")
        if self.webhook_url:
            print(f"• Webhook Forward:  {self.webhook_url} (Auto-Dispatched to AI Model)")
        print("=" * 76)
        print(f"👉 Để kết nối Laptop khác, chạy trên laptop đó:")
        print(f"   python3 client.py --server-url http://{local_ip}:{self.port} --camera 0 --camera-id LAPTOP_01\n")

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
        if self.webhook_dispatcher is not None:
            self.webhook_dispatcher.close()
        logger.info("InferenceServer shut down cleanly.")
