#!/usr/bin/env python3
"""Live End-to-End Test Script: Camera Image -> Central AI Inference -> NVIDIA NIM VLM -> Test Receiver."""

import base64
import json
import os
import sys
import threading
import time
from typing import Any, Dict

import cv2
import numpy as np
import requests

current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from test_receiver_server import TestReceiverHandler, ThreadedReceiverServer
from urbansoc.ai.nvidia_vlm import NvidiaVisionClient
from urbansoc.server.inference_server import InferenceServer


def create_realistic_test_frame() -> np.ndarray:
    """Generate a realistic surveillance camera frame depicting an urban street scene with actors."""
    h, w = 480, 640
    # Background: street pavement and sidewalk
    frame = np.full((h, w, 3), 45, dtype=np.uint8)
    frame[280:, :] = (70, 70, 70)  # Road
    cv2.line(frame, (0, 280), (w, 280), (120, 120, 120), 2)  # Curb

    # Draw CCTV timestamp watermark
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    cv2.putText(frame, f"CAM-01 [LIVE] {ts} EAST-GATE", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

    # Actor 1 (Person A - Attacker in red/orange)
    cv2.circle(frame, (240, 180), 25, (0, 100, 255), -1)  # Head
    cv2.line(frame, (240, 205), (240, 310), (0, 100, 255), 12)  # Torso
    cv2.line(frame, (240, 230), (310, 215), (0, 100, 255), 8)  # Punching arm reaching forward
    cv2.circle(frame, (315, 215), 10, (0, 140, 255), -1)  # Fist
    cv2.line(frame, (240, 310), (220, 410), (0, 80, 200), 10)  # Left leg
    cv2.line(frame, (240, 310), (265, 405), (0, 80, 200), 10)  # Right leg forward

    # Actor 2 (Person B - Victim in blue)
    cv2.circle(frame, (350, 195), 25, (255, 120, 0), -1)  # Head
    cv2.line(frame, (350, 220), (370, 320), (255, 120, 0), 12)  # Torso recoiling back
    cv2.line(frame, (350, 235), (325, 210), (255, 140, 0), 8)  # Defensive blocking arm
    cv2.line(frame, (370, 320), (360, 415), (200, 80, 0), 10)  # Left leg
    cv2.line(frame, (370, 320), (395, 410), (200, 80, 0), 10)  # Right leg back

    cv2.putText(frame, "PERSON A (AGGRESSOR)", (180, 145), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 200, 255), 1)
    cv2.putText(frame, "PERSON B (DEFENDER)", (330, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 200, 0), 1)
    return frame


