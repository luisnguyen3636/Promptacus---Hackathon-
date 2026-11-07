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
  "status": "processed",
  "camera_id": "LAPTOP_01",
  "location": "Cổng Phía Đông - Khu Vực Giám Sát An Ninh",
  "timestamp": "2026-11-08T00:16:35.412Z",
  "measured_fps": 15.2,
  "frame_index": 142,
  "human_count": 2,
  "severity": "critical",
  "action_type": "FIGHTING",
  "threat_score": 0.94,
  "confidence": 0.92,
  "is_urgent": true,
  "description": "Phát hiện ẩu đả bạo lực: Người A có hành vi tấn công vật lý vào vùng đầu của Người B.",
  "reasoning": "Đối tượng Track #1 trong tư thế vung tay đấm áp sát, Đối tượng Track #2 trong tư thế lùi lại tự vệ đỡ đòn. Xuất hiện va chạm vật lý trực diện giữa 2 người.",
  "recommended_action": "DISPATCH_SECURITY",
  "actors": [
    {
      "id": 1,
      "role": "attacker",
      "action": "punching",
      "posture": "Tư thế đứng thẳng nghiêng người về phía trước, tay phải vung đấm",
      "interacting_with": 2,
      "bbox": [180, 95, 340, 480]
    },
    {
      "id": 2,
      "role": "victim",
      "action": "defending",
      "posture": "Hai tay giơ lên che mặt đỡ đòn, trọng tâm lùi về phía sau",
      "interacting_with": 1,
      "bbox": [320, 110, 470, 490]
    }
  ],
  "visual_cues": {
    "weapons_visible": false,
    "physical_contact": true,
    "fallen_person": false
  },
  "nvidia_vlm_analysis": {
    "severity": "critical",
    "timestamp": "2026-11-08T00:16:35.412Z",
    "action_type": "FIGHTING",
    "confidence": 0.92,
    "threat_score": 0.94,
    "description": "Phát hiện ẩu đả bạo lực giữa hai cá nhân.",
    "reasoning": "Hình ảnh ghi nhận cử động đấm và đỡ đòn cự ly gần ở khu vực trung tâm khung hình.",
    "actors": [
      { "id": 1, "role": "attacker", "action": "punching", "posture": "standing aggressive" },
      { "id": 2, "role": "victim", "action": "defending", "posture": "blocking stance" }
    ],
    "visual_cues": {
      "weapons_visible": false,
      "physical_contact": true,
      "fallen_person": false
    },
    "recommended_action": "DISPATCH_SECURITY",
    "is_urgent": true,
    "camera_id": "LAPTOP_01",
    "location": "Cổng Phía Đông - Khu Vực Giám Sát An Ninh",
    "source": "nvidia_nim_vlm"
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
