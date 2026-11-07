# 🛡️ URBAN SAFETY SOC (CYBERGUARD SOC v2.1)
### Hệ Thống Bảng Điều Khiển Giám Sát An Ninh & Lưu Trữ Cloudflare KV Thời Gian Thực
**Nền tảng Hiển thị & Điều hành Tập trung trên Cloudflare Edge (Cloudflare Workers + Cloudflare KV + D1 Audit + React 19)**

---

## 📖 GIỚI THIỆU TỔNG QUAN

**Urban Safety SOC** là nền tảng bảng điều khiển giám sát và điều hành an ninh đô thị thời gian thực. Website và Cloudflare Worker đóng vai trò **thuần túy là Dashboard hiển thị và điều phối tác chiến (Pure Display & Operational HITL Gateway)** — tuyệt đối không chứa dữ liệu giả (`Zero Fake Data`) và không tự chạy suy luận AI trên trình duyệt hay Worker.

Hệ thống hoạt động theo cơ chế:
1. **Server bên ngoài gửi JSON liên tục** (chứa kết quả nhận diện camera, thông số FPS, số người, danh sách `actors`, `visual_cues`, `nvidia_vlm_analysis`, `threat_score`...) lên Cloudflare Worker.
2. **Cloudflare Worker lưu trữ trực tiếp vào Cloudflare KV (`INCIDENT_CACHE`)** đồng thời đẩy thông tin thời gian thực qua WebSocket (`/ws/live-stream`) và cung cấp qua REST APIs.
3. **SOC Dashboard hiển thị trung thực 100% dữ liệu từ Server**, hỗ trợ phóng to/thu nhỏ ma trận camera 2x2 (bố cục 80% Camera / 20% Right Alert Menu Modal), xác thực Vận hành viên (**Authentication**), quản lý camera thực tế (**Device Manager**), cấu hình hệ thống lưu KV (**Settings**) và chốt chặn phê duyệt **Operational HITL (`[CD-04]`)**.

---

## ✨ TÍNH NĂNG NỔI BẬT

- **🗄️ Lưu Trữ Trực Tiếp Cloudflare KV (`INCIDENT_CACHE`) & Zero Fake Data:**
  - Không sử dụng bất kỳ dữ liệu mẫu hay thiết bị giả nào. Khi chưa có dữ liệu từ Server gửi lên, danh sách camera và sự cố hiển thị trạng thái trống chuẩn xác.
  - Ngay khi Server gửi JSON lên, cả thông tin sự cố (`kv_recent_incidents`, `incident:<id>`) và thông tin thiết bị camera (`kv_cameras`) đều được cập nhật tức thời vào Cloudflare KV.
- **🔐 Xác Thực Vận Hành Viên Đầy Đủ (Operator Authentication):**
  - Hỗ trợ đăng nhập (`POST /api/auth/login`), kiểm tra phiên (`GET /api/auth/me`) và đăng xuất (`POST /api/auth/logout`) lưu trữ phiên trực trong Cloudflare KV (`kv_session:<token>`).
  - Giao diện `AuthLoginModal` tích hợp ngay trên thanh `TopHeader` cùng chuông thông báo sự cố khẩn cấp tương tác trực tiếp.