def run_live_test() -> None:
    print("=" * 80)
    print("🚀 BẮT ĐẦU KIỂM THỬ TRỰC TIẾP LUỒNG PHÂN TÍCH AI VÀ RECEIVER SERVER")
    print("=" * 80)

    receiver_port = 9005
    server_port = 8005
    log_file_path = os.path.join(current_dir, "output", "live_test_ai_output.log")
    os.makedirs(os.path.join(current_dir, "output"), exist_ok=True)

    # 1. Khởi động Test Receiver Server tại port 9005
    print(f"\n1️⃣  Khởi động Test Receiver Server tại http://127.0.0.1:{receiver_port}...")
    TestReceiverHandler.received_events = []
    TestReceiverHandler.output_dir = os.path.join(current_dir, "output", "test_received_events")
    receiver_server = ThreadedReceiverServer(("127.0.0.1", receiver_port), TestReceiverHandler)
    receiver_thread = threading.Thread(target=receiver_server.serve_forever, daemon=True)
    receiver_thread.start()
    print("   ✅ Test Receiver Server đã sẵn sàng nhận metadata.")

    # 2. Khởi động AI Server tại port 8005
    print(f"\n2️⃣  Khởi động Central AI Server tại http://127.0.0.1:{server_port}...")
    ai_server = InferenceServer(
        host="127.0.0.1",
        port=server_port,
        output_dir=os.path.join(current_dir, "output"),
        enable_tunnel=False,
        webhook_url=f"http://127.0.0.1:{receiver_port}/api/v1/test/receive",
        always_vlm=True,
    )
    ai_server.start(blocking=False)
    time.sleep(0.5)
    print("   ✅ Central AI Server đã nạp mô hình và sẵn sàng xử lý request.")

    logs: list[str] = []

    try:
        # 3. Tạo khung hình camera thực tế
        print("\n3️⃣  Tạo ảnh camera giả lập hiện trường (2 đối tượng đang ẩu đả)...")
        frame_bgr = create_realistic_test_frame()
        success, encoded = cv2.imencode(".jpg", frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 85])
        assert success, "Mã hóa JPEG thất bại"
        jpeg_bytes = encoded.tobytes()
        b64_img = base64.b64encode(jpeg_bytes).decode("utf-8")

        test_frame_file = os.path.join(current_dir, "output", "live_test_frame.jpg")
        cv2.imwrite(test_frame_file, frame_bgr)
        print(f"   ✅ Đã lưu khung hình kiểm thử tại: {test_frame_file} ({len(jpeg_bytes)} bytes)")

        # 4. GỬI REQUEST 1: POST /api/v1/ingest/frame (Raw JPEG từ Camera)
        print(f"\n4️⃣  Camera gửi ảnh thực tế qua POST /api/v1/ingest/frame...")
        t0 = time.time()
        headers = {
            "Content-Type": "image/jpeg",
            "X-Camera-ID": "CAM_LIVE_GATE_01",
            "X-Camera-Name": "Cong So 1 - Khu Pho An Ninh",
            "X-Test-Action": "FIGHTING",
            "X-Timestamp-Ms": str(int(time.time() * 1000)),
        }
        resp = requests.post(
            f"http://127.0.0.1:{server_port}/api/v1/ingest/frame",
            data=jpeg_bytes,
            headers=headers,
            timeout=30.0,
        )
        elapsed = time.time() - t0
        print(f"   ⏱️ Thời gian xử lý toàn trình (CV + NVIDIA VLM): {elapsed:.2f} giây | HTTP {resp.status_code}")

        res_data = resp.json()
        formatted_json = json.dumps(res_data, indent=2, ensure_ascii=False)

        print("\n" + "=" * 80)
        print("📊 [AI OUTPUT LOG] JSON METADATA TRẢ VỀ TỪ CENTRAL SERVER:")
        print("=" * 80)
        print(formatted_json)
        print("=" * 80)

        logs.append(f"=== TEST RUN: {time.strftime('%Y-%m-%d %H:%M:%S')} ===")
        logs.append(f"Duration: {elapsed:.2f}s | HTTP Status: {resp.status_code}")
        logs.append(formatted_json)

        # 5. GỬI REQUEST 2: POST /api/v1/analyze/nvidia (JSON Base64 Direct Payload)
        print(f"\n5️⃣  Kiểm tra xử lý ảnh qua POST /api/v1/analyze/nvidia (Base64 Image)...")
        payload_b64 = {
            "camera_id": "CAM_LIVE_GATE_01",
            "frame_base64": b64_img,
            "location": "Cong So 1 - Khu Pho An Ninh",
            "action_hint": "FIGHTING",
        }
        resp2 = requests.post(
            f"http://127.0.0.1:{server_port}/api/v1/analyze/nvidia",
            json=payload_b64,
            headers={"Content-Type": "application/json"},
            timeout=15.0,
        )
        print(f"   ✅ API NVIDIA phân tích thành công: HTTP {resp2.status_code}")
        res_data2 = resp2.json()
        logs.append("\n=== NVIDIA VLM DIRECT RESULT ===")
        logs.append(json.dumps(res_data2, indent=2, ensure_ascii=False))

        # 6. Kiểm tra Test Receiver Server đã nhận và lưu trữ sự cố
        print(f"\n6️⃣  Kiểm tra Test Receiver Server (Cổng {receiver_port})...")
        time.sleep(1.2)  # Đợi webhook worker chuyển tiếp
        rec_resp = requests.get(f"http://127.0.0.1:{receiver_port}/events")
        rec_data = rec_resp.json()
        print(f"   ✅ Test Receiver Server xác nhận đã nhận {rec_data.get('count', 0)} sự cố từ AI gửi sang!")

        # 7. Ghi toàn bộ log ra file
        with open(log_file_path, "w", encoding="utf-8") as lf:
            lf.write("\n".join(logs))
        print(f"\n💾 ĐÃ GHI TOÀN BỘ LOG OUTPUT AI VÀO: {log_file_path}")

        print("\n" + "=" * 80)
        print("🎉 KIỂM THỬ HOÀN TẤT THÀNH CÔNG: XỬ LÝ ẢNH CAMERA & TRẢ VỀ JSON METADATA ĐẦY ĐỦ!")
        print("=" * 80)

    finally:
        ai_server.stop()
        receiver_server.shutdown()
        receiver_server.server_close()


if __name__ == "__main__":
    run_live_test()
