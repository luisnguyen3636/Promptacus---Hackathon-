# KẾ HOẠCH TRIỂN KHAI: KẾT NỐI CAMERA CLIENT, LIVE STREAMING & AI ALERT
# CYBERGUARD AI · SOC v2.1

---

> **Tài liệu căn cứ:** `AGENTS.md` (Tuân thủ CD-01 đến CD-05) & `Dashboard/Back End/SPEC.md`  
> **Module:** Camera Streaming & AI Alert Engine  
> **Giai đoạn:** `STAGE 2 & 3 — PLAN & AUTO-APPROVAL`  
> **Trạng thái:** `[PLAN AUTO-APPROVED]`

---

## 1. MỤC TIÊU TRIỂN KHAI
1. Nâng cấp `Dashboard/Back End/src/cameraManager.js`:
   - Lưu trữ bộ đệm khung hình JPEG (latest frame buffer) cho từng camera.
   - Thêm phương thức `saveCameraFrame(cameraId, frameBuffer, metadata)` cập nhật thời gian thực, đo lường FPS và bitrate.
   - Cung cấp `getCameraLatestFrame(cameraId)`.
   - Lưu trữ AI Alert trạng thái trực tiếp trên camera (`aiAlert: { hasAlert, type, severity, message, timestamp }`).
2. Nâng cấp `Dashboard/Back End/server.js`:
   - Tiếp nhận đăng ký camera qua `POST /api/v1/cameras/register`.
   - Tiếp nhận luồng frame JPEG từ camera client qua `POST /api/v1/cameras/:id/stream` và `POST /api/v1/ingest/frame` (hỗ trợ `express.raw({ type: 'image/jpeg', limit: '20mb' })`).
   - Phát luồng MJPEG `GET /api/v1/cameras/:id/stream` và `GET /api/v1/cameras/:id/stream.mjpg`.
   - Phát ảnh tĩnh `GET /api/v1/cameras/:id/snapshot`.
   - Đồng bộ cảnh báo AI tự động lên trường `aiAlert` của camera và gửi qua WebSocket `/ws/live-stream`.
3. Nâng cấp Front-end (`Dashboard/Front End`):
   - Mở rộng kiểu dữ liệu `ICameraDevice` trong `src/types/soc.ts` thêm `aiAlert` và `snapshotUrl`.
   - Nâng cấp `CameraSlot.tsx`:
     - Render thẻ `<img>` kết nối trực tiếp `camera.streamUrl` hoặc snapshot tự động làm mới.
     - Xử lý khi có AI Alert: Kích hoạt viền đỏ chớp nháy cảnh báo nguy cấp (`border-[#EF4444] animate-pulse`).
     - Hiển thị Alert Banner trên đầu ô camera: `[CẢNH BÁO AI: HUNG KHÍ / VŨ KHÍ 98%]`, `[CẢNH BÁO AI: NGƯỜI NGÃ]`, v.v.
     - Hiển thị Bounding Box đè trực tiếp lên hình ảnh video thật.
     - Nút tác chiến nhanh "XÁC MINH HITL" mở thẳng Modal thẩm định bằng chứng.
   - Biên dịch lại ứng dụng bằng `npm run build`.
4. Viết bổ sung và mở rộng bộ kiểm thử tự động trong `tests/test_backend_suite.py` để đạt tối thiểu 36+ test cases bao quát mọi tính năng mới.

---

## 2. DANH MỤC TỆP TIN THỰC HIỆN

| # | Tệp tin | Thao tác | Mô tả |
|---|---|---|---|
| 1 | `Dashboard/Front End/src/types/soc.ts` | Sửa đổi | Bổ sung `aiAlert` và `snapshotUrl` vào interface `ICameraDevice` |
| 2 | `Dashboard/Front End/src/components/CameraMatrix/CameraSlot.tsx` | Sửa đổi | Hiển thị luồng hình ảnh trực tiếp, viền cảnh báo AI, banner và bounding boxes |
| 3 | `Dashboard/Back End/src/cameraManager.js` | Sửa đổi | Quản lý Frame buffer JPEG, AI alerts, đo FPS, lấy snapshot |
| 4 | `Dashboard/Back End/server.js` | Sửa đổi | Cung cấp endpoints đăng ký, nhận frame JPEG, phát MJPEG stream & snapshot |
| 5 | `Dashboard/Front End/dist/` | Biên dịch | Chạy `npm run build` cập nhật bản phân phối Web App mới |
| 6 | `Dashboard/Back End/tests/test_backend_suite.py` | Cập nhật | Kiểm thử luồng register camera, push frame, get MJPEG, get snapshot, alert overlay |

---

[PLAN AUTO-APPROVED]

## 3. PLAN BỔ SUNG — ALERT PROVENANCE & ASYNC NVIDIA VLM

1. `AI/Human/src/urbansoc/ai/nvidia_vlm.py`: stamp NVIDIA provenance only after a valid remote analysis response; mark local and fallback results separately.
2. `AI/Human/src/urbansoc/server/inference_server.py`: keep cloud VLM on the background worker and publish its final status with the analysis event.
3. `AI/Human/src/urbansoc/domain/webhook_models.py` and `AI/Human/src/urbansoc/telemetry/webhook_dispatcher.py`: preserve the structured VLM result in webhook payloads.
4. `Dashboard/Back End/server.js`: consume the AI server SSE feed; create alerts only from completed, unsuppressed NVIDIA results. Remove heuristic and test-action alert creation.
5. `Dashboard/Back End/src/incidentManager.js` and `src/hitlDispatcher.js`: persist provenance and reject dispatch of incidents without a qualified NVIDIA result.
6. `Dashboard/Back End/tests/test_backend_suite.py` and `AI/Human/tests/test_nvidia_vlm.py`: cover real-result provenance, local/fallback rejection, and candidate gating.

**[PLAN AUTO-APPROVED]**
