# 🛡️ URBAN SAFETY AI-SOC (CYBERGUARD AI v2.1)
### Hệ Thống Giám Sát An Ninh & An Toàn Đô Thị Thông Minh Thời Gian Thực
**Nền tảng Hợp nhất Edge Computing (Cloudflare Workers + D1 Database + Workers AI + React 19 + YOLO11-Pose)**

---

## 📖 GIỚI THIỆU TỔNG QUAN

**Urban Safety AI-SOC** là hệ thống giám sát và điều hành an ninh đô thị thông minh thế hệ mới, kết hợp sức mạnh của **Thị giác Máy tính Tốc độ cao (Computer Vision)**, **Phân tích Động học Khớp xương (Pose Kinematics)**, **Mô hình Đa phương thức (Multimodal VLM)** và **Hạ tầng Điện toán Biên (Edge Computing)**.

Hệ thống được thiết kế chuyên biệt nhằm giải quyết bài toán phát hiện sớm các **hành vi tiền phạm tội (Pre-crime indicators)** như: lén lút tiếp cận, rút và thủ thế hung khí, lảng vảng khu vực cấm; cũng như phản ứng thần tốc trước các **hành vi phạm tội/hậu phạm tội (Post-crime actions)** như: ẩu đả bạo lực, cướp giật, bỏ chạy tốc độ cao hoặc nạn nhân nằm bất động.

Đặc biệt, hệ thống tuân thủ nghiêm ngặt nguyên tắc **Dual Human-in-the-Loop (HITL)**: Mọi cảnh báo có độ nguy hiểm cao (`HIGH` / `CRITICAL`) đều phải qua sự xác thực của **Vận hành viên SOC (Human Operator)** trước khi tự động đóng gói hồ sơ bằng chứng gửi tới lực lượng chức năng.

---

## ✨ TÍNH NĂNG NỔI BẬT

- **🌐 Hợp nhất 100% trên Cloudflare Edge:** Không cần duy trì máy chủ VPS cồng kềnh; toàn bộ REST API, WebSocket stream trực tiếp, cơ sở dữ liệu D1 SQL và giao diện React SPA được đóng gói chạy trên mạng lưới Edge toàn cầu của Cloudflare với độ trễ `< 35ms`.
- **🎯 Nhận diện Động học Cơ thể Sâu (YOLO11-Pose Kinematics):** Phân tích 17 điểm khớp xương người, tính toán góc xoay cột sống, độ duỗi khuỷu tay, khoảng cách cổ tay và gia tốc chuyển động để phân biệt chính xác tư thế người bình thường và tư thế đe dọa vũ khí.
- **🛡️ Chốt chặn Vận hành viên Bắt buộc (Strict Operational HITL):** Bảo đảm không bao giờ phát tín hiệu báo động giả ra cơ quan chức năng. Cung cấp 3 quyền quyết định: `Xác nhận & Điều phối (CONFIRM_AND_DISPATCH)`, `Hạ mức theo dõi (DOWNGRADE_MONITOR)`, hoặc `Hủy cảnh báo giả (DISMISS_FALSE_POSITIVE)`.
- **📦 Đóng gói Bằng chứng Tư pháp Tự động (Automated Forensic Packaging):** Khi được xác nhận, hệ thống tự động xuất gói hồ sơ sự cố đầy đủ gồm tọa độ GPS, mã camera, tóm tắt phân tích hành vi AI, ảnh snapshot có khung nhận diện, ảnh crop đối tượng, mã băm SHA-256 chống giả mạo và định danh kiểm toán của Operator.
- **🤖 Phân tích Tình báo DeepSeek Batching 2 Phút (DeepSeek 2-Min Pipeline):** Toàn bộ request POST gửi về hệ thống được tự động đưa vào bộ đệm trượt 2 phút (`window_seconds = 120`). Mô hình DeepSeek mặc định (`@cf/deepseek-ai/deepseek-v4.1-flash-1017`) phân tích log và ảnh Base64, đánh giá mức độ nghiêm trọng (`severity`), mô tả động học đối tượng (`object_description`) và dòng thời gian bằng chứng (`timeline`), lưu vào D1 và cung cấp qua endpoint `GET /api/get-incident`.
- **🖥️ Giao diện Tác chiến SOC & Cụm Chỉ số AI Thời gian thực:**
  1. *SOC Dashboard:* Bảng điều khiển tác chiến trung tâm tích hợp Ma trận Camera trực tiếp (Live Camera Matrix 2x2), cơ chế quan sát cận cảnh thông minh (80% Camera Area / 20% Right Alert Menu Modal), Bảng Alert Log rút gọn cảnh báo sớm và cụm 8 thẻ chỉ số hiệu năng AI.
  2. *Threat Intelligence:* Phân tích tình báo đe dọa, thống kê phân loại hành vi và chặn IP khả nghi.
  3. *Incident Feed:* Nhật ký sự cố chi tiết kèm bộ lọc đa tiêu chí, tra cứu mã sự cố và modal bằng chứng tư pháp.
  4. *Device Manager:* Quản lý danh mục camera, kiểm tra trạng thái luồng video và khởi động lại thiết bị.
  5. *Settings:* Tùy chỉnh ngưỡng cảnh báo, cấu hình còi báo động và phân quyền vận hành.
