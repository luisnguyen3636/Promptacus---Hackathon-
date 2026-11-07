# KẾ HOẠCH TRIỂN KHAI (STAGE 2 — IMPLEMENTATION PLAN)
## Chuyển đổi Toàn bộ Dashboard Frontend & Backend sang Cloudflare Worker
**Mã tài liệu:** `PLAN-CF-UNIFIED-SOC-01`  
**Dự án:** Hệ thống Giám sát An ninh & An toàn Đô thị Thông minh (Urban Safety AI-SOC)  
**Tài liệu tham chiếu:** `CloudflareWorker/SPEC_UNIFIED_SOC.md`, `AGENTS.md` (CD-01 đến CD-05)  
**Mục tiêu:** Xây dựng Edge-Native SOC hoàn chỉnh trên Cloudflare Worker với đầy đủ React Frontend (Static Assets), REST APIs, Native WebSockets, Workers AI và D1 SQL Database.

---

### DANH SÁCH CÔNG VIỆC CỤ THỂ (ATOMIC IMPLEMENTATION TASKS)

#### BƯỚC 1: CẬP NHẬT KIỂU DỮ LIỆU & SCHEMA (`CloudflareWorker/src/types.ts`)
- Mở rộng `types.ts` để bổ sung đầy đủ các interface:
  - `ISocOverviewResponse`, `ICameraDevice`, `IAIBoundingBox`, `IPtzState`, `IPtzCommandRequest`
  - `IIncidentItem`, `IIncidentPlaybackResponse`
  - `IHitlVerificationRequest`, `IHitlVerificationResponse`, `IIncidentDispatchPackage`
  - `WebSocketServerMessage`
  - Mở rộng `Env` interface với `ASSETS: Fetcher` để phục vụ Static Assets fallback.

#### BƯỚC 2: MODULE HÓA LOGIC BACKEND TẠI BIÊN (EDGE BACKEND MODULES)
1. **`src/telemetry.ts`:**
   - Triển khai `getTelemetryOverview(activeThreatCount, criticalThreatCount)` với jitter mạng tự nhiên.
   - Hàm `updateThreatScore(newScore)`.
2. **`src/camera_manager.ts`:**
   - Quản lý 4 camera SOC với tọa độ bounding box động mô phỏng kinematic bám vết AI (`updateAiTrackingFeed`).
   - Hàm `handlePtzCommand(cameraId, action, speed)` hỗ trợ Zoom In/Out (1.0x-5.0x), Pan (0-360°), Focus.
3. **`src/incident_manager.ts`:**
   - Quản lý danh sách sự cố gần đây (`getRecentIncidents`).
   - Hàm `getIncidentPlayback(id)` trích xuất bằng chứng video clip từ Rolling Buffer & VLM reasoning.
   - Hàm `updateIncidentStatus(id, newStatus)`.
4. **`src/hitl_dispatcher.ts`:**
   - Triển khai chốt chặn Operational HITL (`processHitlVerification`):
     - Ràng buộc bất biến `[CD-04]`: Kiểm tra bắt buộc `operatorId`.
     - Phân nhánh quyết định: `CONFIRM_AND_DISPATCH` (đóng gói `incidentPackage`), `DOWNGRADE_MONITOR`, `DISMISS_FALSE_POSITIVE`.
     - Lưu vết kiểm toán `[CD-05]` vào bảng `audit_logs` của D1.
5. **`src/websocket.ts`:**
   - Quản lý kết nối WebSocket thời gian thực bằng chuẩn `WebSocketPair` của Cloudflare Worker.
   - Gửi sự kiện ban đầu `CONNECTED` và loop gửi `TELEMETRY_AND_AI_TICK` (hoặc phản hồi request tick).

#### BƯỚC 3: HỢP NHẤT ROUTER CHÍNH TẠI EDGE GATEWAY (`CloudflareWorker/src/index.ts`)
- Tích hợp tất cả các nhánh định tuyến:
  - WebSocket: `/ws/live-stream` (kiểm tra `Upgrade: websocket`).
  - Telemetry: `GET /api/soc/overview`.
  - Camera & PTZ: `GET /api/devices/cameras`, `POST /api/cameras/:id/ptz`.
  - Incidents & Playback: `GET /api/incidents/recent`, `GET /api/incidents/:id/playback`.
  - Operational HITL Gate: `POST /api/incidents/:id/verify`.
  - Audit Logs: `GET /api/soc/audit-logs`.
  - Ingestion & Workers AI: `POST /api/v1/engine/evaluate`, `GET /api/v1/incidents`, `GET /api/v1/health`.
  - Static Asset Fallback: Bất kỳ request không khớp `/api/` hoặc `/ws/` sẽ được chuyển tiếp tới `env.ASSETS.fetch(request)`.

#### BƯỚC 4: CẤU HÌNH WRANGLER & PACKAGE.JSON
- Cập nhật `wrangler.toml`:
  - Thêm cấu hình `[assets]` trỏ tới thư mục `./dist` với `not_found_handling = "single-page-application"`.
- Cập nhật `CloudflareWorker/package.json`:
  - Thêm script `build:frontend`: build Vite SPA từ `Dashboard/Front End` xuất thẳng ra `CloudflareWorker/dist`.
  - Thêm script `build:worker`: chạy `tsc`.
  - Thêm script `build`: build frontend trước rồi check type worker.
  - Script `deploy`: chạy `build` và `wrangler deploy`.

#### BƯỚC 5: BUILD PRODUCTION BUNDLE & KIỂM THỬ XÁC MINH (VERIFY)
- Thực thi build frontend từ `Dashboard/Front End` xuất ra `CloudflareWorker/dist`.
- Kiểm tra toàn bộ files static (index.html, JS chunks, CSS, SVG).
- Biên dịch TypeScript cho Worker (`pnpm tsc --noEmit`).
- Kiểm tra Wrangler dev/dry-run deploy để xác nhận cấu hình Cloudflare Worker hoàn toàn hợp lệ.
