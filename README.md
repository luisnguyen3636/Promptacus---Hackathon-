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
- **🖥️ 8 Giao diện Tác chiến SOC Độc lập:** 
  1. *Dashboard View:* Bảng điều khiển tác chiến tổng quan thời gian thực.
  2. *Live Video Wall:* Ma trận camera trực tiếp với khả năng điều khiển xoay/zoom PTZ.
  3. *Network Topology:* Giám sát topo mạng, độ trễ và tải PoE camera.
  4. *Threat Intelligence:* Phân tích tình báo đe dọa và lịch sử phân loại hành vi.
  5. *Incident Feed:* Nhật ký sự cố chi tiết kèm bộ lọc đa tiêu chí.
  6. *AI Analyzer:* Theo dõi độ tin cậy mô hình, vệt di chuyển (active tracks) và khung xương.
  7. *Device Manager:* Quản lý danh mục camera và trạng thái kết nối.
  8. *Settings:* Tùy chỉnh ngưỡng đe dọa, cấu hình còi báo động và phân quyền vận hành.

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

### 5. Chốt chặn Xác thực Vận hành viên (Operational HITL Gate)
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

### 6. Nhật ký Kiểm toán Bất biến (SOC Audit Logs)
- `GET /api/soc/audit-logs`: Truy xuất lịch sử kiểm toán bất biến từ Cloudflare D1 SQL.

### 7. Kênh Dữ liệu Thời Gian Thực (WebSocket Live Stream)
- Kết nối tới `ws://127.0.0.1:8787/ws/live-stream`:
  - Sự kiện `CONNECTED`: Nhận heartbeat và thời gian đồng bộ máy chủ.
  - Sự kiện `TELEMETRY_AND_AI_TICK`: Nhận tọa độ bounding box thời gian thực và cập nhật camera.
  - Sự kiện `NEW_INCIDENT`: Nhận thông báo sự cố mới tức thì không cần tải lại trang.

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