- **📹 Tích Hợp Luồng Video Camera Trực Tiếp & Backup Edge Proxy:** Hỗ trợ nhận luồng video thời gian thực từ camera Laptop (`LAPTOP_01`). Để đảm bảo tính bền bỉ khi địa chỉ Cloudflare Tunnel thay đổi, Cloudflare Worker hỗ trợ cấu hình biến `LIVE_CAMERA_STREAM_URL` trong `wrangler.toml` và cung cấp route proxy `GET /api/v1/cameras/:id/stream` truyền phát trực tiếp dữ liệu video kèm CORS headers đầy đủ.
- **🔍 Khắc Phục Zoom Matrix 2x2 & Bố Cục 80/20 Khi Quan Sát:** Cho phép người trực click phóng to bất kỳ camera nào để quan sát cận cảnh (hỗ trợ zoom kỹ thuật số 1.0x - 3.5x qua thanh công cụ PTZ). Khi phóng to, khối camera chiếm đúng 80% chiều rộng màn hình, trong khi bảng Alert Log tự động mở rộng thành Right Menu Modal chiếm đúng 20% chiều rộng còn lại. Phím tắt `Escape` hoặc nút `2x2 Grid` đưa màn hình trở về lưới 2x2 tức thì.

---

## 🏛️ KIẾN TRÚC HỆ THỐNG 4 TẦNG

