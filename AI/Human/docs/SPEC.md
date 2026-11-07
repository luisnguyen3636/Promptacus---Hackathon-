# TÀI LIỆU ĐẶC TẢ KỸ THUẬT (TECHNICAL SPECIFICATION)
## URBAN SAFETY AI-SOC: CHỨNG THỰC TOÀN VẸN BẰNG CHỨNG HÌNH ẢNH (SHA-256 + TIMESTAMP) & TOÀN BỘ METADATA ĐỐI TƯỢNG (FORENSIC EVIDENCE INTEGRITY & COMPREHENSIVE SUBJECT TELEMETRY)
**Mã đặc tả:** `SPEC-URBANSOC-DISPATCH-05`  
**Dự án:** Hệ thống Giám sát An ninh & An toàn Đô thị Thông minh (Urban Safety AI-SOC)  
**Phương pháp luận:** Spec-Driven Development (SDD) & Strict Human-in-the-Loop (AGENTS.md)  
**Tác giả:** AI Assistant (dưới quyền Lead Developer / Principal Architect)  
**Trạng thái:** Chờ phê duyệt (Awaiting Approval)

---

## 1. TỔNG QUAN YÊU CẦU & BỔ SUNG TỪ PRINCIPAL ARCHITECT

### 1.1. Yêu cầu Bổ sung từ Lead Developer
> *"bạn gửi thiếu rồi, bạn phải gửi tất cả mọi thứ về đối tượng , hình ảnh là quan trọng nhất, bạn phải gửi kèm cả mã hash sha256 của hình ảnh (nhớ hash + timestamp)"*

### 1.2. Mục tiêu Kỹ thuật Nâng cấp
1. **Chứng thực Toàn vẹn Chuỗi Bằng chứng Tư pháp (Chain of Custody / Cryptographic Tamper-Proof):**
   - Hình ảnh là bằng chứng pháp lý quan trọng nhất trong hệ thống AI-SOC giám sát an ninh trật tự.
   - Để ngăn ngừa giả mạo, chỉnh sửa hoặc thay thế bằng chứng sau khi phát hiện, hệ thống tạo mã băm mật mã học **SHA-256** kết hợp giữa **dữ liệu byte ảnh thô (RAW JPEG bytes)** và **dấu thời gian (Timestamp Milliseconds)**:
     $$\text{SHA256}_{\text{forensic}} = \mathcal{H}_{\text{sha256}}\left(\text{ImageBytes} \,\|\, \text{TimestampStringOrEpoch}\right)$$
   - Áp dụng độc lập cho cả:
     - **`full_image` (Ảnh toàn cảnh hiện trường)**: trường `sha256_hash` kèm `image_size_bytes`.
     - **Từng `subject` (Ảnh cắt riêng từng đối tượng)**: trường `crop_image_sha256` kèm `crop_image_size_bytes`.
2. **Gửi Trọn Vẹn Tất Cả Mọi Thông Tin Về Đối Tượng (All Subject Telemetry):**
   Không chỉ gửi tọa độ thô, hệ thống trích xuất toàn bộ dữ liệu sinh trắc học và động học chuyên sâu:
   - **Định danh & Trạng thái:** `track_id`, `role` (`suspect`, `victim`, `participant`, `bystander`), `behavior`, `threat_level`, `threat_score`, `confidence`.
   - **Kích thước & Hình học Hộp bao:** `bbox: [x1, y1, x2, y2]`, `bbox_width`, `bbox_height`, `bbox_aspect_ratio`, `bbox_area`.
   - **Lưu trú & Di chuyển:** `dwell_time_seconds` (thời gian đã lảng vảng/hiện diện), `speed` (tốc độ chuẩn hóa và tốc độ px/s), `velocity_vector: [vx, vy]`.
   - **Động học & Sinh trắc học Không gian (Kinematics Telemetry):**
     - Góc nghiêng cột sống `spine_angle`.
     - Vận tốc & động năng cổ tay `wrist_velocity`.
     - Góc khuỷu tay trái/phải `left_elbow_angle`, `right_elbow_angle`.
     - Độ vươn tay trái/phải chuẩn hóa `left_arm_extension`, `right_arm_extension`.
     - Khoảng cách hội tụ giữa 2 cổ tay `wrist_distance` (nhận diện cầm vũ khí 2 tay).
   - **Toàn bộ 17 Khớp Xương Tư Thế (Full 17 COCO Keypoints):** Danh sách đầy đủ tọa độ `(x, y)` và độ tin cậy `confidence` của từng khớp (Mũi, Mắt, Tai, Vai, Khuỷu tay, Cổ tay, Hông, Đầu gối, Cổ chân).
   - **Hình ảnh Cắt & Mã Hash:** `crop_image_base64`, `crop_image_sha256`, `crop_image_size_bytes`.

