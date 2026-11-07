# KẾ HOẠCH TRIỂN KHAI (IMPLEMENTATION PLAN)
## Refactor Toàn Diện: Pure Display Dashboard, Server JSON Ingestion vào Cloudflare KV, Xóa AI & Dữ Liệu Giả, Hoàn Thiện Authentication & Toàn Bộ Tab

**Dự án:** Hệ thống Giám sát An ninh & An toàn Đô thị Thông minh (Urban Safety SOC)  
**Tài liệu Spec liên kết:** `SPEC_PURE_DASHBOARD_KV_SERVER.md`  
**Giai đoạn:** BƯỚC 2: LẬP KẾ HOẠCH TRIỂN KHAI (STAGE 2 — IMPLEMENTATION PLAN)  
**Tuân thủ:** AGENTS.md (CD-01 đến CD-06)  
**Ngày soạn thảo:** 2026-11-08  

---

### 1. DANH SÁCH FILE THAY ĐỔI

#### 1.1. File Tạo Mới:
- `Dashboard/Front End/src/components/Modal/AuthLoginModal.tsx`: Hộp thoại Đăng nhập & Quản lý phiên Vận hành viên SOC.

#### 1.2. File Sửa Đổi:
- `CloudflareWorker/src/types.ts`: Thêm `IServerIngestPayload`, `IServerActor`, `IServerVisualCues`, `INvidiaVlmAnalysis`, `ISocSettings`, `IOperatorSession`.
- `CloudflareWorker/src/camera_manager.ts`:
  - Xóa khởi tạo camera giả mặc định.
  - Thêm `upsertCameraFromServerPayload(payload: IServerIngestPayload, defaultStreamUrl?: string)` và lưu/đọc danh sách camera từ Cloudflare KV (`kv_cameras`).
- `CloudflareWorker/src/incident_manager.ts`:
  - Thêm `ingestServerPayloadToKv(payload: IServerIngestPayload, env: Env, clientIp?: string)` chuẩn hóa toàn bộ trường JSON của Server (`status`, `camera_id`, `location`, `timestamp`, `measured_fps`, `frame_index`, `human_count`, `severity`, `action_type`, `threat_score`, `confidence`, `is_urgent`, `description`, `reasoning`, `recommended_action`, `actors`, `visual_cues`, `nvidia_vlm_analysis`) và lưu vào Cloudflare KV (`kv_recent_incidents`, `incident:<id>`).
  - Thêm hàm đồng bộ trạng thái xác thực HITL trực tiếp vào KV.
- `CloudflareWorker/src/telemetry.ts`:
  - Xóa bỏ toàn bộ thông số giả (`9744.0 Mbps`, jitter ngẫu nhiên).
  - Tính toán chỉ số hoàn toàn từ dữ liệu thật của camera và sự cố trong KV.
- `CloudflareWorker/src/index.ts`:
  - Xóa hoàn toàn các lệnh gọi AI tự phân tích (`analyzeSingleLogWithIntegratedAI`, `WorkersAIEvaluator`, `analyzeWindowWithDeepSeek`).
  - Mọi request POST gửi dữ liệu sự cố/camera đều đi qua luồng lưu trữ trực tiếp vào Cloudflare KV (`INCIDENT_CACHE`).
  - Bổ sung các endpoint:
    - `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`
    - `GET /api/settings`, `POST /api/settings`
    - `DELETE /api/devices/cameras/:id` (xóa thiết bị/camera khỏi KV nếu cần)
- `Dashboard/Front End/src/types/soc.ts`:
  - Cập nhật `ICameraDevice`, `IIncidentItem`, `IServerActor`, `IServerVisualCues`, `INvidiaVlmAnalysis`, `ISocSettings`, `IOperatorUser`.
- `Dashboard/Front End/src/data/mockData.ts`:
  - Đưa `MOCK_CAMERAS = []`, `MOCK_INCIDENTS = []`, `MOCK_OVERVIEW` về giá trị `0` sạch sẽ (Zero Fake Data).
- `Dashboard/Front End/src/hooks/useSocTelemetry.ts`:
  - Đồng bộ dữ liệu từ `/api/get-incident`, `/api/devices/cameras`, `/api/soc/overview`, `/api/settings` từ Cloudflare KV.
  - Map chính xác 100% cấu trúc JSON của Server gửi lên.
