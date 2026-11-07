# KẾ HOẠCH TRIỂN KHAI (STAGE 2 — IMPLEMENTATION PLAN)
## Tích Hợp Payload Nhận Diện Thực Từ AI Detect & Loại Bỏ Dữ Liệu Giả
**Mã tài liệu:** `PLAN-AI-REAL-INGESTION-01`  
**Dự án:** Hệ thống Giám sát An ninh & An toàn Đô thị Thông minh (Urban Safety AI-SOC)  
**Tài liệu tham chiếu:** `CloudflareWorker/SPEC_AI_INTEGRATION.md`, `AGENTS.md` (CD-01 đến CD-05)  

---

### DANH SÁCH CÔNG VIỆC CHI TIẾT (ATOMIC TASKS)

#### TASK 1: MỞ RỘNG DATA SCHEMAS & INTERFACES (`CloudflareWorker/src/types.ts`)
- Định nghĩa interface `IAIRealDetectionPayload`, `IAISubjectData`, `IAISubjectKinematics`, `IAISubjectKeypoint`.
- Cập nhật `IIncidentItem` để lưu trữ thêm `evidenceSnapshotBase64`, `forensicHash`, `rawDetection` và danh sách keypoints.

#### TASK 2: NÂNG CẤP BACKEND MODULES ĐÓN DỮ LIỆU THỰC
1. **`CloudflareWorker/src/camera_manager.ts`:**
   - Xóa bỏ dữ liệu mock tĩnh `cam_01`, `cam_02`... Khởi tạo danh sách camera rỗng hoặc dynamic fleet registry.
   - Thêm hàm `upsertCameraFromAiDetection(camera, subjects, fullImageWidth, fullImageHeight, imageBase64)`:
     * Tự động đăng ký camera mới nếu chưa có trong danh sách.
     * Chuẩn hóa tọa độ Bounding Box pixel (`[x1, y1, x2, y2]`) sang tỷ lệ tương đối `[x, y, w, h]` từ `0.0` đến `1.0`.
2. **`CloudflareWorker/src/incident_manager.ts`:**
   - Xóa bỏ các incident mock `inc_901` và `inc_902`.
   - Thêm hàm `createIncidentFromAiDetection(payload: IAIRealDetectionPayload)`:
     * Tạo incident với ID `payload.event_id`.
     * Gán trạng thái `PENDING_VERIFICATION` (HITL gate `[CD-04]`).
     * Lưu ảnh `full_image.image_base64` và `crop_image_base64`.
3. **`CloudflareWorker/src/telemetry.ts`:**
   - Cập nhật hàm `updateThreatScoreFromAi(threatScore: number, isCritical: boolean)`.
4. **`CloudflareWorker/src/index.ts`:**
   - Thêm route: `POST /api/v1/ai/detection` (và alias `POST /api/v1/webhook`).
   - Xử lý payload: validate -> cập nhật camera fleet -> tạo incident -> ghi D1 `incidents` & `audit_logs` -> broadcast WebSocket tới tất cả client.

#### TASK 3: LOẠI BỎ DỮ LIỆU GIẢ TẠI FRONTEND
1. **`Dashboard/Front End/src/data/mockData.ts`:**
   - Xóa các mảng mock tĩnh, thay thế bằng trạng thái ban đầu sạch (Empty lists / Zero metrics).
2. **`Dashboard/Front End/src/hooks/useSocTelemetry.ts`:**
   - Khởi tạo `cameras: []`, `incidents: []`.
   - Lắng nghe thêm sự kiện WebSocket broadcast `NEW_INCIDENT` hoặc `CAMERA_UPDATE` từ AI.
3. **`Dashboard/Front End/src/components/views/IncidentFeedView.tsx`:**
   - Chuyển các thẻ thống kê sang tính toán động: `incidents.length`, số lượng Critical, v.v.
4. **`Dashboard/Front End/src/components/Modal/EvidencePlaybackModal.tsx`:**
   - Hiển thị trực tiếp ảnh chụp Base64 thật kèm Keypoints và SHA-256 hash từ AI detector.

#### TASK 4: BUILD & VERIFY VỚI PAYLOAD THỰC TẾ
- Build lại Frontend SPA và Worker: `npm run build`.
- Khởi chạy test script mô phỏng gửi đúng mẫu JSON AI payload của người dùng tới `POST /api/v1/ai/detection`.
- Xác minh:
  * Trả về HTTP 201 Created.
  * Camera `LAPTOP_TEST` xuất hiện trong `/api/devices/cameras` với Bounding Box chuẩn hóa.
  * Incident `EVT_20261107_171500_LAPTOP_TEST` xuất hiện trong `/api/incidents/recent` với ảnh thật.
  * Thao tác Operational HITL verify thành công `[CD-04]`.