```
[Camera Streams (RTSP / Video File / Webcam)]
                     │ (Frame Grabber & Rolling Buffer)
                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ TẦNG 1: INPUT & INGESTION LAYER                                         │
│ - Thu thập video thời gian thực không nghẽn luồng (Non-blocking queue)   │
│ - Duy trì Evidence Rolling Buffer (10s trước + 10s sau sự kiện)         │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ TẦNG 2: AI / VLM ANALYTICS LAYER (AI/Human)                             │
│ - YOLO11-Pose: Nhận diện đối tượng & trích xuất 17 điểm khớp xương     │
│ - Kinematics Engine: Đo góc khuỷu tay, vận tốc cổ tay, độ duỗi cánh tay │
│ - Đóng gói ảnh Base64 JPEG + Forensic SHA-256 Hash                     │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ Webhook JSON (POST /api/v1/ai/detection)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ TẦNG 3: TRACKING & DYNAMIC THREAT SCORING (Cloudflare Edge Worker)      │
│ - Đăng ký động Camera Fleet & chuẩn hóa Bounding Box tỉ đối [0.0 - 1.0] │
│ - Dynamic Threat State Machine (LOW -> MEDIUM -> HIGH -> CRITICAL)     │
│ - Workers AI Forensic Evaluator (DeepSeek / Llama 3.2 Vision)           │
│ - WebSocket Live Broadcast (/ws/live-stream) đẩy tới Dashboard          │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ Khi Threat >= HIGH (Trạng thái: PENDING_VERIFICATION)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ TẦNG 4: OPERATIONAL HITL & DISPATCH LAYER                               │
│ - Hiển thị bằng chứng lên Evidence Playback Modal                      │
│ - Vận hành viên xác nhận: POST /api/incidents/:id/verify                │
│ - Đóng gói Tactical Incident Package gửi tới cơ quan chức năng          │
│ - Ghi nhật ký kiểm toán bất biến vào Cloudflare D1 (audit_logs table)   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ YÊU CẦU HỆ THỐNG & CÔNG NGHỆ

| Thành phần | Công nghệ sử dụng | Yêu cầu phiên bản |
|---|---|---|
| **Edge Backend** | Cloudflare Workers, TypeScript, Miniflare | Node.js `>= 20.x`, pnpm `>= 9.x`, Wrangler `>= 3.114` |
| **Cơ sở dữ liệu** | Cloudflare D1 SQL Database | Chuẩn SQLite D1 |
| **Workers AI** | Cloudflare Workers AI Binding | DeepSeek R1 / Llama 3.2 Vision Instruct |
| **Frontend SPA** | React 19, Vite 6, TailwindCSS, Canvas API | Trình duyệt hiện đại (Chrome, Edge, Firefox) |
| **AI Subsystem** | Python 3.10+, PyTorch, Ultralytics, OpenCV | Python `>= 3.10`, GPU NVIDIA (CUDA) khuyến nghị |

---

## 🚀 HƯỚNG DẪN CÀI ĐẶT & CHẠY THỬ NGHIỆM (QUICK START)

### 1. Clone Kho Mã Nguồn
```bash
git clone https://github.com/your-org/Promptacus---Hackathon-.git
cd Promptacus---Hackathon-
```

### 2. Cài Đặt Dependencies (Monorepo)
Cài đặt toàn bộ dependencies cho Root, Backend Worker và Frontend chỉ với một lệnh:
```bash
# Cài đặt qua pnpm
pnpm install

# Hoặc cài đặt độc lập từng phần nếu cần:
pnpm --dir CloudflareWorker install
pnpm --dir "Dashboard/Front End" install
```

### 3. Cài Đặt Môi Trường Python (Phân hệ AI)
```bash
cd AI/Human
python -m venv venv
# Trên Windows:
.\venv\Scripts\activate
# Trên Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
cd ../..
```

### 4. Khởi Chạy Hệ Thống Ở Môi Trường Local Dev

Tại thư mục gốc của dự án, bạn chỉ cần chạy:
```bash
pnpm run dev
```
Lệnh này sẽ khởi động đồng thời:
- **Cloudflare Worker & Live APIs:** Lắng nghe tại `http://127.0.0.1:8787`
- **Frontend SPA & Ma trận CCTV:** Phục vụ trực tiếp qua Worker hoặc cổng dev Vite `http://localhost:5173`.
- **WebSocket Broker:** Hoạt động tại `ws://127.0.0.1:8787/ws/live-stream`.

### 5. Kiểm Thử Gửi Dữ Liệu AI Vào Hệ Thống (End-to-End Simulation)
Chạy script kiểm thử tự động để bơm dữ liệu AI mẫu vào hệ thống và xác thực toàn bộ luồng:
```bash
# Kiểm thử Cloudflare KV, lưu vết Input/Output DeepSeek & đồng bộ Dashboard (24 assertions)
node --experimental-strip-types CloudflareWorker/test_kv_pipeline.mjs

# Kiểm thử lớp AI tích hợp tự động, DeepSeek API Key & Log chuẩn SOC (26 assertions)
node --experimental-strip-types CloudflareWorker/test_integrated_ai_layer.mjs

# Kiểm thử DeepSeek 2-phút & endpoint /api/get-incident (20 assertions)
node --experimental-strip-types CloudflareWorker/test_deepseek_pipeline.mjs

# Kiểm thử end-to-end webhook & incident injection
node CloudflareWorker/test_e2e.mjs
node CloudflareWorker/test_post_incidents.mjs
```

