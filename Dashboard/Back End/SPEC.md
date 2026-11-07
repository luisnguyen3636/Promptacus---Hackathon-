# ĐẶC TẢ KỸ THUẬT: BACKEND SOC CORE SERVICE
# CYBERGUARD AI · SOC v2.1
## Dịch vụ API Thời gian thực, Live Streaming, PTZ Engine & Operational HITL Dispatcher

---

> **Tài liệu căn cứ:** `AGENTS.md` (Tuân thủ CD-01 đến CD-05) & `Dashboard/Back End/standard.md`  
> **Module:** Back-end Core SOC Service  
> **Vị trí:** `Dashboard/Back End/SPEC.md`  
> **Trạng thái:** `[WAITING FOR SPEC APPROVAL]`

---

## 1. MỤC TIÊU & PHẠM VI
Cung cấp dịch vụ Backend thực thi thực sự (Real Operational Service) chạy trên cổng `8000`:
1. **REST APIs:** Cung cấp đầy đủ các endpoint theo đúng hợp đồng dữ liệu chuẩn tại `standard.md` (`/api/soc/overview`, `/api/devices/cameras`, `/api/incidents/recent`, `/api/incidents/:id/playback`, `/api/cameras/:id/ptz`, `/api/incidents/:id/verify`).
2. **Real-time Telemetry Engine:** Tự động mô phỏng và biến thiên số liệu lưu lượng video, độ trễ mạng, packet loss theo chuỗi thời gian thực tế.
3. **PTZ State Manager:** Quản lý tọa độ Zoom/Pan/Tilt của từng camera trong lưới Matrix 2x2.
4. **AI Bounding Box Generator:** Tạo tọa độ bám vết đối tượng thời gian thực qua kênh WebSocket `/ws/live-stream`.
5. **Operational HITL Dispatcher:** Nhận quyết định xác thực từ Vận hành viên, đóng gói hồ sơ sự cố đầy đủ và ghi log kiểm toán không thể đảo ngược (tuân thủ nguyên tắc `[CD-04]`).

---

## 2. KIẾN TRÚC TỆP TIN BACKEND

```
Dashboard/Back End/
├── standard.md               # API Contract mẫu chuẩn
├── SPEC.md                   # Bản Đặc tả Kỹ thuật Backend (File này)
├── package.json              # Khai báo phụ thuộc Node.js (express, cors, ws)
├── server.js                 # Server chính chạy trên cổng 8000
└── src/
    ├── telemetryEngine.js    # Mô phỏng tính toán chỉ số mạng & KPI
    ├── cameraManager.js      # Quản lý 4 Camera & điều khiển PTZ
    ├── incidentManager.js    # Quản lý sự cố & Rolling Buffer
    └── hitlDispatcher.js     # Đóng gói hồ sơ & Ghi audit log
```

---

[WAITING FOR SPEC APPROVAL]
