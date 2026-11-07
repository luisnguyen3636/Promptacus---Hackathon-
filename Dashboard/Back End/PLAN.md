# KẾ HOẠCH TRIỂN KHAI: BACKEND SOC CORE SERVICE
# CYBERGUARD AI · SOC v2.1

---

> **Tài liệu căn cứ:** `AGENTS.md` & `Dashboard/Back End/SPEC.md`  
> **Module:** Back-end Core SOC Service  
> **Giai đoạn:** `STAGE 2 — IMPLEMENTATION PLAN`  
> **Trạng thái:** `[WAITING FOR PLAN APPROVAL]`

---

## 1. CÁC MODULE TRIỂN KHAI TUẦN TỰ
1. `package.json`: Khởi tạo môi trường Node.js ESM.
2. `src/telemetryEngine.js`: Tính toán chỉ số telemetry động (độ trễ, băng thông, điểm đe dọa).
3. `src/cameraManager.js`: Quản lý 4 camera, trạng thái quang học PTZ và sinh tọa độ bám vết AI động.
4. `src/incidentManager.js`: Quản lý kho sự cố và Rolling Buffer bằng chứng video/keyframe.
5. `src/hitlDispatcher.js`: Xử lý chốt chặn phê duyệt của Vận hành viên, đóng gói hồ sơ sự cố và lưu log kiểm toán.
6. `server.js`: Khởi chạy máy chủ Express + WebSocket trên cổng 8000.

---

[WAITING FOR PLAN APPROVAL]