---

## 📡 DANH SÁCH REST APIS & WEBSOCKET PROTOCOL

Toàn bộ các endpoint đều hỗ trợ CORS và phản hồi theo định dạng chuẩn JSON:

### 1. Giám sát & Đo đạc Viễn thông (Telemetry & Status)
- `GET /api/soc/overview`: Lấy điểm rủi ro hiện tại (`threatScore`), mức độ cảnh báo (`threatLevel`), số sự cố đang chờ duyệt và chỉ số mạng (độ trễ, camera online, PoE load).

### 2. Quản lý Đội Camera (Camera Fleet Management)
- `GET /api/devices/cameras` (hoặc `GET /api/cameras`): Lấy danh sách toàn bộ camera đang online, tọa độ, bounding box và ảnh chụp mới nhất.
- `POST /api/cameras/:id/ptz` (hoặc `POST /api/devices/cameras/:id/ptz`): Điều khiển camera xoay/zoom/lấy nét.
  - Body: `{ "action": "ZOOM_IN" | "ZOOM_OUT" | "PAN" | "AUTO_FOCUS", "speed": 1 }`

### 3. Tiếp nhận Phát hiện từ AI & Ghi nhận Sự cố (AI Webhook & Incident Logging)
- `POST /api/v1/ai/detection` (hoặc `POST /api/v1/webhook`): Tiếp nhận kết quả phân tích thời gian thực từ mô hình AI (`YOLO11-Pose` + kinematics + ảnh JPEG base64).
- `POST /api/incidents`: Tiếp nhận bản tin sự cố tổng quát từ client bên ngoài, ghi nhận lập tức vào bảng `audit_logs` của D1 và đưa vào hàng đợi xác thực của Operator.

### 4. Quản lý Sự cố & Bằng chứng Tư pháp (Incidents & Forensic Playback)
- `GET /api/incidents/recent` (hoặc `GET /api/incidents`): Lấy danh sách các sự cố an ninh mới nhất.
- `GET /api/incidents/:id/playback`: Trích xuất gói bằng chứng 20 giây (10s trước và 10s sau sự kiện), ảnh chụp đối tượng và vệt nhận diện.

### 5. Lớp AI Phân Tích Tự Động & Endpoint Truy Vấn Sự Cố (Integrated AI & /api/get-incidents)
Hệ thống tích hợp sẵn lớp phân tích AI trong mã nguồn (in-process automated layer). Không cần người dùng/client gọi thủ công, mọi request POST gửi về đều tự động được AI phân tích ngầm và xuất dữ liệu JSON:
- `GET /api/get-incidents` & `GET /api/get-incident` (Alias: `/api/v1/get-incidents`, `/api/v1/get-incident`, `/api/incidents/get-incidents`):
  - Tham số: `?window=120` (khung thời gian trượt theo giây).
  - Trả về JSON cấu trúc chuẩn sinh ra trực tiếp từ phân tích của AI:
    - `provider`: Cơ chế AI phân tích (`DEEPSEEK_DIRECT_API` | `CLOUDFLARE_WORKERS_AI` | `LOCAL_KINEMATICS_ENGINE`).
    - `model`: Tên mô hình (VD: `deepseek-chat` hoặc `@cf/deepseek-ai/deepseek-v4.1-flash-1017`).
    - `severity`: Cấp độ nghiêm trọng (`LOW` | `MEDIUM` | `HIGH` | `CRITICAL`).
    - `deepseek_analysis`: `threat_verdict`, `investigation_summary`, `analyzed_at`.
    - `object_description`: `role` (suspect/victim/bystander), `primary_action`, `weapon_detected`, `weapon_confidence`, `posture_details`, `kinematics_summary` (góc khuỷu tay, vận tốc, độ duỗi).
    - `timeline`: `event_trigger`, `pre_event_seconds`, `post_event_seconds`, `duration_seconds`.
    - `soc_audit_log`: Bản ghi kiểm toán chuẩn SOC (`log_id`, `log_level`, `latency_ms`, `source: AI_INTEGRATED_LAYER`).
    - `snapshot_url`, `crop_image_url`, `sha256_hash`, `operator_status` (`AWAITING_OPERATOR_VERIFICATION` - tuân thủ [CD-04]).
