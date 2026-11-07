# CẤU TRÚC DỰ ÁN (PROJECT STRUCTURE)
**Dự án:** Hệ thống Giám sát An ninh & An toàn Đô thị Thông minh (Urban Safety SOC)  
**Nền tảng:** Cloudflare Workers Edge Stack (React 19 + TypeScript + Cloudflare KV + D1 SQL)

---

## 1. SƠ ĐỒ CÂY THƯ MỤC TỔNG THỂ

```text
Promptacus---Hackathon-/
├── AGENTS.md                          # Quy tắc điều phối AI Agent (SDD, HITL, CD-01 -> CD-06)
├── README.md                          # Tài liệu giới thiệu, hướng dẫn cài đặt & API hệ thống
├── PROJECT_STRUCTURE.md               # Sơ đồ và mô tả chi tiết toàn bộ cấu trúc dự án (Tài liệu này)
├── SPEC_PURE_DASHBOARD_KV_SERVER.md   # Đặc tả kỹ thuật Pure Display Dashboard, KV Storage & Server JSON Ingestion
├── PLAN_PURE_DASHBOARD_KV_SERVER.md   # Kế hoạch triển khai Pure Display Dashboard, KV Storage & Server JSON Ingestion
├── SPEC_STREAM_ZOOM_ALERT_REFACTOR.md # Đặc tả kỹ thuật tích hợp video stream Laptop, zoom matrix 2x2 & Alert Log 20% modal
├── PLAN_STREAM_ZOOM_ALERT_REFACTOR.md # Kế hoạch triển khai tích hợp video stream Laptop, zoom matrix 2x2 & Alert Log 20% modal
├── SPEC_DASHBOARD_KV_REALTIME.md      # Đặc tả kỹ thuật đồng bộ realtime Dashboard với Cloudflare KV
├── PLAN_DASHBOARD_KV_REALTIME.md      # Kế hoạch triển khai đồng bộ realtime Dashboard với Cloudflare KV
├── SPEC.md                            # Đặc tả kỹ thuật mức tổng thể hệ thống
├── PLAN.md                            # Kế hoạch triển khai mức tổng thể hệ thống
├── package.json                       # Root package.json điều phối build, dev và deploy
├── pnpm-workspace.yaml                # Cấu hình pnpm monorepo workspace
├── pnpm-lock.yaml                     # Khóa phiên bản dependencies toàn dự án
├── .gitignore                         # Danh sách tệp/thư mục loại trừ khỏi Git
│
├── CloudflareWorker/                  # [CORE BACKEND & KV GATEWAY] Nền tảng hợp nhất Edge SOC
│   ├── src/
│   │   ├── index.ts                   # Router chính: Server JSON Ingest -> KV, Forensic Image Endpoints, Auth, Settings, Stream Proxy, HITL
│   │   ├── types.ts                   # Data Models & Schemas (IServerIngestPayload, IActionValidation, IWeaponInfo, IServerAuditInfo, ICameraDevice, IIncidentItem)
│   │   ├── camera_manager.ts          # Quản lý danh mục camera thực tế từ Server JSON, lưu trữ vào KV (`kv_cameras`)
│   │   ├── incident_manager.ts        # Lưu trữ sự cố trực tiếp từ Server JSON vào KV (`kv_recent_incidents`, `incident:<id>`)
│   │   ├── hitl_dispatcher.ts         # Chốt chặn HITL [CD-04], đóng gói hồ sơ sự cố, ghi log kiểm toán [CD-05]
│   │   ├── telemetry.ts               # Tính toán chỉ số tổng quan thực tế từ KV (Zero fake metrics)
│   │   ├── websocket.ts               # WebSocket broker native (Cloudflare WebSocketPair)
│   │   ├── security.ts                # Bộ điều khiển bảo mật: CORS Origin Whitelist & Client IP CIDR Filter
│   │   └── db.ts                      # Repository tương tác cơ sở dữ liệu Cloudflare D1 SQL (Audit & Backup)
│   ├── dist/                          # Thư mục chứa bản build tĩnh của React Frontend SPA
│   ├── schema.sql                     # Schema SQL D1 (bảng incidents, audit_logs và các index)
│   ├── wrangler.toml                  # Cấu hình Cloudflare Worker, KV Namespace (`INCIDENT_CACHE`), D1, `LIVE_CAMERA_STREAM_URL`
│   ├── package.json                   # Dependencies & scripts của Cloudflare Worker
│   ├── tsconfig.json                  # Cấu hình TypeScript cho Cloudflare Worker
│   └── worker-configuration.d.ts      # Khai báo kiểu môi trường (Cloudflare Env bindings)
│
├── Dashboard/
│   ├── Front End/                     # [FRONTEND SPA] Giao diện Hiển thị & Điều hành SOC (React 19)
│   │   ├── src/
│   │   │   ├── App.tsx                # Container chính, quản lý phiên đăng nhập (`session`), điều phối 5 tab và HITL
│   │   │   ├── main.tsx               # Điểm khởi chạy ứng dụng React 19
│   │   │   ├── index.css              # Cấu hình CSS toàn cục & TailwindCSS directives
│   │   │   ├── types/
│   │   │   │   └── soc.ts             # Định nghĩa kiểu dữ liệu frontend khớp 100% với Server JSON & KV
│   │   │   ├── hooks/
│   │   │   │   ├── useSocTelemetry.ts # Hook đồng bộ dữ liệu thực tế từ KV qua REST polling & Live WebSocket
│   │   │   │   ├── useCctvCanvas.ts   # Canvas renderer vẽ video frame & bounding box của `actors`
│   │   │   │   └── useUtcClock.ts     # Đồng hồ chuẩn hóa UTC cho SOC
│   │   │   ├── data/
│   │   │   │   └── mockData.ts        # Trạng thái khởi tạo rỗng (`MOCK_CAMERAS = []`, `MOCK_INCIDENTS = []`)
│   │   │   └── components/
│   │   │       ├── Sidebar.tsx        # Menu trái 5 tab với badge động (đã xóa hộp thông tin góc dưới)
│   │   │       ├── TopHeader.tsx      # Thanh tiêu đề hệ thống, nút Sign In / Operator Profile & chuông thông báo
│   │   │       ├── KpiCards.tsx       # Khối hiển thị chỉ số quan trọng từ dữ liệu thực
│   │   │       ├── CameraMatrix/      # Ma trận hiển thị luồng camera 2x2, zoom 1x1 (80% width) & điều khiển PTZ
│   │   │       │   ├── CameraMatrix.tsx
│   │   │       │   └── CameraSlot.tsx
│   │   │       ├── AlertLog/          # Bảng Alert Log rút gọn cảnh báo sớm & mở rộng 20% right menu modal khi phóng to
│   │   │       │   └── AlertLogModule.tsx
│   │   │       ├── Modal/
│   │   │       │   ├── EvidencePlaybackModal.tsx # Hộp thoại chi tiết sự cố (`actors`, `visual_cues`, `reasoning`) & duyệt HITL
│   │   │       │   └── AuthLoginModal.tsx        # Hộp thoại đăng nhập & quản lý phiên trực Vận hành viên SOC
│   │   │       ├── RecentThreats/     # Bảng danh sách sự kiện Server gửi lên lưu trong KV
│   │   │       │   ├── RecentThreatsTable.tsx
│   │   │       │   └── ThreatRow.tsx
│   │   │       └── views/             # 5 Giao diện Tác chiến:
│   │   │           ├── DashboardView.tsx           # Tab 1: SOC Dashboard (đã gỡ bỏ nút Phòng Thủ Khẩn Cấp)
│   │   │           ├── ThreatIntelligenceView.tsx  # Tab 2: Phân tích `action_type`, `visual_cues`, `actors` từ dữ liệu thật
│   │   │           ├── IncidentFeedView.tsx        # Tab 3: Nhật ký sự cố chi tiết từ KV kèm tìm kiếm & lọc
│   │   │           ├── DeviceManagerView.tsx       # Tab 4: Quản lý camera thực tế từ Server JSON (`measured_fps`, `frame_index`, `human_count`)
│   │   │           └── SettingsView.tsx            # Tab 5: Cấu hình hệ thống đồng bộ hai chiều với Cloudflare KV
│   │   ├── index.html                 # Template HTML chính
│   │   ├── package.json               # Dependencies của React (Vite, Tailwind, Lucide)
│   │   ├── vite.config.ts             # Cấu hình Vite build ra CloudflareWorker/dist
│   │   └── tsconfig.json              # Cấu hình TypeScript cho Frontend
│   │
│   └── Back End/                      # [LEGACY BACKEND] Lưu trữ tham chiếu trước đây
├── AI/                                # [EXTERNAL CAMERA SERVER SCRIPTS] Phân hệ Server bên ngoài gửi JSON lên Worker
├── Engine/                            # [BEHAVIOR RULE ENGINE] Quy tắc đánh giá chuỗi hành vi
└── Rule/                              # [SECURITY POLICIES] Tập luật an ninh đô thị
```

