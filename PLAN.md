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

**[PLAN VERIFICATION READY]**
