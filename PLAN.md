# KẾ HOẠCH TRIỂN KHAI (IMPLEMENTATION PLAN)
## Module: CyberGuard Ingestion & Forwarding Gateway Service (Flask)
**Dự án:** Hệ thống Giám sát An ninh & An toàn Đô thị Thông minh (Urban Safety AI-SOC)  
**Tài liệu cơ sở:** `SPEC.md`, `AGENTS.md`  
**Giai đoạn:** STAGE 2 — IMPLEMENTATION PLAN  
**Ngày soạn:** 2026-11-07  

---

### 1. DANH SÁCH FILE VÀ CẤU TRÚC THƯ MỤC

Module sẽ được xây dựng độc lập và đóng gói chuẩn SOC bên trong `Dashboard/Back End/ingestion_service/`:

```
Dashboard/Back End/ingestion_service/
├── requirements.txt            # Danh sách thư viện phụ thuộc
├── config.py                   # Cấu hình hệ thống & biến môi trường
├── schemas.py                  # Pydantic Schemas cho toàn bộ 10 miền dữ liệu & Master Payload
├── forwarder.py                # HTTP Dispatcher client, Retry backoff & Dead-Letter-Queue (DLQ)
├── routes.py                   # 11 Flask Routes chuyên biệt (POST) xử lý từng phần thông tin
├── app.py                      # Application Factory, Error Handlers, Structured Logging
├── run.py                      # Entrypoint khởi động server
└── tests/
    ├── __init__.py
    ├── mock_target_server.py   # Máy chủ giả lập Target Server để kiểm thử chuyển tiếp
    └── test_ingestion.py       # Bộ test tự động kiểm thử toàn diện 11 routes & cơ chế forward
```

---

### 2. DANH SÁCH CÁC HÀM, CLASS VÀ FUNCTION SIGNATURES

#### 2.1. Module Cấu hình (`config.py`)
- `class IngestionConfig`:
  - `GATEWAY_HOST: str = "0.0.0.0"`
  - `GATEWAY_PORT: int = 5000`
  - `TARGET_SERVER_BASE_URL: str = "http://127.0.0.1:5001"`
  - `TARGET_SERVER_TIMEOUT_MS: int = 3000`
  - `TARGET_SERVER_MAX_RETRIES: int = 3`
  - `TARGET_SERVER_API_KEY: str = "cyberguard-soc-internal-secret"`
  - `FORWARD_MODE: str = "sync"`  # "sync" hoặc "async"
  - `DLQ_STORAGE_PATH: str = "./data/dlq"`

#### 2.2. Module Thẩm định Dữ liệu (`schemas.py`)
- `class SessionData(BaseModel)`
- `class SystemConfigData(BaseModel)`
- `class PTZConfig(BaseModel)`
- `class CameraConfigItem(BaseModel)`
- `class LiveMetaData(BaseModel)`
- `class LiveSystemData(BaseModel)`
- `class ThreatOverviewData(BaseModel)`
- `class KPIData(BaseModel)`
- `class InfrastructureData(BaseModel)`
- `class BoundingBox(BaseModel)`
- `class DetectionItem(BaseModel)`
- `class MatrixTileItem(BaseModel)`
- `class CameraMatrixPayload(BaseModel)`
- `class PlaybackInfo(BaseModel)`
- `class RecentThreatItem(BaseModel)`
- `class FullCyberguardPayload(BaseModel)`

#### 2.3. Module Chuyển tiếp & DLQ (`forwarder.py`)
- `class DLQManager`:
  - `__init__(storage_path: str)`
  - `enqueue(route: str, payload: dict, error_reason: str, correlation_id: str) -> str`
  - `get_failed_records() -> List[dict]`
- `class ForwarderService`:
  - `__init__(config: IngestionConfig, dlq_manager: DLQManager)`
  - `forward(endpoint: str, payload: dict, event_type: str, correlation_id: str) -> Tuple[bool, int, dict]`
  - `_execute_with_retry(url: str, payload: dict, headers: dict) -> Tuple[bool, int, dict]`
  - `_enforce_hitl_check(event_type: str, payload: dict) -> dict`  # Chốt chặn [CD-04]

