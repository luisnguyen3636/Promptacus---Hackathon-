#!/usr/bin/env python3
"""Dedicated Test Receiver Server for Urban Safety AI-SOC.

Máy chủ độc lập tiếp nhận và kiểm chứng JSON metadata do AI Server gửi sang.
Lắng nghe mặc định trên cổng 9000:
    python3 test_receiver_server.py 9000

Tính năng:
1. Tiếp nhận mọi POST request (Webhooks, AI metadata, Incident packages).
2. In định dạng màu sắc ANSI trực quan chi tiết ra Terminal (Severity, Threat Score, Actors, Reasoning).
3. Lưu toàn bộ JSON metadata vào thư mục output/test_received_events/ để kiểm toán.
4. Cung cấp GET /events để kiểm tra danh sách sự cố đã nhận.
"""

import argparse
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import os
from socketserver import ThreadingMixIn
import sys
import time
from typing import Any, Dict, List

# ANSI Color Codes
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
RESET = "\033[0m"


class ThreadedReceiverServer(ThreadingMixIn, HTTPServer):
    __test__ = False
    daemon_threads = True
    allow_reuse_address = True


class TestReceiverHandler(SimpleHTTPRequestHandler):
    __test__ = False
    received_events: List[Dict[str, Any]] = []
    output_dir: str = "output/test_received_events"

    def do_GET(self) -> None:
        """Route GET requests: check status or retrieve received events list."""
        clean_path = self.path.split("?")[0].rstrip("/")

        if clean_path in ("", "/", "/status"):
            resp = {
                "service": "Urban Safety AI Test Receiver Server",
                "status": "online",
                "total_events_received": len(self.received_events),
                "storage_directory": os.path.abspath(self.output_dir),
            }
            self._send_json(200, resp)
            return

        if clean_path in ("/events", "/api/v1/events"):
            resp = {
                "count": len(self.received_events),
                "events": self.received_events[-50:],  # Return latest 50 events
            }
            self._send_json(200, resp)
            return

        self._send_json(404, {"status": "error", "message": "Not Found"})

    def do_POST(self) -> None:
        """Receive and log JSON metadata from AI Server."""
        length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length)

        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except Exception as e:
            print(f"{RED}[RECEIVER ERROR] Failed to parse JSON payload: {e}{RESET}")
            self._send_json(400, {"status": "error", "message": f"Invalid JSON: {e}"})
            return

        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        os.makedirs(self.output_dir, exist_ok=True)

        # Store in-memory
        payload["_received_at"] = now_str
        self.received_events.append(payload)

        # Extract primary metadata fields
        severity = str(payload.get("severity") or payload.get("threat_level") or "UNKNOWN").upper()
        threat_score = payload.get("threat_score") or payload.get("highest_threat_score") or 0.0
        action = str(payload.get("action_type") or payload.get("primary_action") or "UNSPECIFIED").upper()
        camera_id = payload.get("camera_id") or "UNKNOWN_CAM"
        if isinstance(payload.get("camera"), dict):
            camera_id = payload["camera"].get("camera_id", camera_id)

        location = payload.get("location")
        if isinstance(location, dict):
            location_str = location.get("address") or location.get("name") or str(location)
        else:
            location_str = str(location or "Surveillance Area")

        actors = payload.get("actors") or payload.get("humans") or []
        visual_cues = payload.get("visual_cues") or {}
        reasoning = payload.get("reasoning") or payload.get("description") or "N/A"

        situation = payload.get("situation_assessment") or {}
        intent_data = payload.get("intent_prediction") or {}
        active_cam = payload.get("active_camera") or {}
        eval_subs = payload.get("evaluated_subjects") or []
        directives = payload.get("operator_dashboard_directives") or {}

        # Determine color badge
        if severity == "CRITICAL":
            sev_color = RED + BOLD
        elif severity == "HIGH":
            sev_color = YELLOW + BOLD
        elif severity == "MEDIUM":
            sev_color = CYAN
        else:
            sev_color = GREEN

        # Print formatted incident receipt block
        print("\n" + "=" * 78)
        print(f"📡 {BOLD}[TEST RECEIVER] NHẬN GÓI METADATA TỪ AI SERVER{RESET} ({now_str})")
        print("=" * 78)
        cam_display_name = active_cam.get("camera_name") or camera_id
        cam_phys_loc = active_cam.get("physical_location") or location_str
        print(f"• Camera Đích Danh:  {CYAN}{BOLD}{cam_display_name}{RESET}")
        print(f"• Địa Điểm Vật Lý:   {cam_phys_loc}")
        print(f"• Severity:          {sev_color}[{severity}]{RESET} | Threat Score: {BOLD}{threat_score}{RESET}")
        print(f"• Hành Vi Nhận Diện: {MAGENTA}{BOLD}{action}{RESET}")

        if eval_subs:
            sub = eval_subs[0]
            if sub.get("false_positive_suppressed"):
                print(f"• Triệt tiêu lỗi:    {YELLOW}[FALSE POSITIVE SUPPRESSED] {sub.get('suppression_explanation')}{RESET}")
            bs_data = sub.get("multi_camera_blind_spot_reasoning", {})
            if bs_data and bs_data.get("is_triggered"):
                tactical = bs_data.get("subject_tactical_profile", {})
                print(f"• Cổng Thoát Vùng Mù: {bs_data.get('exit_gate_on_origin_cam')} ➔ Vùng {bs_data.get('blind_spot_zone_id')}")
                print(f"• Hồ Sơ Chiến Thuật:  Tay thuận: {tactical.get('dominant_hand')} | Tay giữ đồ: {tactical.get('active_holding_hand')} | Tâm lý: {tactical.get('psychological_state')}")

                preds = bs_data.get("predicted_next_cameras", [])
                if preds:
                    print(f"\n🔮 {BOLD}DỰ BÁO ĐÓN LÕNG TẠI CÁC CAMERA ĐÍCH DANH TIẾP THEO:{RESET}")
                    for p in preds[:3]:
                        print(f"   [Rank {p.get('rank')}] 📹 {BOLD}{p.get('target_camera_name')}{RESET} (Xác suất: {BOLD}{int(p.get('probability',0)*100)}%{RESET})")
                        print(f"          - Cửa ngõ xuất hiện: {CYAN}{p.get('expected_entry_gate_on_target_cam')}{RESET}")
                        print(f"          - Cửa sổ thời gian ETA: {p.get('estimated_arrival_seconds', [0,0])[0]} - {p.get('estimated_arrival_seconds', [0,0])[1]} giây")
                        print(f"          - Hành vi ẩn dự đoán: {', '.join(p.get('predicted_hidden_actions_in_blind_spot', []))}")
                        print(f"          - Phân tích: {p.get('detailed_tactical_reasoning')}")

                reid = bs_data.get("cross_camera_reid_handover_token", {})
                if reid:
                    print(f"• Nhận Dạng ReID:    Tag: {reid.get('global_subject_tag')} | {reid.get('visual_appearance_signature')}")

        if directives and directives.get("suggested_operator_focus"):
            print(f"\n🚨 {BOLD}CHỈ THỊ VẬN HÀNH VIÊN (SOC DIRECTIVE):{RESET}")
            print(f"   👉 {directives.get('suggested_operator_focus')}")
            if directives.get("highlight_camera_names_on_map"):
                print(f"   🗺️ Camera cần bật viền đỏ: {directives.get('highlight_camera_names_on_map')}")

        # Save to file
        event_filename = f"event_{int(time.time() * 1000)}_{camera_id}.json"
        event_path = os.path.join(self.output_dir, event_filename)
        try:
            with open(event_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            print(f"💾 Saved to:        {GREEN}{event_path}{RESET}")
        except Exception as e:
            print(f"{RED}Failed to save JSON to disk: {e}{RESET}")

        print("=" * 78 + "\n")

        # Response
        self._send_json(200, {
            "status": "received",
            "message": "Metadata successfully processed by Test Receiver",
            "received_at": now_str,
            "event_file": event_filename,
        })

    def _send_json(self, status_code: int, data: Dict[str, Any]) -> None:
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress standard logging to keep terminal output clean and focused."""
        pass


def run_receiver(port: int = 9000, host: str = "0.0.0.0", blocking: bool = True) -> ThreadedReceiverServer:
    server_address = (host, port)
    httpd = ThreadedReceiverServer(server_address, TestReceiverHandler)
    print("=" * 78)
    print(f"🎯 {BOLD}[URBAN SAFETY AI] TEST RECEIVER SERVER ĐANG CHẠY{RESET}")
    print("=" * 78)
    print(f"• Lắng nghe tại:     http://{host}:{port}")
    print(f"• Nhận Webhook:      POST http://localhost:{port}/api/v1/test/receive")
    print(f"• Xem sự kiện:       GET  http://localhost:{port}/events")
    print(f"• Thư mục lưu JSON:  output/test_received_events/")
    print("=" * 78)
    print("Sẵn sàng tiếp nhận request phân tích từ AI Server...\n")

    if blocking:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nTest Receiver Server stopping...")
        finally:
            httpd.server_close()
    return httpd


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Receiver Server for Urban Safety AI")
    parser.add_argument("port", type=int, nargs="?", default=9000, help="Port to listen (default: 9000)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host address (default: 0.0.0.0)")
    args = parser.parse_args()

    run_receiver(port=args.port, host=args.host, blocking=True)
