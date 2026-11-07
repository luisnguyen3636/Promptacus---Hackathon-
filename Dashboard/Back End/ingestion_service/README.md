# CyberGuard Ingestion & Forwarding Gateway Service

Dịch vụ Ingestion & Forwarding Gateway viết bằng Flask, đóng vai trò tiếp nhận các luồng dữ liệu giám sát an ninh chuẩn hóa từ camera telemetry, hệ thống phân tích AI, thông tin phiên làm việc, chỉ số hạ tầng và các sự cố an ninh đe dọa (Incidents/Threats).

Hệ thống bóc tách dữ liệu JSON tổng hợp thành các routes chuyên biệt trong Flask để kiểm soát độc lập, thẩm định chặt chẽ theo Pydantic schema từng phần, sau đó chuyển tiếp (forward/push) dữ liệu sang Máy chủ Mục tiêu (`TARGET_SERVER`) qua HTTP POST với đầy đủ metadata kiểm toán (audit headers, correlation IDs, timestamps).

---

## 1. Cấu trúc Thư mục

```
Dashboard/Back End/ingestion_service/
├── app.py                      # Application Factory, Error Handlers, Structured Logging
├── config.py                   # Cấu hình hệ thống & biến môi trường
├── forwarder.py                # HTTP Dispatcher client, Retry backoff & Dead-Letter-Queue (DLQ)
├── requirements.txt            # Danh sách thư viện phụ thuộc
├── routes.py                   # 11 Flask Routes chuyên biệt (POST) xử lý từng phần thông tin
├── run.py                      # Entrypoint khởi động server
├── schemas.py                  # Pydantic Schemas cho toàn bộ 10 miền dữ liệu & Master Payload
├── README.md                   # Hướng dẫn sử dụng & tài liệu vận hành
└── tests/
    ├── mock_target_server.py   # Máy chủ giả lập Target Server để kiểm thử chuyển tiếp
    └── test_ingestion.py       # Bộ test tự động kiểm thử toàn diện 16 test cases
```

---

## 2. Bảng Danh mục 11 Routes POST

Tất cả các route tiếp nhận yêu cầu bằng phương thức **POST** và chuyển tiếp sang máy chủ đích (`TARGET_SERVER`):

| # | Route Gateway | Phương thức | Dữ liệu xử lý | Endpoint chuyển tiếp tới Target Server |
|---|---|---|---|---|
| 1 | `/api/v1/session` | POST | Phiên đăng nhập & user info | `{TARGET_SERVER}/api/soc/session` |
| 2 | `/api/v1/config/system` | POST | Cấu hình Brand, Site, Display, Palette, Thresholds, Enums | `{TARGET_SERVER}/api/soc/config/system` |
| 3 | `/api/v1/config/cameras` | POST | Danh mục và thông số phần cứng camera (IP, PTZ, codec, WebRTC) | `{TARGET_SERVER}/api/devices/cameras/config` |
| 4 | `/api/v1/live/meta` | POST | Sequence, stream mode, timestamp tạo gói | `{TARGET_SERVER}/api/soc/live/meta` |
| 5 | `/api/v1/live/system` | POST | Trạng thái engine, threat DB version, unread badges | `{TARGET_SERVER}/api/soc/live/system` |
| 6 | `/api/v1/live/threat-overview` | POST | Dynamic threat score (0-100) & thống kê severity | `{TARGET_SERVER}/api/soc/threat-overview` |
| 7 | `/api/v1/live/kpi` | POST | Stream latency (ms) & danh sách camera offline | `{TARGET_SERVER}/api/soc/kpi` |
| 8 | `/api/v1/live/infrastructure` | POST | Dung lượng NVR storage & phụ tải PoE switch | `{TARGET_SERVER}/api/soc/infrastructure` |
| 9 | `/api/v1/live/camera-matrix` | POST | Video wall layout, telemetry, AI bounding boxes | `{TARGET_SERVER}/api/devices/cameras/matrix` |
| 10 | `/api/v1/live/incidents` | POST | Recent threats, snapshots, video playback URLs | `{TARGET_SERVER}/api/incidents/recent` |
| 11 | `/api/v1/ingest/full` | POST | Toàn bộ payload JSON gốc (session, config, live) | `{TARGET_SERVER}/api/soc/full-sync` |
| - | `/api/v1/health` | GET | Kiểm tra sức khỏe gateway & số lượng bản ghi DLQ | *(Không chuyển tiếp)* |

---

## 3. Cài đặt & Khởi động

### 3.1. Cài đặt thư viện
```bash
pip install -r requirements.txt
```

### 3.2. Cấu hình biến môi trường (Tùy chọn)
```bash
export GATEWAY_HOST="0.0.0.0"
export GATEWAY_PORT=5000
export TARGET_SERVER_BASE_URL="http://127.0.0.1:5001"
export TARGET_SERVER_TIMEOUT_MS=3000
export TARGET_SERVER_MAX_RETRIES=3
export DLQ_STORAGE_PATH="./data/dlq"
```

### 3.3. Khởi chạy Gateway
```bash
python3 run.py
```

---

## 4. Kiểm thử Tự động (Automated Verification)

Chạy bộ kiểm thử tự động (16 test cases kiểm tra toàn diện cả 11 routes, schema validation, HITL safeguard, và cơ chế fallback DLQ khi target server offline):

```bash
python3 -m pytest "tests/test_ingestion.py" -v
```

---

## 5. Ví dụ Gọi API (cURL)

### 5.1. Đẩy thông tin Dynamic Threat Overview (`POST /api/v1/live/threat-overview`)
```bash
curl -X POST http://127.0.0.1:5000/api/v1/live/threat-overview \
  -H "Content-Type: application/json" \
  -d '{
    "threat_score": 68,
    "open_threats": {
      "by_severity": { "CRITICAL": 1, "HIGH": 1, "MEDIUM": 2, "LOW": 0 }
    }
  }'
```

Phản hồi từ Gateway:
```json
{
  "correlation_id": "REQ-7c189b-001",
  "forward_status": "FORWARDED",
  "route": "/api/v1/live/threat-overview",
  "success": true,
  "summary": {
    "open_threats": {
      "by_severity": {
        "CRITICAL": 1,
        "HIGH": 1,
        "LOW": 0,
        "MEDIUM": 2
      }
    },
    "threat_score": 68
  },
  "target_response": {
    "ack": true,
    "module": "threat_overview",
    "status": "SUCCESS"
  },
  "target_status_code": 200,
  "timestamp": "2026-11-07T07:40:00.000Z"
}
```

### 5.2. Đẩy toàn bộ payload tổng hợp (`POST /api/v1/ingest/full`)
```bash
curl -X POST http://127.0.0.1:5000/api/v1/ingest/full \
  -H "Content-Type: application/json" \
  -d @sample_input.json
```