- `GET /api/soc/logs` (Alias: `/api/v1/soc/logs`, `/api/get-incident-logs`):
  - Trả về danh sách toàn bộ bản ghi nhật ký kiểm toán chuẩn SOC (`IStandardSocLogEntry`) do lớp AI phân tích sinh ra.
- `POST /api/v1/deepseek/analyze`: Kích hoạt phân tích tức thời luồng log POST trượt 2 phút qua mô hình DeepSeek (tùy chọn webhook).
  - Query/Body: `{ "windowSeconds": 120 }`

### 6. Cấu Hình Gắn Trực Tiếp DeepSeek API Key (Pluggable API Key)
Bạn có thể gắn API Key trực tiếp vào hệ thống để gọi mô hình DeepSeek qua 2 cách:
1. **Trong `wrangler.toml`:**
   ```toml
   [vars]
   DEEPSEEK_API_KEY = "sk-xxxxxxxxxxxxxxxxxxxxxxxx"
   DEEPSEEK_MODEL = "deepseek-chat"
   ```
2. **Qua Cloudflare Secrets (Production):**
   ```bash
   npx wrangler secret put DEEPSEEK_API_KEY
   ```
Khi có API Key, hệ thống tự động ưu tiên gọi trực tiếp `https://api.deepseek.com/chat/completions` (JSON mode); nếu không có key hoặc mất kết nối, hệ thống tự động chuyển tiếp mượt mà qua Workers AI hoặc Động cơ Động học Khớp xương Nội bộ.

### 7. Đường Ống Lưu Trữ Cloudflare KV & Debug Trace Input/Output
Hệ thống sử dụng Cloudflare KV (`INCIDENT_CACHE`) để ghi nhận cả Input và Output của DeepSeek, phục vụ debug tức thì và tối ưu tốc độ phản hồi Dashboard:
- `raw_incident:<event_id>`: Bản ghi thô từ edge camera/client.
- `deepseek:input:<event_id>`: Prompt, kinematics và payload đầu vào gửi DeepSeek.
- `deepseek:output:<event_id>`: Raw completion và JSON đã parse đầu ra kèm thời gian phản hồi (latency ms) tuân thủ định dạng chuẩn DeepSeek.
- `deepseek:trace:<event_id>`: Debug trace hợp nhất xem cả Input & Output trong 1 truy vấn duy nhất.
- `kv_recent_incidents`: Bộ đệm các sự cố mới nhất trong KV giúp Dashboard fetch với độ trễ `< 15ms`.
- `GET /api/kv/trace/:id` (Alias: `/api/deepseek/trace/:id`, `/api/v1/debug/trace/:id`): Endpoint tra cứu chi tiết Input & Output của một sự cố theo ID.