---

## 2. THIẾT KẾ CẤU TRÚC JSON SCHEMA ĐẦU RA (PAYLOAD CONTRACT)

Gói HTTP POST payload gửi đi đạt chuẩn:

```json
{
  "event_id": "EVT_20261107_145500_a1b2c3d4",
  "timestamp": "2026-11-07T14:55:00.123456",
  "timestamp_ms": 1794038100123,
  "camera": {
    "camera_id": "CAM_01",
    "name": "Cổng Chính - Phố Đi Bộ",
    "zone_id": "ZONE_ALPHA",
    "address": "Nguyễn Huệ, Quận 1, TP.HCM",
    "latitude": 10.776889,
    "longitude": 106.700806
  },
  "detection": {
    "primary_action": "WEAPON_THREAT",
    "threat_level": "CRITICAL",
    "threat_score": 0.96,
    "is_urgent": true,
    "reasoning": "Detected tactical two-handed aiming posture with converged wrists.",
    "weapon": {
      "is_weapon_detected": true,
      "weapon_types": ["TACTICAL_WEAPON_POSTURE"],
      "confidence": 0.95,
      "description": "Tactical pointing stance detected"
    },
    "subjects": [
      {
        "track_id": 1,
        "role": "suspect",
        "behavior": "WEAPON_THREAT",
        "threat_level": "CRITICAL",
        "threat_score": 0.96,
        "confidence": 0.92,
        "bbox": [180, 110, 310, 440],
        "bbox_width": 130,
        "bbox_height": 330,
        "bbox_aspect_ratio": 2.54,
        "bbox_area": 42900,
        "dwell_time_seconds": 4.25,
        "speed": 0.35,
        "velocity_vector": [1.2, -0.4],
        "kinematics": {
          "spine_angle": 12.5,
          "aspect_ratio": 2.54,
          "wrist_velocity": 45.0,
          "left_elbow_angle": 162.0,
          "right_elbow_angle": 158.0,
          "left_arm_extension": 0.42,
          "right_arm_extension": 0.40,
          "wrist_distance": 22.5
        },
        "keypoints": [
          {"id": 0, "name": "nose", "x": 245.0, "y": 135.0, "confidence": 0.98},
          {"id": 5, "name": "left_shoulder", "x": 225.0, "y": 175.0, "confidence": 0.95},
          {"id": 6, "name": "right_shoulder", "x": 265.0, "y": 175.0, "confidence": 0.96},
          {"id": 9, "name": "left_wrist", "x": 248.0, "y": 210.0, "confidence": 0.94},
          {"id": 10, "name": "right_wrist", "x": 252.0, "y": 212.0, "confidence": 0.93}
        ],
        "crop_image_base64": "data:image/jpeg;base64,/9j/4AAQSkZJRg...",
        "crop_image_sha256": "8f4a1c2d3e...",
        "crop_image_size_bytes": 24580
      }
    ],
    "full_image": {
      "format": "jpeg",
      "width": 640,
      "height": 480,
      "image_base64": "data:image/jpeg;base64,/9j/4AAQSkZJRg...",
      "sha256_hash": "a5e8c1b9f0...",
      "image_size_bytes": 62450
    },
    "audio": {
      "is_audio_active": false,
      "audio_threat_detected": false
    }
  },
  "audit": {
    "frame_index": 42,
    "human_count": 1,
    "hash_algorithm": "SHA-256 (RAW_JPEG_BYTES + TIMESTAMP_MS)",
    "verification_status": "AI_AUTO_DETECTED_PENDING_SOC_CONFIRMATION"
  }
}
```

---

## 3. CƠ CHẾ SINH MÃ BĂM MẬT MÃ HỌC (HASH GENERATION LOGIC)

```python
import hashlib

def compute_image_forensic_hash(image_bytes: bytes, timestamp_ms: int) -> str:
    """Tạo mã băm SHA-256 chứng thực tính toàn vẹn kết hợp dữ liệu ảnh và dấu thời gian."""
    hasher = hashlib.sha256()
    hasher.update(image_bytes)
    hasher.update(str(timestamp_ms).encode("utf-8"))
    return hasher.hexdigest()
```

---

[WAITING FOR SPEC APPROVAL]
