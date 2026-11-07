# CẤU TRÚC DỰ ÁN (PROJECT STRUCTURE)
**Dự án:** Hệ thống Giám sát An ninh & An toàn Đô thị Thông minh (Urban Safety AI-SOC)  
**Nền tảng:** Cloudflare Workers Edge Stack (React 19 + TypeScript + Workers AI + D1 SQL + YOLO11-Pose)

---

## 1. SƠ ĐỒ CÂY THƯ MỤC TỔNG THỂ

```text
Promptacus---Hackathon-/
├── AGENTS.md                          # Quy tắc điều phối AI Agent (SDD, HITL, CD-01 -> CD-06)
├── README.md                          # Tài liệu giới thiệu, hướng dẫn cài đặt & vận hành hệ thống
├── PROJECT_STRUCTURE.md               # Sơ đồ và mô tả chi tiết toàn bộ cấu trúc dự án (Tài liệu này)
├── SPEC.md                            # Đặc tả kỹ thuật mức tổng thể hệ thống
├── PLAN.md                            # Kế hoạch triển khai mức tổng thể hệ thống
├── package.json                       # Root package.json điều phối build, dev và deploy
├── pnpm-workspace.yaml                # Cấu hình pnpm monorepo workspace
├── pnpm-lock.yaml                     # Khóa phiên bản dependencies toàn dự án
├── .gitignore                         # Danh sách tệp/thư mục loại trừ khỏi Git
│
├── CloudflareWorker/                  # [CORE BACKEND & EDGE RUNTIME] Nền tảng hợp nhất Edge SOC
│   ├── src/
│   │   ├── index.ts                   # Router chính: REST APIs, WebSocket broker, Static Assets fetcher
│   │   ├── types.ts                   # Data Models & Schemas (AI Ingestion, Incidents, Cameras, HITL, DeepSeek, SOC Log)
│   │   ├── deepseek_analyzer.ts       # Lớp AI phân tích tự động: DeepSeek Direct API, Workers AI, Kinematics, SOC Audit Logs
│   │   ├── camera_manager.ts          # Quản lý fleet camera động, chuẩn hóa bounding box tỉ đối
│   │   ├── incident_manager.ts        # Quản lý sự cố, rolling buffer bằng chứng, tích hợp AI
│   │   ├── hitl_dispatcher.ts         # Chốt chặn HITL [CD-04], đóng gói gói cứu hộ, ghi log kiểm toán [CD-05]
│   │   ├── telemetry.ts               # Bộ máy chấm điểm rủi ro động (Dynamic Threat Scoring)
│   │   ├── websocket.ts               # WebSocket broker native (Cloudflare WebSocketPair)
│   │   ├── ai_evaluator.ts            # Tích hợp Workers AI (DeepSeek / Llama 3.2 Vision)
│   │   ├── security.ts                # Bộ điều khiển bảo mật: CORS Origin Whitelist & Client IP CIDR Filter
│   │   └── db.ts                      # Repository tương tác cơ sở dữ liệu Cloudflare D1 SQL
│   ├── dist/                          # Thư mục chứa bản build tĩnh của React Frontend SPA
│   ├── schema.sql                     # Schema SQL D1 (bảng incidents, audit_logs và các index)
│   ├── wrangler.toml                  # Cấu hình Cloudflare Worker, D1 Database, Workers AI binding, DeepSeek API Key
│   ├── package.json                   # Dependencies & scripts của Cloudflare Worker
│   ├── tsconfig.json                  # Cấu hình TypeScript cho Cloudflare Worker
│   ├── worker-configuration.d.ts      # Khai báo kiểu môi trường (Cloudflare Env bindings)
│   ├── test_e2e.mjs                   # Script kiểm thử tự động toàn diện AI Ingestion & HITL
│   ├── test_post_incidents.mjs        # Script kiểm thử tự động endpoint POST /api/incidents
│   ├── test_cors_ip_whitelist.mjs     # Script kiểm thử tự động CORS Origin & IP Whitelist Gate
│   ├── test_deepseek_pipeline.mjs     # Script kiểm thử tự động DeepSeek 2-phút & /api/get-incident (20 assertions)
│   ├── test_integrated_ai_layer.mjs   # Script kiểm thử tự động Lớp AI Tích Hợp & Log Chuẩn SOC (26 assertions)
│   ├── test_kv_pipeline.mjs           # Script kiểm thử tự động Cloudflare KV & Input/Output Trace (24 assertions)
│   ├── SPEC_KV_INCIDENT_PIPELINE.md   # Đặc tả kỹ thuật lưu trữ KV & DeepSeek Input/Output Trace
│   ├── PLAN_KV_INCIDENT_PIPELINE.md   # Kế hoạch triển khai lưu trữ KV & DeepSeek Input/Output Trace
│   ├── SPEC_INTEGRATED_AI_LAYER.md    # Đặc tả kỹ thuật lớp AI tích hợp tự động & DeepSeek API Key
│   ├── PLAN_INTEGRATED_AI_LAYER.md    # Kế hoạch triển khai lớp AI tích hợp tự động & DeepSeek API Key
│   ├── SPEC_DEEPSEEK_PIPELINE.md      # Đặc tả kỹ thuật đường ống phân tích DeepSeek 2 phút
│   ├── PLAN_DEEPSEEK_PIPELINE.md      # Kế hoạch triển khai đường ống phân tích DeepSeek 2 phút
│   ├── SPEC_AI_INTEGRATION.md         # Đặc tả kỹ thuật tích hợp payload AI thực tế
│   ├── PLAN_AI_INTEGRATION.md         # Kế hoạch triển khai tích hợp payload AI thực tế
│   ├── SPEC_UNIFIED_SOC.md            # Đặc tả kỹ thuật hợp nhất backend lên Cloudflare Worker
│   └── PLAN_UNIFIED_SOC.md            # Kế hoạch triển khai hợp nhất backend lên Cloudflare Worker
│
├── Dashboard/
│   ├── Front End/                     # [FRONTEND SPA] Giao diện Tác chiến SOC chuyên dụng (React 19)
│   │   ├── src/
│   │   │   ├── App.tsx                # Container chính, điều phối 8 view tác chiến và xử lý lệnh PTZ/HITL
│   │   │   ├── main.tsx               # Điểm khởi chạy ứng dụng React 19
│   │   │   ├── index.css              # Cấu hình CSS toàn cục & TailwindCSS directives
│   │   │   ├── types/
│   │   │   │   └── soc.ts             # Định nghĩa kiểu dữ liệu frontend (Camera, Incident, Overview)
│   │   │   ├── hooks/
│   │   │   │   ├── useSocTelemetry.ts # Hook đồng bộ dữ liệu qua REST polling & Live WebSocket
│   │   │   │   ├── useCctvCanvas.ts   # Canvas renderer hiệu năng cao vẽ video frame & bounding box
│   │   │   │   └── useUtcClock.ts     # Đồng hồ nguyên tử chuẩn hóa UTC cho SOC
│   │   │   ├── data/
│   │   │   │   └── mockData.ts        # Trạng thái khởi tạo sạch (Zero fake data, sẵn sàng đón nhận AI)
│   │   │   └── components/
│   │   │       ├── Sidebar.tsx        # Menu tác chiến chuyển đổi giữa các module (đã gỡ bỏ Network Topology)
│   │   │       ├── TopHeader.tsx      # Thanh tiêu đề hệ thống, trạng thái mạng, PoE, KPI tổng
│   │   │       ├── KpiCards.tsx       # Khối hiển thị chỉ số quan trọng (Độ trễ, Camera online, Threat)
│   │   │       ├── AiMetricsGrid/     # Cụm 8 thẻ chỉ số hiệu năng AI & phân bố đối tượng thời gian thực
│   │   │       │   └── AiMetricsGrid.tsx # Inference Time, GPU Load, Accuracy, Active Tracks, Class Breakdown
│   │   │       ├── CameraMatrix/      # Ma trận hiển thị luồng camera 2x2 có hỗ trợ vẽ Bounding Box AI
│   │   │       ├── Modal/
│   │   │       │   └── EvidencePlaybackModal.tsx # Hộp thoại phát lại bằng chứng tư pháp & nút duyệt HITL
│   │   │       ├── RecentThreats/     # Bảng danh sách sự cố thời gian thực
│   │   │       ├── ThreatScoreGauge/  # Đồng hồ đo mức độ đe dọa đô thị (0 - 100)
│   │   │       ├── TrafficChart/      # Biểu đồ lưu lượng mạng truyền thống (được thay thế bởi AiMetricsGrid trên Dashboard)
│   │   │       └── views/             # Các Giao diện Tác chiến Chuyên biệt:
│   │   │           ├── DashboardView.tsx           # View 1: Trung tâm chỉ huy tổng thể (nhúng AiMetricsGrid)
│   │   │           ├── LiveVideoWallView.tsx       # View 2: Tường video CCTV mở rộng & điều khiển PTZ
│   │   │           ├── ThreatIntelligenceView.tsx  # View 3: Phân tích tình báo rủi ro & bằng chứng
│   │   │           ├── IncidentFeedView.tsx        # View 4: Quản lý chi tiết danh mục sự cố
│   │   │           ├── AiAnalyzerView.tsx          # View 5: Giám sát hiệu năng mô hình AI & vệt track
│   │   │           ├── DeviceManagerView.tsx       # View 6: Quản lý danh mục thiết bị phần cứng
│   │   │           └── SettingsView.tsx            # View 7: Cấu hình ngưỡng cảnh báo & hệ thống
│   │   ├── index.html                 # Template HTML chính
│   │   ├── package.json               # Dependencies của React (Vite, Tailwind, Lucide, Chart.js)
│   │   ├── vite.config.ts             # Cấu hình Vite build ra CloudflareWorker/dist
│   │   ├── tsconfig.json              # Cấu hình TypeScript cho Frontend
│   │   ├── SPEC_REMOVE_DATA_SUMMARY.md # Đặc tả kỹ thuật gỡ bỏ Data Summary Table trong AI Analyzer
│   │   ├── PLAN_REMOVE_DATA_SUMMARY.md # Kế hoạch triển khai gỡ bỏ Data Summary Table trong AI Analyzer
│   │   ├── SPEC.md                    # Đặc tả kỹ thuật giao diện Frontend
│   │   └── PLAN.md                    # Kế hoạch triển khai giao diện Frontend
│   │
│   └── Back End/                      # [LEGACY BACKEND] Express.js & Python Ingestion (Lưu trữ tham chiếu)
│       ├── server.js                  # Máy chủ Express.js truyền thống (đã được chuyển đổi lên Worker)
│       ├── package.json               # Cấu hình Express & WS
│       └── ingestion_service/         # Service phụ trợ nhận dữ liệu trước đây
│
├── AI/                                # [AI DETECTION SUBSYSTEM] Phân hệ Trí tuệ Nhân tạo Thị giác
│   ├── Human/
│   │   ├── src/urbansoc/              # Module nghiệp vụ phân tích hành vi & nhận diện tư thế
│   │   │   ├── domain/                # Pydantic schemas (WebhookIncidentPayload, AIKeypoint, Kinematics)
│   │   │   ├── pipeline/              # Xử lý khung hình, ước lượng dáng điệu (YOLO-Pose), bộ đệm bằng chứng
│   │   │   └── utils/                 # Băm tư pháp SHA-256, chuyển đổi Base64, mã hóa video
│   │   ├── server.py                  # Server giả lập luồng camera và phát hiện bất thường
│   │   ├── client.py                  # Client gửi video và webhook kiểm thử
│   │   ├── main.py                    # Điểm khởi chạy phân tích luồng trực tiếp
│   │   ├── requirements.txt           # Thư viện Python (ultralytics, torch, opencv-python, pydantic)
│   │   ├── pyproject.toml             # Cấu hình gói Python UrbanSOC
│   │   └── README.md                  # Hướng dẫn khởi chạy mô hình AI
│   └── Rule/                          # Các quy tắc phát hiện nghiệp vụ đặc thù
│
├── Engine/                            # [BEHAVIOR RULE ENGINE] Quy tắc đánh giá chuỗi hành vi
└── Rule/                              # [SECURITY POLICIES] Tập luật an ninh đô thị
```

