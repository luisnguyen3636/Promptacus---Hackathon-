# KẾ HOẠCH TRIỂN KHAI (IMPLEMENTATION PLAN)
## Refactor: Tích Hợp Live Stream Laptop, Khắc Phục Zoom Matrix 2x2, Alert Log Rút Gọn (20% Modal) & Tái Cấu Trúc Menu

**Dự án:** Hệ thống Giám sát An ninh & An toàn Đô thị Thông minh (Urban Safety AI-SOC)  
**Tài liệu Spec liên kết:** `SPEC_STREAM_ZOOM_ALERT_REFACTOR.md`  
**Giai đoạn:** BƯỚC 2: LẬP KẾ HOẠCH TRIỂN KHAI (STAGE 2 — IMPLEMENTATION PLAN)  
**Tuân thủ:** AGENTS.md (CD-01 đến CD-06)  
**Ngày soạn thảo:** 2026-11-07  

---

### 1. DANH SÁCH FILE ẢNH HƯỞNG

#### 1.1. File Tạo Mới:
- `Dashboard/Front End/src/components/AlertLog/AlertLogModule.tsx`: Module Alert Log rút gọn thay thế cho ThreatScoreModule, hiển thị các cảnh báo thời gian thực và hỗ trợ chế độ mở rộng thành 20% right menu modal.
- `Dashboard/Front End/src/components/AlertLog/AlertLogItem.tsx`: Từng hàng cảnh báo tinh gọn (Badge mức độ nguy hiểm, mã camera, thời gian, hành vi phát hiện, nút xem nhanh).

#### 1.2. File Sửa Đổi:
- `CloudflareWorker/wrangler.toml`: Thêm biến `LIVE_CAMERA_STREAM_URL = "https://means-brick-determined-send.trycloudflare.com/api/v1/cameras/LAPTOP_01/stream"`.
- `CloudflareWorker/src/types.ts`: Bổ sung `LIVE_CAMERA_STREAM_URL?: string` vào interface `Env`.
- `CloudflareWorker/src/index.ts`: Bổ sung route proxy `GET /api/v1/cameras/:id/stream` và `GET /api/cameras/:id/stream` chuyển tiếp luồng video với CORS headers.
- `CloudflareWorker/src/camera_manager.ts`: Khởi tạo sẵn camera `LAPTOP_01` trong registry với streamUrl trỏ về endpoint stream.
- `Dashboard/Front End/src/types/soc.ts`: Mở rộng interface `ICameraDevice` và bổ sung `ICompactAlertLog`.
- `Dashboard/Front End/src/data/mockData.ts`: Khởi tạo sẵn thông tin camera `LAPTOP_01` trong `MOCK_CAMERAS`.
- `Dashboard/Front End/src/components/CameraMatrix/CameraMatrix.tsx`: Thêm state phóng to/thu nhỏ `zoomedCameraId`, nút chuyển đổi 1x1 / 2x2, xử lý click zoom từng camera.
- `Dashboard/Front End/src/components/CameraMatrix/CameraSlot.tsx`: Hỗ trợ hiển thị video stream (MJPEG `<img>` hoặc stream element) bên dưới canvas overlay.
- `Dashboard/Front End/src/hooks/useCctvCanvas.ts`: Hỗ trợ vẽ AI Bounding Boxes trên luồng stream đang phát.
- `Dashboard/Front End/src/components/views/DashboardView.tsx`: Thay `ThreatScoreModule` bằng `AlertLogModule`, quản lý state `zoomedCameraId`, chia tỷ lệ 80% camera và 20% right menu modal khi phóng to.
- `Dashboard/Front End/src/components/Sidebar.tsx`: Gỡ bỏ 2 tab `Live Video Wall` và `AI Analyzer`.
- `Dashboard/Front End/src/App.tsx`: Gỡ bỏ import và định tuyến của 2 tab đã xóa.
- `AGENTS.md`, `README.md`, `PROJECT_STRUCTURE.md`: Đồng bộ bộ ba tài liệu bắt buộc theo CD-06.

#### 1.3. File Xóa Bỏ:
- `Dashboard/Front End/src/components/views/AiAnalyzerView.tsx`
- `Dashboard/Front End/src/components/views/LiveVideoWallView.tsx`

---

### 2. DANH SÁCH HÀM & CHỮ KÝ HÀM (FUNCTION SIGNATURES)

1. **Cloudflare Worker Stream Proxy:**
   - `handleCameraStreamProxy(request: Request, env: Env, cameraId: string): Promise<Response>`: Proxy luồng video multipart stream từ `env.LIVE_CAMERA_STREAM_URL` về browser.
2. **Camera Registry Initialization:**
   - `initDefaultFleet(env?: Env): void`: Đảm bảo `LAPTOP_01` luôn tồn tại trong memory registry với stream URL chính xác.
3. **Frontend Zoom & Alert Layout:**
   - `toggleCameraZoom(cameraId: string | null): void`: Chuyển đổi giữa ma trận 2x2 và chế độ quan sát chuyên sâu.
   - `handleSelectAlert(incident: IIncidentItem): void`: Mở modal xem bằng chứng và kích hoạt thẩm định HITL.

---

### 3. CÁC BƯỚC THỰC HIỆN CHI TIẾT (ATOMIC EXECUTION TASKS)

- **Bước 1 (Backend):** Cấu hình `wrangler.toml`, cập nhật `types.ts`, `camera_manager.ts`, và thêm route stream proxy trong `index.ts`.
- **Bước 2 (Frontend Clean-up):** Xóa 2 file view `AiAnalyzerView.tsx`, `LiveVideoWallView.tsx`. Cập nhật `Sidebar.tsx` và `App.tsx`.
- **Bước 3 (Camera Stream & Zoom):** Cập nhật `CameraSlot.tsx`, `useCctvCanvas.ts`, `mockData.ts`, và `CameraMatrix.tsx` để hỗ trợ hiển thị luồng stream và logic phóng to thu nhỏ.
- **Bước 4 (Alert Log & 80/20 Layout):** Tạo `AlertLogModule.tsx`, tích hợp vào `DashboardView.tsx` với cơ chế mở rộng thành right menu 20% khi zoom.
- **Bước 5 (Verification & Build Check):** Chạy `pnpm run build` và kiểm thử tích hợp.
- **Bước 6 (Documentation Sync):** Đồng bộ `AGENTS.md`, `README.md`, `PROJECT_STRUCTURE.md`.

---

**[STATUS: PLAN READY FOR EXECUTION]**