#### 2.4. Module Routes (`routes.py`)
- Blueprint: `ingestion_bp = Blueprint('ingestion', __name__, url_prefix='/api/v1')`
- Các endpoint:
  1. `POST /session`: Nhận `SessionData` -> Thẩm định -> Forward `{TARGET}/api/soc/session`
  2. `POST /config/system`: Nhận `SystemConfigData` -> Thẩm định -> Forward `{TARGET}/api/soc/config/system`
  3. `POST /config/cameras`: Nhận `List[CameraConfigItem]` -> Thẩm định -> Forward `{TARGET}/api/devices/cameras/config`
  4. `POST /live/meta`: Nhận `LiveMetaData` -> Thẩm định -> Forward `{TARGET}/api/soc/live/meta`
  5. `POST /live/system`: Nhận `LiveSystemData` -> Thẩm định -> Forward `{TARGET}/api/soc/live/system`
  6. `POST /live/threat-overview`: Nhận `ThreatOverviewData` -> Thẩm định -> Forward `{TARGET}/api/soc/threat-overview`
  7. `POST /live/kpi`: Nhận `KPIData` -> Thẩm định -> Forward `{TARGET}/api/soc/kpi`
  8. `POST /live/infrastructure`: Nhận `InfrastructureData` -> Thẩm định -> Forward `{TARGET}/api/soc/infrastructure`
  9. `POST /live/camera-matrix`: Nhận `CameraMatrixPayload` -> Thẩm định -> Forward `{TARGET}/api/devices/cameras/matrix`
  10. `POST /live/incidents`: Nhận `List[RecentThreatItem]` -> Thẩm định & HITL inspect -> Forward `{TARGET}/api/incidents/recent`
  11. `POST /ingest/full`: Nhận `FullCyberguardPayload` -> Bóc tách & Điều phối toàn diện
  12. `GET /health`: Health-check endpoint

---

### 3. DANH SÁCH THƯ VIỆN PHỤ THUỘC (DEPENDENCIES)

| Thư viện | Phiên bản | Giải trình sự cần thiết |
|---|---|---|
| `flask` | `^3.0.0` | Khung web micro-framework theo yêu cầu bắt buộc của bài toán. |
| `pydantic` | `^2.5.0` | Thẩm định cấu trúc dữ liệu nghiêm ngặt theo JSON Schema chuẩn SOC. |
| `requests` | `^2.31.0` | HTTP Client đồng bộ tin cậy, hỗ trợ connection pooling và custom timeout để forward dữ liệu sang server đích. |
| `pytest` | `^8.0.0` | Khung kiểm thử tự động phục vụ verification. |

---

### 4. KỊCH BẢN KIỂM THỬ VÀ XÁC MINH (VERIFICATION & TEST PLAN)

1. **Test Case 1: Thẩm định và chuyển tiếp thành công cho từng Route (TC-01 đến TC-10):**
   - Gửi payload chuẩn từ dữ liệu mẫu của từng phân hệ vào lần lượt 10 routes.
   - Mock Target Server nhận được đúng payload, trả về `200 OK`.
   - Gateway phản hồi HTTP 200 kèm `forward_status: "FORWARDED"`.
2. **Test Case 2: Kiểm thử Route Ingest Tổng Hợp (TC-11):**
   - Gửi toàn bộ payload JSON gốc (bao gồm session, config, live) vào `POST /api/v1/ingest/full`.
   - Xác nhận Gateway bóc tách thành công và chuyển tiếp dữ liệu đến Target Server.
3. **Test Case 3: Thẩm định lỗi Schema (TC-12 - Schema Rejection):**
   - Gửi payload sai kiểu dữ liệu (ví dụ `threat_score: 999` vượt quá range [0, 100], hoặc thiếu trường bắt buộc).
   - Gateway trả về HTTP `422 Unprocessable Entity` và không thực hiện forward.