### 7.1. Cấu Trúc Đầu Ra Chuẩn Hóa DeepSeek KV & Realtime Dashboard
Toàn bộ sự cố lưu trong KV và cung cấp qua `/api/get-incident` / `/api/get-incidents` đều được chuẩn hóa 100% khớp theo định dạng:
```json
{
  "event_id": "EVT_20261107_213746_3e304691",
  "raw_response": "[DeepSeek Forensic Engine] Hoạt động quan sát định kỳ tại Laptop Client Zone. Tiếp tục giám sát.",
  "parsed_json": {
    "severity": "MEDIUM",
    "threat_verdict": "OBSERVED_ACTIVITY",
    "investigation_summary": "[DeepSeek Forensic Engine] Hoạt động quan sát định kỳ tại Laptop Client Zone. Tiếp tục giám sát.",
    "object_description": {
      "primary_action": "NORMAL",
      "role": "bystander",
      "posture_details": "Detected action: NORMAL (threat score: 0.10)",
      "weapon_detected": null,
      "weapon_confidence": 0,
      "kinematics_summary": "Góc khuỷu tay phải: N/A°, Độ duỗi tay: N/Am, Vận tốc cổ tay: N/Apx/s",
      "keypoints_count": 17
    }
  },
  "model_used": "@cf/deepseek-ai/deepseek-v4.1-flash-1017",
  "latency_ms": 925,
  "timestamp": "2026-11-07T14:37:50.049Z"
}
```
Dashboard kết nối Realtime 2 kênh đồng bộ:
1. **WebSocket (`/ws/live-stream`):** Nhận gói tin `NEW_INCIDENT` ngay khi Worker phân tích AI xong và cập nhật tức thì vào bảng điều khiển.
2. **REST Polling Tối ưu 1000ms:** Polling liên tục tới `/api/get-incident`, truy xuất thẳng vào bộ đệm `kv_recent_incidents` từ Cloudflare KV với độ trễ `< 15ms`.
3. **Render Toàn diện:** Hiển thị chi tiết động học (`kinematics_summary`: góc khuỷu tay, độ duỗi, vận tốc), tư thế (`posture_details`), model và độ trễ trên `RecentThreatsTable`, `EvidencePlaybackModal`, `IncidentFeedView` và `AiAnalyzerView`. Mọi sự cố đều khóa mặc định ở trạng thái `AWAITING_OPERATOR_VERIFICATION` / `PENDING_VERIFICATION` theo đúng quy định Operational HITL [CD-04].

### 8. Chốt chặn Xác thực Vận hành viên (Operational HITL Gate)
- `POST /api/incidents/:id/verify`: API bắt buộc Vận hành viên phê duyệt trước khi phát lệnh điều phối.
  - Body:
    ```json
    {
      "operatorId": "OP-VN-SOC-804",
      "decision": "CONFIRM_AND_DISPATCH" | "DOWNGRADE_MONITOR" | "DISMISS_FALSE_POSITIVE",
      "notes": "Xác nhận đối tượng có hung khí tại Cổng Đông."
    }
    ```
  - Khi `decision === "CONFIRM_AND_DISPATCH"`, hệ thống tự động sinh ra gói `incidentPackage` hoàn chỉnh để chuyển giao lực lượng ứng cứu.

### 9. Nhật ký Kiểm toán Bất biến (SOC Audit Logs)
- `GET /api/soc/audit-logs`: Truy xuất lịch sử kiểm toán bất biến từ Cloudflare D1 SQL.

### 10. Kênh Dữ liệu Thời Gian Thực (WebSocket Live Stream)
- Kết nối tới `ws://127.0.0.1:8787/ws/live-stream`:
  - Sự kiện `CONNECTED`: Nhận heartbeat và thời gian đồng bộ máy chủ.
  - Sự kiện `TELEMETRY_AND_AI_TICK`: Nhận tọa độ bounding box thời gian thực và cập nhật camera.
  - Sự kiện `NEW_INCIDENT`: Nhận thông báo sự cố mới tức thì không cần tải lại trang.

### 11. Cấu Hình Bảo Mật Whitelist CORS & Client IP
Hệ thống tích hợp cổng bảo mật kép (`CloudflareWorker/src/security.ts`) cấu hình qua `wrangler.toml`:
- `ALLOWED_ORIGINS`: Danh sách các domain trình duyệt được phép kết nối (Hỗ trợ wildcard, VD: `https://*.pages.dev,https://*.workers.dev`).
- `ALLOWED_IPS`: Danh sách IP / Subnet CIDR được phép truy cập (Mặc định cho phép loopback `127.0.0.1`, `::1` và mạng LAN riêng `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`).
- `ENFORCE_IP_WHITELIST`: Đặt `"true"` trên production để chặn cứng toàn bộ IP ngoài whitelist với mã lỗi `403 Forbidden` và tự động ghi log `SECURITY_IP_BLOCKED` vào Cloudflare D1.

