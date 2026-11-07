# SPEC — CẬP NHẬT SCHEMA JSON NHẬN TỪ SERVER & LƯU TRỮ CLOUDFLARE KV
**Mã tài liệu:** `SPEC-SERVER-JSON-V2`  
**Trạng thái:** `[SPEC AUTO-APPROVED]`

---

## 1. MỤC TIÊU
Cập nhật toàn diện tầng tiếp nhận dữ liệu từ Server (Cloudflare Worker + KV Storage) và tầng hiển thị trên Dashboard (React 19) để tương thích 100% với cấu trúc JSON thực tế mới nhất từ Server gửi lên:

```json
{
  "event_id": "EVT_20261108_042450_f8a92b1c",
  "timestamp": "2026-11-08T04:24:50.123456",
  "timestamp_ms": 1794111890123,
  "camera_id": "LAPTOP_01",
  "camera_name": "Laptop Chief (DEVICE)",
  "cameraId": "LAPTOP_01",
  "title": "Cảnh báo: WEAPON_THREAT (CRITICAL)",
  "severity": "CRITICAL",
  "primary_action": "WEAPON_THREAT",
  "threat_level": "CRITICAL",
  "threat_score": 0.95,
  "is_urgent": true,
  "action_confirmed": true,
  "ai_verified": true,
  "action_validation": {
    "is_valid": true,
    "validation_source": "nvidia_nim_vlm_multimodal",
    "detected_action": "WEAPON_THREAT",
    "severity": "CRITICAL",
    "threat_score": 0.95,
    "benign_hypothesis_probability": 0.08,
    "reasoning": "AI xác nhận hành vi nguy hiểm 'WEAPON_THREAT' trên hình ảnh đối tượng. Tư thế 2 tay chĩa thẳng về phía trước, phản xạ đối kháng rõ rệt."
  },
  "reasoning": "Detected action: WEAPON_THREAT. Subject aiming posture with 2-handed forward grip. Falsification passed with high tactical confidence.",
  "vlmAnalysis": "Detected action: WEAPON_THREAT. Subject aiming posture with 2-handed forward grip. Falsification passed with high tactical confidence.",
  "weapon_info": {
    "is_weapon_detected": true,
    "weapon_types": ["TACTICAL_WEAPON_POSTURE"],
    "confidence": 0.95,
    "description": "Tactical pointing or overhead strike stance detected"
  },
  "image": "data:image/jpeg;base64,...",
  "image_base64": "data:image/jpeg;base64,...",
  "subject_crop_base64": "data:image/jpeg;base64,...",
  "hand_crop_base64": "data:image/jpeg;base64,...",
  "forensic_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "image_url": "/api/v1/incidents/EVT_20261108_042450_f8a92b1c/image.jpg",
  "hand_crop_url": "/api/v1/incidents/EVT_20261108_042450_f8a92b1c/hand_crop.jpg",
  "camera": {
    "camera_id": "LAPTOP_01",
    "name": "Laptop Chief (DEVICE)",
    "zone_id": "ZONE_DEFAULT",
    "address": "Khu vực Giám sát Trung tâm",
    "latitude": 10.776889,
    "longitude": 106.700806
  },
  "detection": {
    "action_confirmed": true,
    "ai_verified": true,
    "primary_action": "WEAPON_THREAT",
    "threat_level": "CRITICAL",
    "threat_score": 0.95,
    "is_urgent": true,
    "reasoning": "Detected action: WEAPON_THREAT. Subject aiming posture with 2-handed forward grip.",
    "weapon": {
      "is_weapon_detected": true,
      "weapon_types": ["TACTICAL_WEAPON_POSTURE"],
      "confidence": 0.95
    },
    "subjects": [
      {
        "track_id": 1,
        "role": "suspect",
        "behavior": "WEAPON_THREAT",
        "threat_level": "CRITICAL",
        "threat_score": 0.95,
        "confidence": 0.95,
        "bbox": [120, 80, 450, 420],
        "speed": 0.35,
        "velocity_vector": [0.05, -0.02],
        "kinematics": {
          "spine_angle": 12.5,
          "left_elbow_angle": 168.0,
          "right_elbow_angle": 172.0,
          "left_arm_extension": 0.58,
          "right_arm_extension": 0.61
        },
        "keypoints": [
          {"id": 0, "name": "nose", "x": 280.0, "y": 110.0, "confidence": 0.92},
          {"id": 9, "name": "left_wrist", "x": 380.0, "y": 210.0, "confidence": 0.88},
          {"id": 10, "name": "right_wrist", "x": 385.0, "y": 215.0, "confidence": 0.89}
        ],
        "crop_image_base64": "data:image/jpeg;base64,...",
        "crop_image_sha256": "3a7b9c1d...",
        "crop_image_size_bytes": 14280
      }
    ],
    "audio": {
      "is_audio_active": false,
      "audio_threat_detected": false
    }
  },
  "audit": {
    "frame_index": 145,
    "human_count": 1,
    "action_confirmed": true,
    "ai_verified": true,
    "ai_model": "YOLOv11-Pose + NVIDIA NIM Llama-3.2-90B Vision",
    "hash_algorithm": "SHA-256 (RAW_JPEG_BYTES + TIMESTAMP_MS)",
    "verification_status": "AUTO_DISPATCHED_TO_AI_MODEL"
  }
}
```