4. **Test Case 4: Kiểm thử Khả năng Chịu lỗi khi Target Server Offline (TC-13 - Resiliency & DLQ):**
   - Tắt Mock Target Server hoặc cấu hình URL không tồn tại.
   - Gateway thực hiện retry 3 lần, phát hiện timeout/connection error, tự động lưu gói tin vào Dead Letter Queue (`DLQ`) trên ổ đĩa và trả về mã lỗi có cấu trúc.
5. **Test Case 5: Kiểm tra Chốt chặn An toàn HITL (TC-14 - Rule `[CD-04]` Enforcement):**
   - Gửi sự cố mức `CRITICAL` và `HIGH` chưa có `OPERATOR_CONFIRMED`.
   - Xác minh Gateway gắn nhãn `requires_operator_verification = True` và cô lập luồng cảnh báo tự động ra bên ngoài.

---

---

### 5. KẾ HOẠCH TRIỂN KHAI CHO TỰ ĐỘNG HÓA PUBLIC HTTPS TUNNEL & CAMERA STREAMING (FEATURE ADDENDUM)

#### 5.1. Danh sách Tác vụ (Atomic Tasks)
1. **Tác vụ 1 (Server In-Browser Watch Player):**
   - Bổ sung route `/watch`, `/player`, `/video` trong `src/urbansoc/server/inference_server.py`.
   - Phục vụ giao diện HTML5 Video Player tối ưu xem trên điện thoại và máy tính, tự động kết nối `/stream.mjpg` và fetch trạng thái từ `/api/v1/dashboard/state`.
2. **Tác vụ 2 (Edge Camera Client Tunneling):**
   - Cập nhật `AI/Human/client.py` hỗ trợ cờ `--tunnel` (mặc định bật) và in URL HTTPS công khai khi kết nối.
3. **Tác vụ 3 (Tự động hóa toàn diện trong `start.sh`):**
   - Nâng cấp luồng xử lý `client|camera|edge)` trong `start.sh`:
     - Tự động kiểm tra tính khả dụng của AI-SOC Server trên cổng chỉ định (8000).
     - Nếu chưa chạy: tự khởi chạy server ngầm, chờ HTTP 200 từ `/api/v1/cameras`.
     - Kích hoạt Cloudflare Tunnel và trích xuất URL HTTPS dạng `https://*.trycloudflare.com`.
     - Lưu URL vào `/tmp/soc_public_url.txt` và in banner nổi bật chỉ dẫn người dùng mở trình duyệt xem stream video.
     - Dọn dẹp tài nguyên (dừng tunnel + auto-server) khi tắt client.
4. **Tác vụ 4 (Bộ kiểm thử tự động đạt >= 30 test cases):**
   - Xây dựng file test `tests/test_camera_tunnel_streaming.py` bao quát:
     - URL parsing & Cloudflare regex
     - Endpoint `/watch` trả về HTML player chuẩn
     - Endpoint `/stream.mjpg` trả về header MJPEG chính xác
     - Kiểm thử logic khởi động và cleanup tunnel
     - Kiểm thử client parameter parser

---

---

### 6. KẾ HOẠCH TRIỂN KHAI XÓA BỎ 100% DỮ LIỆU DUMMY / MOCK & ĐẢM BẢO 100% CẢNH BÁO TỪ NVIDIA AI

#### 6.1. Danh sách Tác vụ (Atomic Tasks)
1. **Tác vụ 1: Backend Zero Dummy Cleanup (`Dashboard/Back End`)**
   - Trong `src/incidentManager.js`: Đặt `INITIAL_INCIDENTS = []`, `incidents = []`.
   - Trong `src/cameraManager.js`:
     - Thiết lập `aiAlert: null` và `boundingBoxes: []` cho toàn bộ 4 camera ban đầu (`cam_01` -> `cam_04`).
     - Gỡ bỏ hoàn toàn logic dao động sóng sin (`Math.sin(tick)`) tạo bounding box giả trong `updateAiTrackingFeed`.
   - Trong `src/telemetryEngine.js`: Đặt `threatScore: 0`, `threatLevel: 'LOW'`, `status: 'SAFE'`.