---

## 2. MÔ TẢ TRÁCH NHIỆM CÁC THÀNH PHẦN CHỦ CHỐT

### 2.1. Phân hệ Edge Backend & KV Gateway (`CloudflareWorker/`)
- Tiếp nhận liên tục các gói tin JSON từ Server gửi lên qua các endpoint `POST` (`/api/v1/ai/detection`, `/api/incidents`, `/api/v1/webhook`, `/api/ingest`) mà không chạy lại mô hình AI trên Worker.
- Lưu trữ trực tiếp danh sách sự cố (`kv_recent_incidents`, `incident:<id>`), danh sách camera (`kv_cameras`), cấu hình hệ thống (`kv_settings`) và phiên đăng nhập (`kv_session:<token>`) vào **Cloudflare KV (`INCIDENT_CACHE`)**.
- Thực thi nghiêm ngặt chốt chặn **Operational HITL (`[CD-04]`)** và ghi nhật ký kiểm toán bất biến (`[CD-05]`).

### 2.2. Phân hệ Dashboard Frontend (`Dashboard/Front End/`)
- Hiển thị trung thực 100% dữ liệu từ Server gửi lên (Zero Fake Data).
- Cung cấp đầy đủ 5 tab hoạt động hoàn chỉnh: `SOC Dashboard`, `Threat Intelligence`, `Incident Feed`, `Device Manager`, và `Settings`, cùng hệ thống xác thực `Sign In` / `Sign Out` cho Vận hành viên trực ban.
