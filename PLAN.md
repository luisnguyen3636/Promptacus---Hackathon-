# KẾ HOẠCH TRIỂN KHAI CHI TIẾT (IMPLEMENTATION PLAN v3.0)
## Hệ thống Giám sát An ninh & An toàn Đô thị Thông minh (Urban Safety AI-SOC)
**Tài liệu tham chiếu:** `SPEC.md` v3.0, `AGENTS.md` (SDD & HITL Framework, Auto-Approve Mode)  
**Trạng thái:** [PLAN AUTO-APPROVED] (Tự động phê duyệt theo CD-01, CD-02 & CD-04)  
**Mục tiêu cốt lõi:** Làm sạch code, đảm bảo TOÀN BỘ HỆ THỐNG VẪN HOẠT ĐỘNG HOÀN HẢO, tích hợp MMAction2, bắt buộc qua lớp VLM NVIDIA, debug logging toàn diện, bộ 10 rule tội phạm, chuyển đổi dashboard (Xóa Topology, Xóa AI Analyzer, Thêm Danh Sách Truy Nã CRUD & Evidence Stamping, Chuyển Device Manager thành Camera Manager, Tối ưu layout thu nhỏ Camera / phóng to Alert, gán Threat Score cho từng camera, và Panel Suy Luận Vùng Mù Đa Camera).

---

### BẢNG THEO DÕI CÁC TÁC VỤ (ATOMIC TASK BREAKDOWN)

| Task ID | Mô Tả Tác Vụ | File Ảnh Hưởng | Trạng Thái |
|---------|--------------|----------------|------------|
| **TSK-01** | Bổ sung module Debug Logging toàn diện cho Python AI SOC | `AI/Human/src/urbansoc/telemetry/debug_logger.py` | SẴN SÀNG |
| **TSK-02** | Xây dựng Module MMAction2 thay thế hoàn toàn cơ chế detect người và hành động | `AI/Human/src/urbansoc/mmaction2/detector.py`, `recognizer.py`, `__init__.py` | SẴN SÀNG |
| **TSK-03** | Viết bộ Rule Nhận Diện 10 Hành Vi Tội Phạm Phổ Biến chuẩn điều tra hình sự | `AI/Human/src/urbansoc/behavior/criminal_rules.py`, `Rule/criminal_rules.py` | SẴN SÀNG |
| **TSK-04** | Nâng cấp NVIDIA VLM thành LỚP BẮT BUỘC cho mọi luồng và khung hình | `AI/Human/src/urbansoc/server/inference_server.py`, `ai_service.py` | SẴN SÀNG |
| **TSK-05** | Nâng cấp Suy Luận Vùng Mù Đa Camera (>=2 Camera, Re-ID & Linkage) | `AI/Human/src/urbansoc/topology/blind_spot_reasoner.py`, `cross_camera_reid.py` | SẴN SÀNG |
| **TSK-06** | Xây dựng Debug Logger & Module Quản lý Danh Sách Truy Nã Backend (CRUD & Evidence Stamping) | `Dashboard/Back End/src/debugLogger.js`, `wantedManager.js` | SẴN SÀNG |
| **TSK-07** | Cập nhật Backend Gán Threat Score cho từng Camera & Xóa bỏ Endpoint Topology | `Dashboard/Back End/src/cameraManager.js`, `telemetryEngine.js`, `server.js` | SẴN SÀNG |
| **TSK-08** | Cập nhật Type Definitions & Mock Data Front End chuẩn hóa logic mới | `Dashboard/Front End/src/types/soc.ts`, `data/mockData.ts` | SẴN SÀNG |
| **TSK-09** | Xóa Network Topology & Xóa AI Analyzer trong SOC Dashboard Front End | `Dashboard/Front End/src/components/Sidebar.tsx`, `App.tsx` | SẴN SÀNG |
| **TSK-10** | Xây dựng Giao diện "Danh Sách Truy Nã" (Thêm, Sửa, Xóa & Đóng Dấu Bằng Chứng) | `Dashboard/Front End/src/components/views/WantedCriminalsView.tsx` | SẴN SÀNG |
| **TSK-11** | Chuyển đổi Device Manager thành Camera Manager (Kiểm tra camera & Threat Score per-cam) | `Dashboard/Front End/src/components/views/CameraManagerView.tsx` | SẴN SÀNG |
| **TSK-12** | Xây dựng Panel "Suy Luận Vùng Mù Đa Camera" (Truy vết >= 2 Camera từ ảnh đầu vào) | `Dashboard/Front End/src/components/views/BlindSpotTrackingView.tsx` | SẴN SÀNG |
| **TSK-13** | Tối ưu Bố cục Dashboard: Thu nhỏ Camera Matrix, Phóng to Newest Alert & Gán Threat Score Camera | `Dashboard/Front End/src/components/views/DashboardView.tsx`, `CameraSlot.tsx`, `NewestAlertModule.tsx` | SẴN SÀNG |
| **TSK-14** | Hiệu chỉnh thông số KPI & Telemetry khớp hoàn hảo với logic tác chiến thực tế | `Dashboard/Front End/src/components/KpiCards.tsx`, `useSocTelemetry.ts` | SẴN SÀNG |
| **TSK-15** | Biên dịch Frontend (Vite build) & Kiểm thử tích hợp toàn diện (>= 30 test cases) | `npm run build`, `test_backend_suite.py`, `pytest` | SẴN SÀNG |

---

### TIÊU CHÍ HOÀN THÀNH (ACCEPTANCE CRITERIA)
1. Frontend build thành công 100% không có lỗi TypeScript hay Vite bundler.
2. Backend khởi động và phục vụ đầy đủ API cho Wanted Criminals, Camera Manager, Blind Spot Reasoning, Newest Alert, Camera Stream.
3. Toàn bộ tests (tối thiểu 30 test cases) vượt qua kiểm thử thành công (PASSED).
4. Khởi chạy `./start_all.sh` mượt mà, không gặp lỗi runtime.

`[PLAN AUTO-APPROVED]`
