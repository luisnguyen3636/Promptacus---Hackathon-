#!/usr/bin/env python3
"""DeepSeek V4 Flash Webhook Receiver & VLM Vision Analyzer for Urban Safety AI-SOC.

Script mẫu kết nối DeepSeek Multimodal API để tiếp nhận và phân tích hình ảnh sự cố từ AI-SOC.

Cách sử dụng:
1. Chạy receiver trên máy chủ của bạn (ví dụ cổng 9000):
   python3 scripts/deepseek_v4_flash_receiver.py --port 9000

2. Khởi động AI-SOC Server chuyển tiếp webhook về receiver này:
   python3 server.py 8000 --webhook-forward-url http://127.0.0.1:9000/api/v1/incidents
"""

import argparse
import base64
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict


class DeepSeekWebhookHandler(BaseHTTPRequestHandler):
    """Webhook HTTP Receiver optimized for DeepSeek VLM vision analysis."""

    def do_POST(self) -> None:
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length)

        try:
            payload: Dict[str, Any] = json.loads(raw_body.decode("utf-8"))
        except Exception as e:
            self._send_response(400, {"status": "error", "message": f"Invalid JSON: {e}"})
            return

        event_id = payload.get("event_id", "UNKNOWN_EVENT")
        camera_id = payload.get("camera_id", payload.get("camera", {}).get("camera_id", "CAM_01"))
        primary_action = payload.get("primary_action", "NORMAL")
        threat_level = payload.get("threat_level", "LOW")
        threat_score = payload.get("threat_score", 0.0)

        # 1. Trích xuất trực tiếp ảnh toàn cảnh và ảnh zoom bàn tay cho DeepSeek
        full_image_b64 = payload.get("image") or payload.get("image_base64")
        hand_crop_b64 = payload.get("hand_crop_base64")
        deepseek_message = payload.get("deepseek_message")

        print("\n" + "=" * 76)
        print(f"🚨 [DEEPSEEK V4 FLASH RECEIVER] ĐÃ NHẬN SỰ CỐ: {event_id}")
        print("=" * 76)
        print(f"• Camera:          {camera_id}")
        print(f"• Hành vi sơ bộ:   {primary_action} (Cấp độ: {threat_level}, Điểm: {threat_score:.2f})")
        print(f"• Ảnh toàn cảnh:   {'✅ Có sẵn (Base64 Data URI)' if full_image_b64 else '❌ Không có'}")
        print(f"• Ảnh zoom bàn tay: {'✅ Có sẵn (Hand ROI)' if hand_crop_b64 else '❌ Không có'}")
        print(f"• DeepSeek Message: {'✅ Đã chuẩn hóa OpenAI Multimodal Format' if deepseek_message else '❌ Thiếu'}")
        print("=" * 76)

        # 2. Ví dụ gọi DeepSeek API (nếu có DEEPSEEK_API_KEY)
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if api_key and deepseek_message:
            print("🤖 Đang gửi hình ảnh và prompt sang DeepSeek Multimodal API...", flush=True)
            try:
                import urllib.request
                ds_req = urllib.request.Request(
                    "https://api.deepseek.com/chat/completions",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {api_key}",
                    },
                    data=json.dumps({
                        "model": "deepseek-chat",
                        "messages": [deepseek_message],
                        "temperature": 0.2,
                        "max_tokens": 512,
                    }).encode("utf-8"),
                    method="POST",
                )
                with urllib.request.urlopen(ds_req, timeout=15.0) as ds_resp:
                    ds_data = json.loads(ds_resp.read().decode("utf-8"))
                    answer = ds_data["choices"][0]["message"]["content"]
                    print("\n📝 [DEEPSEEK V4 PHÂN TÍCH THỊ GIÁC]:")
                    print(answer)
            except Exception as err:
                print(f"⚠️ Gọi DeepSeek API thất bại: {err}")
        else:
            print("💡 (Mẹo: Cài đặt biến môi trường DEEPSEEK_API_KEY để tự động gọi API phân tích thực tế).")

        self._send_response(200, {
            "status": "success",
            "event_id": event_id,
            "deepseek_ready": True,
            "images_received": {
                "full_image": bool(full_image_b64),
                "hand_crop": bool(hand_crop_b64),
            }
        })

    def _send_response(self, code: int, data: Dict[str, Any]) -> None:
        resp_bytes = json.dumps(data).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(resp_bytes)))
        self.end_headers()
        self.wfile.write(resp_bytes)

    def log_message(self, format: str, *args: Any) -> None:
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description="DeepSeek V4 Flash Webhook Receiver")
    parser.add_argument("--port", type=int, default=9000, help="Listening port (default: 9000)")
    args = parser.parse_args()

    server = HTTPServer(("0.0.0.0", args.port), DeepSeekWebhookHandler)
    print(f"🌐 DeepSeek V4 Flash Webhook Receiver đang lắng nghe tại http://0.0.0.0:{args.port}/api/v1/incidents")
    print("👉 Nhấn Ctrl+C để dừng server.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Đang dừng DeepSeek Receiver...")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