---

## 2. MÔ TẢ TRÁCH NHIỆM CÁC THÀNH PHẦN CHỦ CHỐT

### 2.1. Phân hệ Edge Backend (`CloudflareWorker/`)
- Chịu trách nhiệm toàn quyền xử lý các yêu cầu HTTP REST và phiên kết nối WebSocket trực tiếp từ trình duyệt của Điều hành viên SOC.
- **Hợp nhất Edge:** Không cần máy chủ VPS hay container Docker; toàn bộ backend được biên dịch thành một Cloudflare Worker duy nhất, tận dụng mạng lưới máy chủ biên toàn cầu của Cloudflare.
- **Lưu trữ Bất biến:** Sử dụng **Cloudflare D1 SQL Database** để lưu vết sự cố và nhật ký kiểm toán tư pháp theo tiêu chuẩn SOC-grade.
- **Workers AI:** Tích hợp trực tiếp các mô hình AI ngôn ngữ lớn và VLM (DeepSeek, Llama 3.2 Vision) để thẩm định độ tin cậy của sự cố, loại trừ cảnh báo giả (False Positive Filtering).

### 2.2. Phân hệ Dashboard Frontend (`Dashboard/Front End/`)
- Giao diện tác chiến chuẩn quân sự/SOC dành riêng cho Vận hành viên (Human Operator).
- **8 View Tác chiến Độc lập:** Cung cấp đầy đủ công cụ từ tường camera trực tiếp (Live Video Wall), điều khiển xoay/zoom PTZ, phân tích đồ thị mạng, tra cứu tình báo rủi ro đến cài đặt hệ thống.
- **Hiển thị Bằng chứng Trực quan:** Trích xuất và phát lại bằng chứng từ Rolling Buffer gồm ảnh chụp trước sự kiện (pre-event) và đỉnh điểm sự cố (peak event), vẽ khung nhận diện đối tượng và khung xương 17 điểm khớp động học.
- **Nút Xác thực HITL:** Cung cấp 3 nút bấm nghiệp vụ bắt buộc (`Xác nhận & Điều phối`, `Hạ mức theo dõi`, `Hủy cảnh báo giả`) để hoàn tất chốt chặn an toàn con người.

