#!/usr/bin/env python3
"""Script kiểm thử gửi POST Request lên Server Trung Gian / Giả Lập Urban Safety AI-SOC.

Chạy kiểm thử:
    python3 scripts/send_test_post.py --server-url http://localhost:8000
"""

import argparse
import base64
import hashlib
import json
import os
import sys
import time
from typing import Dict, Any
from urllib.parse import quote

import cv2
import numpy as np
import requests


def compute_forensic_sha256(raw_bytes: bytes, timestamp_ms: int) -> str:
    """Tính mã băm mật mã học SHA-256(raw_bytes + timestamp_ms) chuẩn SOC."""
    hasher = hashlib.sha256()
    hasher.update(raw_bytes)
    hasher.update(str(timestamp_ms).encode("utf-8"))
    return hasher.hexdigest()


def test_post_requests(server_url: str = "http://localhost:8000") -> bool:
    server_url = server_url.rstrip("/")
    print("=" * 76)
    print("🚀 [TEST POST REQUESTS] BẮT ĐẦU GỬI POST LÊN SERVER URBAN SAFETY AI-SOC")
    print("=" * 76)
    print(f"• Target Server URL: {server_url}")

    # 1. Test POST Đăng ký Camera (/api/v1/cameras/register)
    print("\n[TEST 1] Gửi POST /api/v1/cameras/register (Đăng ký Camera mới)...")
    reg_url = f"{server_url}/api/v1/cameras/register"
    reg_payload = {
        "camera_id": "LAPTOP_DEMO_01",
        "name": "Laptop Cổng Đông (Demo)",
        "latitude": 10.776889,
        "longitude": 106.700806,
        "address": "Cổng Đông - Tòa Nhà Trung Tâm",
        "fps": 15.0,
    }
    try:
        resp1 = requests.post(reg_url, json=reg_payload, timeout=3.0)
        print(f"   HTTP Status: {resp1.status_code}")
        print(f"   Server Response: {resp1.json()}")
        assert resp1.status_code == 200, f"Đăng ký thất bại với mã {resp1.status_code}"
    except Exception as e:
        print(f"❌ [LỖI TEST 1]: Không thể kết nối tới server tại {reg_url}: {e}")
        return False

    # 2. Test POST Truyền Khung Hình (/api/v1/ingest/frame)
    print("\n[TEST 2] Gửi POST /api/v1/ingest/frame (Truyền Frame Binary JPEG)...")
    ingest_url = f"{server_url}/api/v1/ingest/frame"
    
    # Tạo frame giả lập có đánh dấu đồ họa
    test_frame = np.full((360, 480, 3), 35, dtype=np.uint8)
    cv2.rectangle(test_frame, (80, 60), (400, 300), (0, 200, 255), 2)
    cv2.putText(
        test_frame,
        "POST TEST STREAM - LAPTOP_DEMO_01",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (0, 255, 200),
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        test_frame,
        f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        (20, 330),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.45,
        (180, 180, 180),
        1,
        cv2.LINE_AA,
    )

    success, enc = cv2.imencode(".jpg", test_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
    raw_jpeg = enc.tobytes()
    now_ms = int(time.time() * 1000)

    headers = {
        "Content-Type": "image/jpeg",
        "X-Camera-ID": "LAPTOP_DEMO_01",
        "X-Camera-Name": quote("Laptop Cổng Đông (Demo)"),
        "X-Timestamp-Ms": str(now_ms),
    }

    try:
        resp2 = requests.post(ingest_url, data=raw_jpeg, headers=headers, timeout=3.0)
        print(f"   HTTP Status: {resp2.status_code}")
        print(f"   Dữ liệu trả về từ AI Engine: {resp2.json()}")
        assert resp2.status_code == 200, f"Truyền frame thất bại với mã {resp2.status_code}"
    except Exception as e:
        print(f"❌ [LỖI TEST 2]: {e}")
        return False

    # 3. Test POST Webhook Cảnh báo Sự cố kèm mã băm Forensic SHA-256 (/api/v1/incidents)
    print("\n[TEST 3] Gửi POST /api/v1/incidents (Báo động Sự Cố kèm Forensic SHA-256)...")
    inc_url = f"{server_url}/api/v1/incidents"
    ts_ms = int(time.time() * 1000)

    # Tạo ảnh sự cố và tính mã băm SHA-256
    incident_img = np.full((240, 320, 3), 40, dtype=np.uint8)
    cv2.putText(
        incident_img,
        "CRITICAL ALERT: WEAPON_THREAT DETECTED",
        (10, 120),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.45,
        (0, 0, 255),
        1,
        cv2.LINE_AA,
    )
    _, enc_inc = cv2.imencode(".jpg", incident_img)
    inc_bytes = enc_inc.tobytes()
    expected_sha256 = compute_forensic_sha256(inc_bytes, ts_ms)
    inc_b64 = "data:image/jpeg;base64," + base64.b64encode(inc_bytes).decode("utf-8")

    event_id = f"EVT_TEST_{time.strftime('%Y%m%d_%H%M%S')}"

    incident_payload: Dict[str, Any] = {
        "event_id": event_id,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000+07:00"),
        "timestamp_ms": ts_ms,
        "camera": {
            "camera_id": "LAPTOP_DEMO_01",
            "name": "Laptop Cổng Đông (Demo)",
            "latitude": 10.776889,
            "longitude": 106.700806,
            "address": "Cổng Đông - Tòa Nhà Trung Tâm",
        },
        "detection": {
            "primary_action": "WEAPON_THREAT",
            "threat_level": "CRITICAL",
            "threat_score": 0.98,
            "is_urgent": True,
            "reasoning": "Detected tactical weapon posture with two-handed pointing stance",
            "weapon": {
                "is_weapon_detected": True,
                "weapon_types": ["FIREARM_TACTICAL_STANCE"],
                "confidence": 0.96,
                "description": "Tactical weapon isosceles triangle posture",
            },
            "subjects": [
                {
                    "track_id": 1,
                    "role": "suspect",
                    "behavior": "WEAPON_THREAT",
                    "threat_level": "CRITICAL",
                    "threat_score": 0.98,
                    "confidence": 0.94,
                    "bbox": [120, 80, 220, 300],
                    "speed": 0.15,
                    "dwell_time_seconds": 4.5,
                }
            ],
            "full_image": {
                "format": "jpeg",
                "width": 320,
                "height": 240,
                "image_base64": inc_b64,
                "sha256_hash": expected_sha256,
            },
        },
        "audit": {
            "verification_status": "AI_AUTO_DETECTED_PENDING_SOC_CONFIRMATION",
            "human_count": 1,
        },
    }

    try:
        resp3 = requests.post(inc_url, json=incident_payload, timeout=3.0)
        print(f"   HTTP Status: {resp3.status_code}")
        res3_json = resp3.json()
        print(f"   Server Response: {res3_json}")
        assert resp3.status_code == 200, f"Gửi Webhook thất bại với mã {resp3.status_code}"
        assert res3_json.get("forensic_hash_valid") is True, "Chữ ký băm Forensic SHA-256 không hợp lệ!"
        print("   ✅ Kiểm chứng chữ ký số Forensic SHA-256 trên Server: CHÍNH XÁC (TAMPER-PROOF)")
    except Exception as e:
        print(f"❌ [LỖI TEST 3]: {e}")
        return False

    # 4. Kiểm tra GET /api/v1/cameras xác nhận trạng thái
    print("\n[TEST 4] Truy vấn GET /api/v1/cameras để kiểm tra danh sách Camera...")
    try:
        resp4 = requests.get(f"{server_url}/api/v1/cameras", timeout=3.0)
        cams = resp4.json().get("cameras", [])
        print(f"   Số lượng camera đang hoạt động: {len(cams)}")
        for c in cams:
            print(f"   ▶ [{c['camera_id']}] {c['name']} | Trạng thái: {c['status']} | Frames: {c['total_frames']} | Mức đe dọa: {c['highest_threat']}")
    except Exception as e:
        print(f"❌ [LỖI TEST 4]: {e}")
        return False

    print("\n" + "=" * 76)
    print("🎉 TOÀN BỘ CÁC BÀI TEST GỬI POST REQUEST LÊN SERVER THÀNH CÔNG 100%!")
    print("=" * 76)
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test gửi POST Request lên Server AI-SOC")
    parser.add_argument("--server-url", type=str, default="http://localhost:8000", help="URL server (default: http://localhost:8000)")
    args = parser.parse_args()

    success = test_post_requests(args.server_url)
    sys.exit(0 if success else 1)