2. **Tác vụ 2: Front End Zero Mock Cleanup (`Dashboard/Front End`)**
   - Trong `src/data/mockData.ts`:
     - Đặt `MOCK_INCIDENTS = []`.
     - Đặt `MOCK_CAMERAS`: `boundingBoxes: []`, `aiAlert: null`.
     - Đặt `MOCK_OVERVIEW`: `threatScore: 0`, `openThreats: 0`, `criticalThreats: 0`, `threatLevel: 'LOW'`, `status: 'SAFE'`.
   - Trong `src/components/views/LiveVideoWallView.tsx`: Loại bỏ mã cứng `cam_05`, `cam_06` với bounding box giả, sử dụng trực tiếp danh sách camera thực từ telemetry/backend.
   - Trong `src/components/views/IncidentFeedView.tsx`: Thay thế số liệu mã cứng ("14 Incidents", "2 Critical") bằng hàm tính động `incidents.length` và `incidents.filter(i => i.severity === 'CRITICAL').length`. Hiển thị trạng thái "NO ACTIVE THREATS" khi danh sách trống.
   - Trong `src/components/RecentThreats/RecentThreatsTable.tsx`: Hiển thị thông báo sạch "NO ACTIVE THREATS DETECTED — 100% REAL-TIME NVIDIA AI MONITORING ACTIVE" khi không có sự cố.
3. **Tác vụ 3: Build & Package Front End**
   - Chạy `npm run build` trong `Dashboard/Front End` để biên dịch vào thư mục `dist/` phục vụ web app.
4. **Tác vụ 4: Kiểm thử Tự động & Xác minh Chặt chẽ (>= 30 Test Cases)**
   - Cập nhật và bổ sung test cases trong `Dashboard/Back End/tests/test_backend_suite.py`:
     - Kiểm thử trạng thái khởi động sạch (Clean baseline): 0 incidents, 0 bounding boxes ban đầu, 0 dummy alerts.
     - Kiểm thử 100% alert xuất phát từ NVIDIA AI: khi AI POST detection, camera bật viền cảnh báo, nhãn ALERT, banner reasoning và WebSocket broadcast.
     - Bảo đảm toàn bộ test cases (> 40 tests) pass 100%.

---

---

### 7. KẾ HOẠCH TRIỂN KHAI KHẮC PHỤC YOLO ACTION DETECTION & TỐI ƯU HÓA SUY LUẬN REAL-TIME

#### 7.1. Danh sách Tác vụ (Atomic Tasks)
1. **Tác vụ 1: Khắc phục Model Path Resolution trong `yolo_pose.py`**
   - Mở rộng hàm `_resolve_model_path`: Thêm đường dẫn tính từ vị trí file nguồn `yolo_pose.py` (`os.path.join(os.path.dirname(__file__), "../../../yolo/yolo11n-pose.pt")`), thư mục gốc `Promptacus---Hackathon-/AI/Human/yolo/`, và biến môi trường `YOLO_MODEL_PATH`.
2. **Tác vụ 2: Tối ưu hóa Real-time Frame Ingestion trong `server.js`**
   - Trong `requestIntermediateAiAnalysis`: Thêm header `'X-Batch-AI': 'false'` và `'X-Sync-VLM': 'true'` để AI Server xử lý suy luận frame ngay lập tức và phản hồi kết quả trực tiếp.
   - Trong `handleIngestFrame`: Luôn cập nhật bounding boxes cho camera khi có người (`aiAnalysis?.humans`), bất kể là trạng thái `NORMAL` hay có cảnh báo, để giao diện luôn bám vết mượt mà.
3. **Tác vụ 3: Tối ưu hóa Chuẩn hóa Bounding Box trong `cameraManager.js`**
   - Đọc trực tiếp tọa độ chuẩn hóa `x, y, w, h` từ AI detection (khi nằm trong khoảng `[0..1]`), hoặc tự động nhận diện tỷ lệ theo độ phân giải ảnh thực tế.
   - Sửa logic gán nhãn severity: giữ nguyên `NORMAL` cho các đối tượng có `threat_level === 'LOW'`.