### 2.3. Phân hệ Phân tích Thị giác AI (`AI/Human/`)
- Thu thập luồng camera giám sát và chạy mô hình **YOLO11-Pose** theo thời gian thực để trích xuất 17 điểm khớp xương người (`keypoints`).
- Tính toán động học cơ thể (`kinematics`): Góc khuỷu tay, độ duỗi cánh tay, khoảng cách cổ tay, vận tốc cổ tay để nhận diện sớm các hành vi tiền phạm tội (rút hung khí, giơ vũ khí nhắm bắn, thủ thế cận chiến) và hậu phạm tội (bỏ chạy tốc độ cao, xô xát, nằm bất động).
- Đóng gói toàn bộ bằng chứng hình ảnh (Base64 JPEG), chữ ký hash SHA-256 và gửi Webhook trực tiếp tới endpoint `POST /api/v1/ai/detection` của Edge Worker.

---

## 3. NGUYÊN TẮC BẢO TRÌ CẤU TRÚC (STRUCTURE INTEGRITY RULES)

Theo chỉ thị `[CD-03]` và `[CD-06]` trong `AGENTS.md`:
1. Mọi thay đổi về cấu trúc thư mục, bổ sung tệp mới hoặc thay đổi đường dẫn đều phải được cập nhật lại vào tài liệu này.
2. Không tạo các thư mục rác hoặc file thử nghiệm tạm thời bên ngoài thư mục được chỉ định.
3. Bản build của Frontend luôn xuất trực tiếp vào `CloudflareWorker/dist/` để Edge Worker đóng gói và phục vụ trực tiếp.