- **🖥️ Hoàn Thiện Toàn Bộ 5 Tab Tác Chiến:**
  1. **SOC Dashboard:** Ma trận Camera trực tiếp 2x2 (tích hợp stream `LAPTOP_01` kèm proxy dự phòng), chế độ phóng to quan sát 80% Camera / 20% Right Alert Menu Modal, bảng `AlertLogModule` rút gọn, bảng `RecentThreatsTable` và nút **Xuất Báo Cáo Ca Trực (JSON)** (đã gỡ bỏ hoàn toàn nút Phòng Thủ Khẩn Cấp và các cụm thẻ AI giả).
  2. **Threat Intelligence:** Thống kê và lọc trực tiếp từ dữ liệu Server gửi lên (`action_type`, `visual_cues`: va chạm vật lý, vũ khí, người ngã gục, và danh sách `actors`: `attacker` / `victim`, tư thế, `bbox`).
  3. **Incident Feed:** Tra cứu, lọc theo cấp độ (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`) và trạng thái xử lý (`PENDING_VERIFICATION`, `OPERATOR_CONFIRMED`, `DISMISSED`), hiển thị đầy đủ `description`, `reasoning`, `recommended_action`, `actors` và `visual_cues`.
  4. **Device Manager:** Lấy 100% thông tin thật từ các camera xuất hiện trong JSON của Server (`camera_id`, `location`, `measured_fps`, `frame_index`, `human_count`, `timestamp`, `status`), hỗ trợ kiểm tra kết nối (Ping), khởi động lại (Reboot), xóa thiết bị khỏi KV và làm mới dữ liệu.
  5. **Settings:** Lưu và đồng bộ cấu hình trực tiếp với Cloudflare KV (`GET /api/settings`, `POST /api/settings`), bao gồm thông tin ca trực, URL stream camera dự phòng (`liveStreamUrl`), ngưỡng cảnh báo, thời lượng bộ đệm và Webhook điều phối.
- **🛡️ Chốt Chặn Vận Hành Viên Bắt Buộc (`[CD-04]` Operational HITL):**
  - Mọi sự cố mới từ Server gửi lên đều khởi tạo ở trạng thái `PENDING_VERIFICATION`.
  - Vận hành viên thẩm định trên `EvidencePlaybackModal` với 3 quyết định: `CONFIRM_AND_DISPATCH`, `DOWNGRADE_MONITOR`, hoặc `DISMISS_FALSE_POSITIVE`.

---

## 📥 ĐỊNH DẠNG DỮ LIỆU JSON TỪ SERVER GỬI LÊN

Server gửi liên tục bản tin JSON qua phương thức `POST` tới một trong các đường dẫn:
- `POST /api/v1/ai/detection`
- `POST /api/incidents`
- `POST /api/v1/webhook`
- `POST /api/ingest`
- `POST /api/update`

### Ví dụ Payload Chuẩn từ Server:
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
  "image": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD...",
  "image_base64": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD...",
  "subject_crop_base64": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD...",
  "hand_crop_base64": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD...",
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
        "crop_image_base64": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD...",
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

---

## 🚀 HƯỚNG DẪN CÀI ĐẶT & KHỞI CHẠY

### 1. Cài đặt Dependencies
```bash
pnpm install
```

### 2. Chạy Môi trường Phát triển (Local Dev)
```bash
pnpm run dev
```
- **Cloudflare Worker & REST/WebSocket Gateway:** `http://127.0.0.1:8787`
- **React 19 Frontend Dashboard:** `http://localhost:5173`

### 3. Build Toàn bộ Dự án (Frontend + Worker Typecheck)
```bash
pnpm run build
```

---

## 📡 DANH SÁCH REST APIS CHÍNH

| Phương thức & Endpoint | Mô tả chức năng |
|---|---|
| `POST /api/v1/ai/detection` (hoặc `/api/incidents`, `/api/ingest`) | Nhận JSON từ Server, lưu sự cố và thông tin camera vào Cloudflare KV (`INCIDENT_CACHE`), phát WebSocket |
| `GET /api/get-incident` (hoặc `/api/incidents/recent`) | Đọc danh sách sự cố đã lưu từ Cloudflare KV (`kv_recent_incidents`) |
| `GET /api/devices/cameras` | Đọc danh sách camera thực tế từ Cloudflare KV (`kv_cameras`) |
| `DELETE /api/devices/cameras/:id` | Xóa một camera khỏi danh mục trong Cloudflare KV |
| `GET /api/v1/cameras/:id/stream` | Proxy luồng MJPEG video trực tiếp từ biến `LIVE_CAMERA_STREAM_URL` hoặc `?url=` |
| `POST /api/cameras/:id/ptz` | Điều khiển PTZ / Reboot / Ping camera thực tế |
| `GET /api/soc/overview` | Lấy chỉ số tổng quan tính toán thực tế từ các camera và sự cố trong KV |
| `POST /api/incidents/:id/verify` | Chốt chặn xác thực Vận hành viên HITL (`CONFIRM_AND_DISPATCH`, `DOWNGRADE_MONITOR`, `DISMISS_FALSE_POSITIVE`) |
| `POST /api/auth/login` | Đăng nhập phiên trực Vận hành viên SOC và lưu token vào KV |
| `GET /api/auth/me` | Kiểm tra phiên đăng nhập hiện tại từ token |
| `POST /api/auth/logout` | Đăng xuất và xóa phiên khỏi KV |
| `GET /api/settings` & `POST /api/settings` | Đọc và lưu cấu hình hệ thống trong Cloudflare KV (`kv_settings`) |