## 2. ĐẶC TẢ XỬ LÝ & ÁNH XẠ DỮ LIỆU
1. **Tầng Camera (`camera_manager.ts` -> KV `kv_cameras`):**
   - Trích xuất `camera_id` từ `payload.camera_id || payload.cameraId || payload.camera?.camera_id`.
   - Trích xuất `name` từ `payload.camera_name || payload.camera?.name`, `zoneId` từ `payload.camera?.zone_id`, `address`/`location` từ `payload.camera?.address || payload.location`, tọa độ GPS (`latitude`, `longitude`) từ `payload.camera`.
   - Trích xuất `frameIndex` từ `payload.audit?.frame_index ?? payload.frame_index`, `humanCount` từ `payload.audit?.human_count ?? payload.human_count ?? payload.detection?.subjects?.length`.
   - Chuyển đổi `payload.detection.subjects` (gồm `track_id`, `role`, `behavior`, `bbox`, `confidence`, `keypoints`, `kinematics`) thành `boundingBoxes` chuẩn hóa `[0.0 - 1.0]` kèm `keypoints` để hiển thị trực tiếp trên `CameraSlot`.
2. **Tầng Sự Cố (`incident_manager.ts` -> KV `kv_recent_incidents` & `incident:<event_id>`):**
   - Lưu đầy đủ các trường mới trong `IIncidentItem`:
     - `eventId`, `timestamp`, `timestampMs`, `cameraId`, `cameraName`, `title`, `severity`, `primaryAction` / `actionType`, `threatLevel`, `threatScore`, `isUrgent`
     - `actionConfirmed`, `aiVerified`, `actionValidation` (`validation_source`, `detected_action`, `benign_hypothesis_probability`, `reasoning`)
     - `reasoning`, `vlmAnalysis` (kết hợp cả `action_validation.reasoning` và `reasoning` gốc)
     - `weaponInfo` (`is_weapon_detected`, `weapon_types`, `confidence`, `description`)
     - `imageBase64` (`payload.image || payload.image_base64`), `subjectCropBase64` (`payload.subject_crop_base64 || subjects[0]?.crop_image_base64`), `handCropBase64` (`payload.hand_crop_base64`), `forensicSha256` (`payload.forensic_hash`), `imageUrl`, `handCropUrl`
     - `cameraMeta` (`zone_id`, `address`, `latitude`, `longitude`)
     - `subjects` (kèm `kinematics`: `spine_angle`, `left_elbow_angle`, `right_elbow_angle`, `left_arm_extension`, `right_arm_extension`, `speed`, `velocity_vector`, `keypoints`, `crop_image_base64`)
     - `audioInfo` (`is_audio_active`, `audio_threat_detected`)
     - `auditInfo` (`frame_index`, `human_count`, `action_confirmed`, `ai_verified`, `ai_model`, `hash_algorithm`, `verification_status`)
     - Tự động tổng hợp `actors` và `visualCues` từ `detection.subjects` và `weapon_info` để toàn bộ bảng thống kê trên `ThreatIntelligenceView` và `IncidentFeedView` hoạt động đồng nhất.
3. **Endpoint Phục Vụ Ảnh Trực Tiếp từ KV:**
   - Hỗ trợ `GET /api/v1/incidents/:id/image.jpg`, `GET /api/v1/incidents/:id/hand_crop.jpg`, `GET /api/v1/incidents/:id/subject_crop.jpg` giải mã Base64 từ sự cố trong KV và trả về `image/jpeg` chuẩn xác.
4. **Chốt Chặn HITL (`[CD-04]`):**
   - Mọi sự cố mới nhận từ Server (kể cả khi `audit.verification_status === "AUTO_DISPATCHED_TO_AI_MODEL"` và `ai_verified === true`) vẫn phải khởi tạo trạng thái vận hành `status: "PENDING_VERIFICATION"` để Vận hành viên SOC xác nhận trước khi phát lệnh điều phối tới cơ quan chức năng.
