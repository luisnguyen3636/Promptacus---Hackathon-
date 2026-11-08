#!/usr/bin/env python3
"""Script gửi POST Request kiểm thử trực tiếp tới Endpoint Sự Cố (UrbanStrike / AI Model).

Cách sử dụng:
    python3 scripts/test_post_endpoint.py
    python3 scripts/test_post_endpoint.py --url https://urbanstrike.tech/api/incident
    python3 scripts/test_post_endpoint.py --action KNIFE_THREAT
"""

import argparse
import base64
import json
import os
import sys
import time
import uuid

import cv2
import numpy as np
import requests

# Ensure src is in sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_dir = os.path.join(root_dir, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from urbansoc.config import HARDCODED_MODEL_URL
from urbansoc.telemetry.webhook_dispatcher import encode_image_and_hash


def send_test_incident(
    target_url: str = HARDCODED_MODEL_URL,
    action: str = "KNIFE_THREAT",
    camera_id: str = "LAPTOP_01",
) -> bool:
    print("=" * 76)
    print(f"🚀 GỬI TEST POST REQUEST TỚI ENDPOINT: {target_url}")
    print("=" * 76)

    # 1. Tạo ảnh giả lập hiện trường có BBox và cảnh báo
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.rectangle(frame, (180, 80), (460, 420), (0, 0, 255), 3)
    cv2.putText(
        frame,
        f"URBAN SAFETY AI-SOC: {action} DETECTED",
        (30, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 0, 255),
        2,
    )
    cv2.putText(
        frame,
        "Track ID: #1 | Threat: CRITICAL (0.98)",
        (190, 70),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (0, 255, 255),
        2,
    )

    # Vùng tay cầm hung khí
    cv2.circle(frame, (400, 220), 30, (0, 0, 255), 2)
    cv2.putText(
        frame,
        "SHARP OBJECT ROI",
        (340, 180),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (0, 0, 255),
        2,
    )

    hand_crop = frame[160:280, 340:460]

    now_ms = int(time.time() * 1000)
    iso_ts = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()) + "+07:00"
    event_id = f"EVT_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

    full_b64, full_hash, full_size = encode_image_and_hash(frame, timestamp_ms=now_ms)
    hand_b64, hand_hash, hand_size = encode_image_and_hash(hand_crop, timestamp_ms=now_ms)

    ai_prompt = (
        f"URBAN SAFETY AI-SOC SURVEILLANCE EVENT [{event_id} | CAMERA: {camera_id}]:\n"
        f"Detected action: {action} (Threat: CRITICAL, Score: 0.98).\n"
        f"Task for DeepSeek VLM: Please inspect the attached surveillance frame and zoomed hand crop:\n"
        f"1. Is the subject wielding a knife, blade, or sharp object?\n"
        f"2. Confirm weapon classification and threat posture."
    )

    payload = {
        "event_id": event_id,
        "timestamp": iso_ts,
        "timestamp_ms": now_ms,
        "camera_id": camera_id,
        "cameraId": camera_id,
        "camera_name": f"{camera_id} - Zone Monitor",
        "title": f"Cảnh báo: {action} (CRITICAL)",
        "severity": "CRITICAL",
        "primary_action": action,
        "threat_level": "CRITICAL",
        "threat_score": 0.98,
        "is_urgent": True,
        "reasoning": f"Phát hiện hành vi nguy hiểm {action} với dấu hiệu tấn công trực diện",
        "vlmAnalysis": f"Phát hiện hành vi nguy hiểm {action} với dấu hiệu tấn công trực diện",
        "weapon_info": {
            "is_weapon_detected": True,
            "weapon_types": ["SHARP_OBJECT_KNIFE" if "KNIFE" in action else "TACTICAL_WEAPON"],
            "confidence": 0.98,
            "description": "Tactical stance identified by Urban Safety SOC Behavior Engine",
        },
        "image": full_b64,
        "image_base64": full_b64,
        "hand_crop_base64": hand_b64,
        "ai_prompt": ai_prompt,
        "deepseek_message": {
            "role": "user",
            "content": [
                {"type": "text", "text": ai_prompt},
                {"type": "image_url", "image_url": {"url": full_b64}},
                {"type": "image_url", "image_url": {"url": hand_b64}},
            ],
        },
        "forensic_hash": full_hash,
        "audit": {
            "verification_status": "AUTO_DISPATCHED_TO_AI_MODEL",
            "hash_algorithm": "SHA-256 (RAW_JPEG_BYTES + TIMESTAMP_MS)",
        },
    }

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "UrbanSafety-AI-SOC/2.0 WebhookDispatcher",
    }

    print(f"• Event ID:        {event_id}")
    print(f"• Tiêu đề:         {payload['title']}")
    print(f"• Hành vi:         {action}")
    print(f"• Camera ID:       {camera_id}")
    print(f"• Forensic Hash:   {full_hash[:16]}... (SHA-256)")
    print(f"• Kích thước body: {len(json.dumps(payload))} bytes")
    print("-" * 76)

    t0 = time.time()
    try:
        resp = requests.post(target_url, json=payload, headers=headers, timeout=12.0)
        dt = (time.time() - t0) * 1000

        print(f"📥 KẾT QUẢ PHẢN HỒI (HTTP {resp.status_code} | Độ trễ: {dt:.1f}ms):")
        try:
            resp_data = resp.json()
            print(json.dumps(resp_data, indent=2, ensure_ascii=False))
        except Exception:
            print(resp.text[:500])

        if 200 <= resp.status_code < 300:
            print("\n✅ POST REQUEST THÀNH CÔNG! Dữ liệu đã được lưu vết trên máy chủ.")
            return True
        else:
            print(f"\n❌ Máy chủ phản hồi mã lỗi: {resp.status_code}")
            return False
    except Exception as e:
        print(f"\n❌ LỖI KẾT NỐI: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Test POST Incident to Endpoint")
    parser.add_argument("--url", type=str, default=HARDCODED_MODEL_URL, help=f"Target endpoint URL (default: {HARDCODED_MODEL_URL})")
    parser.add_argument("--action", type=str, default="KNIFE_THREAT", help="Incident action (default: KNIFE_THREAT)")
    parser.add_argument("--camera", type=str, default="LAPTOP_01", help="Camera ID (default: LAPTOP_01)")
    args = parser.parse_args()

    success = send_test_incident(target_url=args.url, action=args.action, camera_id=args.camera)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
