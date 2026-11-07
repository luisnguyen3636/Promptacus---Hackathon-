Checklist dưới đây chia đúng theo từng module trên thanh menu trái của giao diện **CYBERGUARD AI** và thiết kế sẵn trạng thái chờ `fetch` API / WebSocket từ Backend để bạn tick chọn theo tiến độ code:

---

### Cấu trúc JSON chuẩn (API Contract) để Front-end tạo sẵn State chờ Backend

Bạn có thể copy 3 mẫu cấu trúc dữ liệu (Data Models) này vào thư mục `services/` hoặc `types/` ở Front-end để code giao diện trước bằng dữ liệu giả lập (Mock Data), khi Backend làm xong chỉ cần thay URL vào hàm `fetch`:

**1. API Dashboard & Telemetry (`GET /api/soc/overview`)**

```json
{
  "threatLevel": "LOW",
  "threatScore": 12,
  "status": "SAFE",
  "metrics": {
    "latencyMs": 42,
    "downloadMbps": 9744.0,
    "uploadMbps": 4824.2,
    "activeNodes": 43,
    "camerasOnline": 40,
    "camerasTotal": 43,
    "packetLossPercent": 0.0,
    "openThreats": 4,
    "criticalThreats": 1
  }
}

```

**2. API Danh sách Camera & AI Stream (`GET /api/devices/cameras`)**

```json
[
  {
    "id": "cam_01",
    "name": "Server Room - Cam 01",
    "ip": "192.168.1.101",
    "status": "ONLINE",
    "streamUrl": "webrtc://server-ip:8554/cam_01",
    "ptzEnabled": true,
    "aiAlert": {
      "hasAlert": true,
      "type": "INTRUSION_DETECTED",
      "severity": "CRITICAL",
      "boxes": [{ "label": "Person", "x": 120, "y": 80, "w": 60, "h": 140 }]
    }
  }
]

```

**3. API Incident Feed & Recent Threats (`GET /api/incidents/recent`)**

```json
[
  {
    "id": "inc_901",
    "title": "Port Scan Detected",
    "sourceIp": "45.33.32.156",
    "category": "NETWORK",
    "severity": "MEDIUM",
    "timestamp": "16:07",
    "cameraSnapshotUrl": null,
    "playbackUrl": null
  },
  {
    "id": "inc_902",
    "title": "Unauthorized Access - Server Room",
    "sourceIp": "192.168.1.101",
    "category": "PHYSICAL_CAMERA",
    "severity": "HIGH",
    "timestamp": "16:12",
    "cameraSnapshotUrl": "/snapshots/inc_902.jpg",
    "playbackUrl": "/recordings/inc_902.mp4"
  }
]

```