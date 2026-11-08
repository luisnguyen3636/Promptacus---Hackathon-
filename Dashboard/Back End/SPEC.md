# ĐẶC TẢ KỸ THUẬT: KẾT NỐI CAMERA CLIENT, LIVE STREAMING & XỬ LÝ ALERT AI
# CYBERGUARD AI · SOC v2.1
## Kết nối Trực tiếp Camera Client, Hiển thị Khung hình Live Video & Xử lý Cảnh báo Thời gian thực từ AI

---

> **Tài liệu căn cứ:** `AGENTS.md` (Tuân thủ CD-01 đến CD-05) & Yêu cầu Người dùng  
> **Module:** Camera Streaming & AI Alert Engine  
> **Vị trí:** `Dashboard/Back End/SPEC.md`  
> **Trạng thái:** `[SPEC AUTO-APPROVED]`

---

## 1. MỤC TIÊU & PHẠM VI

1. **Kết nối Toàn diện Camera Client (`EdgeCameraClient` / `client.py`):**
   - Đăng ký camera qua endpoint chuẩn `POST /api/v1/cameras/register` (hỗ trợ `camera_id`, `name`, `latitude`, `longitude`, `fps`, `ip`).
   - Tiếp nhận luồng khung hình JPEG thô thời gian thực qua `POST /api/v1/cameras/:id/stream` hoặc `POST /api/v1/ingest/frame` (truyền tải bằng header `X-Camera-ID`, `X-Timestamp-Ms`, `X-Camera-Name`, `X-Test-Action`).
   - Tự động duy trì trạng thái `ONLINE`, đo lường FPS thực tế, băng thông bitrate và lưu trữ bộ đệm khung hình mới nhất (Latest Frame Buffer).

2. **Hiển thị Hình ảnh Trực tiếp trên Cửa sổ Camera (Live Video Display):**
   - Cung cấp luồng stream chuẩn MJPEG đa phần (`multipart/x-mixed-replace; boundary=frame`) tại `GET /api/v1/cameras/:id/stream` và `GET /api/v1/cameras/:id/stream.mjpg`.
   - Cung cấp ảnh chụp tức thời chất lượng cao tại `GET /api/v1/cameras/:id/snapshot`.
   - Cập nhật thành phần [`CameraSlot.tsx`](file:///home/test/Promptacus---Hackathon-/Dashboard/Front%20End/src/components/CameraMatrix/CameraSlot.tsx) và [`LiveVideoWallView.tsx`](file:///home/test/Promptacus---Hackathon-/Dashboard/Front%20End/src/components/views/LiveVideoWallView.tsx) trên Front-end để tải và render trực tiếp hình ảnh live stream từ camera client.
   - Nếu camera chưa gửi luồng hoặc tạm mất tín hiệu, tự động hiển thị màn hình chờ Standby/CCTV Canvas công nghệ cao kèm thông báo trạng thái.

3. **Xử lý Cảnh báo (Alerts) Tức thì do AI Suy luận & Phát hiện:**
   - Tiếp nhận dữ liệu cảnh báo từ AI (YOLOv11-Pose + NVIDIA VLM) qua Webhook/Ingestion (`POST /api/v1/incidents` hoặc phản hồi stream POST).
   - Nhận diện các lớp nguy cơ an ninh cao:
     - `WEAPON_THREAT`, `KNIFE_THREAT`: Cầm hung khí, dao nhọn, vật sắc nhọn.
     - `FALLEN`: Nạn nhân ngã quỵ hoặc bất động trên sàn.
     - `FIGHTING`, `SNATCHING`, `PURSUIT`: Ẩu đả, cướp giật, rượt đuổi.
     - `INTRUSION`, `LOITERING`, `CROUCHING`: Đột nhập khu vực cấm, lảng vảng đáng ngờ.
   - Khi có cảnh báo AI trên camera:
     - Cửa sổ camera lập tức kích hoạt viền chớp đỏ/vàng cảnh báo (`CRITICAL_ALERT` / `HIGH_ALERT`).
     - Hiển thị Banner cảnh báo hành vi trên đầu cửa sổ camera với mức độ đe dọa và điểm tin cậy (`98% CONFIDENCE`).
     - Vẽ Bounding Box đè chính xác lên khung hình live video.
     - Bổ sung nút bấm tác chiến nhanh "XÁC MINH HITL" ngay trên ô camera để mở modal thẩm định và điều phối lực lượng.
     - Phát âm thanh/siren cảnh báo trực quan trên Dashboard.

4. **Bảo tồn Ràng buộc [CD-04] & [CD-05]:**
   - Mọi cảnh báo khi chuyển sang điều phối bắt buộc phải qua chốt chặn Vận hành viên (Operational HITL).
   - Bộ kiểm thử tự động đạt tối thiểu 30 test cases hợp lệ.

---

## 2. KIẾN TRÚC API & LUỒNG DỮ LIỆU STREAMING

```
[Camera Client (Webcam / Laptop)]
         │
         ├── 1. POST /api/v1/cameras/register (Đăng ký Camera ID & GPS)
         │
         ├── 2. POST /api/v1/cameras/:id/stream (Gửi JPEG Binary Frames)
         ▼
[Dashboard Backend Core (server.js)]
         │
         ├── 3. Cập nhật Frame Buffer & AI Bounding Boxes (cameraManager.js)
         ├── 4. Tiếp nhận Alert & Threat Scoring (incidentManager.js & telemetryEngine.js)
         │
         ├── 5. GET /api/v1/cameras/:id/stream (Phát MJPEG Stream 30 FPS)
         ├── 6. GET /api/v1/cameras/:id/snapshot (Phát Snapshot JPEG)
         ├── 7. WebSocket /ws/live-stream (Bắn Bounding Boxes & INCIDENT_ALERT)
         ▼
[SOC Dashboard Web App (CameraSlot.tsx)]
         │
         ├── Hiển thị Live Video trực tiếp trong ô Camera
         ├── Hiển thị Viền cảnh báo đỏ nhấp nháy khi có Alert
         └── Vẽ Bounding Box đè lên luồng video thực tế
```

## 3. SPEC BỔ SUNG — NVIDIA VLM VERIFIED ALERTS (2026-11-08)

- YOLO/kinematic output and `X-Test-Action` are candidate signals only; they must never create `aiAlert`, emit `INCIDENT_ALERT`, or authorize dispatch.
- The Dashboard forwards frames to `/api/v1/ingest/frame` without waiting synchronously for the cloud VLM. The AI server runs NVIDIA NIM analysis on its bounded background worker and publishes completed results through `/api/v1/dashboard/events`.
- An alert requires `nvidia_vlm_analysis.source == "nvidia_nim_vlm"`, `analysis_status == "completed"`, a non-normal action, `HIGH` or `CRITICAL` severity, a reasoning summary, and no false-positive suppression flag.
- Local-only, mock, queued, malformed, timed-out, and fallback results remain candidates and cannot trigger camera alerts or `CONFIRM_AND_DISPATCH`.
- External `POST /api/v1/incidents` payloads are untrusted candidates even if they claim NVIDIA provenance; only the Dashboard's connection to the configured AI inference SSE stream can promote a completed model result to an alert.
- Incident records retain the VLM result and provider/model provenance. Dispatch continues to require an operator ID and a VLM-verified incident.

**[SPEC AUTO-APPROVED]**