- `Dashboard/Front End/src/components/Sidebar.tsx`:
  - Xóa hộp thông tin góc dưới bên trái (`SYSTEM ACTIVE / Threat DB / Engine: Online`).
  - Thay badge cố định bằng số lượng sự cố thật đang chờ xử lý.
- `Dashboard/Front End/src/components/TopHeader.tsx`:
  - Hoàn thiện nút `Sign In` / hiển thị thông tin Vận hành viên đã đăng nhập & nút `Sign Out`.
  - Hoàn thiện nút chuông thông báo (hiển thị danh sách cảnh báo khẩn cấp chưa xử lý khi click).
- `Dashboard/Front End/src/components/views/DashboardView.tsx`:
  - Xóa nút `PHÒNG THỦ KHẨN CẤP` (Lockdown).
  - Xóa `AiMetricsGrid` (chứa dữ liệu AI giả).
  - Hoàn thiện nút `XUẤT BÁO CÁO CA TRỰC` xuất file báo cáo JSON từ dữ liệu thật.
- `Dashboard/Front End/src/components/CameraMatrix/CameraMatrix.tsx` & `CameraSlot.tsx`:
  - Không tạo IP giả `192.168.1.10x` cho các ô trống; các ô chưa có camera hiển thị rõ trạng thái ô trống chờ tín hiệu từ server, còn ô có camera thật hiển thị đầy đủ `location`, `measured_fps`, `frame_index`, `human_count`, `actors` bounding boxes và live stream.
- `Dashboard/Front End/src/components/AlertLog/AlertLogModule.tsx` & `RecentThreats/ThreatRow.tsx` & `Modal/EvidencePlaybackModal.tsx`:
  - Hiển thị đầy đủ các trường từ JSON của Server (`action_type`, `description`, `reasoning`, `recommended_action`, `actors`, `visual_cues`, `nvidia_vlm_analysis`, `measured_fps`, `frame_index`, `human_count`).
- `Dashboard/Front End/src/components/views/ThreatIntelligenceView.tsx`:
  - Xóa toàn bộ danh sách IP giả và thẻ số liệu giả; hiển thị phân tích tình báo thật tổng hợp từ dữ liệu Server gửi lên (phân bố hành vi, cảnh báo vũ khí/va chạm vật lý/người ngã, danh sách đối tượng `actors`, phân tích `nvidia_vlm_analysis`).
- `Dashboard/Front End/src/components/views/DeviceManagerView.tsx`:
  - Xóa toàn bộ thiết bị giả (`sw_core_01`, `nvr_primary_01`, `cam_offline_01`).
  - Lấy trực tiếp danh sách camera thật từ dữ liệu Server gửi lên (`camera_id`, `location`, `measured_fps`, `frame_index`, `human_count`, `timestamp`, `status`), hỗ trợ kiểm tra kết nối (Ping thật tới Worker), xem thông số chi tiết và cấu hình stream.
- `Dashboard/Front End/src/components/views/SettingsView.tsx`:
  - Kết nối thật với `GET /api/settings` và `POST /api/settings` lưu trữ trên Cloudflare KV.
- `Dashboard/Front End/src/App.tsx`:
  - Tích hợp state Authentication, Settings, và truyền dữ liệu thật xuống toàn bộ các Tab.

#### 1.3. File Xóa Bỏ:
- `Dashboard/Front End/src/components/AiMetricsGrid/AiMetricsGrid.tsx` (chứa toàn bộ số liệu AI giả).

---

### 2. KỊCH BẢN KIỂM THỬ (VERIFICATION PLAN)

1. Kiểm tra biên dịch TypeScript & Vite (`pnpm run build`) đạt 0 lỗi.
2. Viết script kiểm thử End-to-End gửi đúng mẫu JSON của người dùng (`camera_id: "LAPTOP_01"`, `action_type: "FIGHTING"`, `actors`, `visual_cues`, `nvidia_vlm_analysis`) lên Worker, xác nhận dữ liệu được lưu vào KV và trả về chuẩn xác qua `/api/get-incident`, `/api/devices/cameras`, `/api/soc/overview`, `/api/settings`, `/api/auth/login`.
3. Đồng bộ bộ 3 tài liệu `AGENTS.md`, `README.md`, `PROJECT_STRUCTURE.md` theo quy tắc `[CD-06]`.