### 12. Luồng Video Trực Tiếp Camera Laptop & Proxy Edge (Live Stream Proxy & Backup URL)
Hệ thống hỗ trợ phát trực tiếp luồng video từ camera laptop (`LAPTOP_01`):
- **Endpoint Proxy Edge:** `GET /api/v1/cameras/:id/stream` (hoặc `GET /api/cameras/:id/stream`).
- **Cấu hình Backup URL:** Biến `LIVE_CAMERA_STREAM_URL` trong `wrangler.toml` [vars]:
  ```toml
  LIVE_CAMERA_STREAM_URL = "https://means-brick-determined-send.trycloudflare.com/api/v1/cameras/LAPTOP_01/stream"
  ```
  Khi đường hầm Cloudflare Tunnel được cấp phát lại, người vận hành chỉ cần cập nhật biến này trong `wrangler.toml` hoặc qua Dashboard Cloudflare Workers mà không cần build lại frontend. Proxy Edge tự động chuyển tiếp luồng dữ liệu kèm đầy đủ CORS headers, hỗ trợ fallback mượt mà khi upstream gặp sự cố mạng.

---

## 🏗️ BUILD & DEPLOY LÊN CLOUDFLARE WORKERS

### 1. Build Dự Án (Toàn bộ Frontend & Worker)
```bash
pnpm run build
```
Lệnh này sẽ:
1. Chạy TypeScript type-checking cho Frontend.
2. Build ứng dụng React 19 tối ưu hóa bằng Vite vào thư mục `CloudflareWorker/dist/`.
3. Kiểm tra kiểu tĩnh TypeScript cho mã nguồn Cloudflare Worker (`tsc --noEmit`).

### 2. Tạo Cơ sở dữ liệu Cloudflare D1 (Nếu triển khai mới)
```bash
cd CloudflareWorker
npx wrangler d1 create urban_soc_db
# Cập nhật database_id vào file wrangler.toml
npx wrangler d1 execute urban_soc_db --file=./schema.sql
```

### 3. Deploy Lên Mạng Lưới Cloudflare Toàn Cầu
```bash
# Đăng nhập Wrangler
npx wrangler login

# Hoặc gán token Cloudflare API:
# $env:CLOUDFLARE_API_TOKEN="your_token_here"

# Triển khai trực tiếp
pnpm run deploy
```

---

## 📜 NGUYÊN TẮC PHÁT TRIỂN & ĐIỀU PHỐI (AGENTS.MD)

Dự án áp dụng phương pháp luận **Spec-Driven Development (SDD)** và quy tắc nghiêm ngặt trong [AGENTS.md](file:///c:/Users/admin/OneDrive/Tài%20liệu/SGU/Hackathon/Promptacus---Hackathon-/AGENTS.md):
- **[CD-01] Spec-First & Plan-First:** Không sinh code khi chưa có `SPEC.md` và `PLAN.md` được phê duyệt.
- **[CD-04] Dual HITL Integrity:** Bảo đảm chốt chặn Vận hành viên con người ở cả tầng phát triển và tầng vận hành tác chiến.
- **[CD-05] SOC-Grade Traceability:** Mọi sự cố đều có nhật ký kiểm toán bất biến.
- **[CD-06] Tri-Document Sync:** Bắt buộc đồng bộ liên tục `AGENTS.md`, `README.md` và `PROJECT_STRUCTURE.md` sau mỗi task hoàn thành.

---

## 👥 ĐỘI NGŨ PHÁT TRIỂN & BẢN QUYỀN

- **Dự án:** Urban Safety AI-SOC (CyberGuard AI)
- **Sự kiện:** Hackathon 2026
- **Bản quyền:** © 2026 Promptacus Team. Giữ toàn quyền kiến trúc và giải pháp.