4. **Tác vụ 4: Cải tiến Bộ Quy tắc Hành vi & Biometrics trong `rules.py` & `kinematics.py`**
   - Trong `kinematics.py`: Bổ sung tính toán `spine_angle` từ vector đầu - vai và độ nghiêng trục hai vai khi hông bị khuất.
   - Trong `rules.py`:
     - `FALLEN`: Phát hiện ngã khi thân người hoặc hai vai nghiêng ngang mạnh (> 35°), hoặc đầu tụt ngang/thấp hơn vai.
     - `WEAPON_THREAT`: Nới góc khuỷu tay (>= 115°), hỗ trợ chĩa vũ khí thẳng về phía camera.
     - `KNIFE_THREAT`: Tối ưu ngưỡng vận tốc cổ tay (>= 400 px/s) và tư thế thủ thế cận chiến.
     - `HANDS_UP`: Nhận diện giơ 1 hoặc 2 tay lên cao qua đầu.
     - `FIGHTING`: Hỗ trợ phát hiện ra đòn/đấm nhanh liên tục cho đối tượng đơn lẻ (`single-person fighting / boxing strikes`).
5. **Tác vụ 5: Tối ưu Hysteresis State Machine trong `state_machine.py` & `camera_context.py`**
   - Cấu hình `fast_track_debounce_frames = 2` để phản ứng nhạy bén với các mối đe dọa cận kề.
   - `CameraContext.process_detections` ưu tiên báo cáo cảnh báo cấp bách ngay khi phát hiện.
6. **Tác vụ 6: Kiểm thử Tự động & Xác minh**
   - Chạy toàn bộ test suites của cả Backend (`Dashboard/Back End/tests`) và AI Engine (`AI/Human/tests`).
   - Đảm bảo toàn bộ test cases pass 100%.

---

### GIAI ĐOẠN 11: SAO CHÉP & ĐỒNG BỘ TOÀN DIỆN LOGIC DETECT TỪ DỰ ÁN HUMAN DETECT

1. **Tác vụ 1: Tuân thủ nghiêm ngặt nguyên tắc KHÔNG sửa đổi dự án nguồn `/home/test/Hackathon-Test-/HUMAN DETECT`**
   - Chỉ đọc (Read-only) từ `/home/test/Hackathon-Test-/HUMAN DETECT`.
   - Tuyệt đối không xóa, sửa, tạo hoặc ghi đè bất kỳ file nào trong `/home/test/Hackathon-Test-/`.
2. **Tác vụ 2: Sao chép các tệp logic detect vào `/home/test/Promptacus---Hackathon-/AI/Human/`**
   - Sao chép: `yolo_pose_detector.py`, `behavior_detector.py`, `models.py`, `clip_recorder.py`, `rate_limiter.py`, `alert_models.py`, `ai_service.py`, `alert_client.py`, `human_detection.py`, `camera_recorder.py`, `pose_detector.py`, `test_system.py`, `test_alert_system.py`.
   - Đảm bảo `yolo_pose_detector.py` có cơ chế tìm kiếm `yolo11n-pose.pt` thông minh qua nhiều vị trí.
3. **Tác vụ 3: Đồng bộ Debounce State Machine trong `AI/Human/src/urbansoc/behavior/engine.py`**
   - Đảm bảo `engine.py` tuân thủ nguyên tắc debounce lọc nhiễu 2-frame để `test_state_machine.py` đạt 100% pass.
4. **Tác vụ 4: Kiểm chứng toàn diện (Verification & Test Execution)**
   - Chạy `test_system.py` và `test_alert_system.py` trực tiếp trong `AI/Human`.
   - Chạy toàn bộ 281 tests trong `AI/Human/tests/`.
   - Chạy toàn bộ 46 tests trong `Dashboard/Back End/tests/`.
   - Đảm bảo vượt mốc 30 test cases quy định trong `AGENTS.md`.

---

**[PLAN AUTO-APPROVED]**
