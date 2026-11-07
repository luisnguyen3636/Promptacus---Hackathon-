# ĐẶC TẢ KỸ THUẬT: DEEPSEEK 2-MINUTE INCIDENT ANALYSIS PIPELINE & UI REFINEMENT
**Mã tài liệu:** `SPEC-DEEPSEEK-INCIDENT-PIPELINE-01`  
**Dự án:** Urban Safety AI-SOC (CyberGuard AI)  
**Phương pháp:** Spec-Driven Development (SDD) & Strict HITL

---

## 1. YÊU CẦU NGHIỆP VỤ & PHẠM VI

### 1.1. Backend Pipeline
1. **Lưu vết mọi POST Request:** Mọi request POST gửi đến hệ thống (như `/api/v1/ai/detection`, `/api/incidents`, `/api/cameras/:id/ptz`, `/api/v1/engine/evaluate`) được ghi nhận chi tiết vào bộ nhớ đệm log (`postRequestLogs`) và D1 `audit_logs`.
2. **Tổng hợp theo cửa sổ 2 phút & Gọi DeepSeek:**
   - Hệ thống duy trì cửa sổ trượt 2 phút (120 giây).
   - Gọi mô hình AI mặc định `@cf/deepseek-ai/deepseek-v4.1-flash-1017` qua `env.AI` để phân tích ngữ cảnh sự cố từ logs và hình ảnh (Base64 JPEG).
   - Trích xuất: `severity` (CRITICAL, HIGH, MEDIUM, LOW), `evidence_timeline`, `object_description` (dáng vẻ, vũ khí, hành vi), `deepseek_reasoning`.
3. **Lưu trữ D1 & Endpoint `/api/get-incident`:**
   - Dữ liệu sự cố phân tích được ghi vào bảng `incidents` của Cloudflare D1.
   - Cung cấp endpoint `GET /api/get-incident` sinh JSON chuẩn cho frontend polling liên tục.

### 1.2. Frontend UI Refinement
1. **Tab 'SOC Dashboard' (`DashboardView.tsx`):**
   - Xóa bỏ 2 biểu đồ lưu lượng 'Ingress Video Traffic' và 'Egress Traffic' (`TrafficCharts.tsx`).
   - Thay thế bằng cụm thẻ Thống kê Hiệu năng AI & Phân bố Đối tượng (8 thẻ theo bản hình đính kèm `media_1794056279016_65657f42.png`):
     - Hàng 1: Inference Time, GPU Cluster Load, Accuracy, Active Threads.
     - Hàng 2: Class Person, Class Vehicle, Class Loitering, Class Intrusion / Breach.
2. **Xóa tab 'Network Topology':**
   - Loại bỏ khỏi `Sidebar.tsx` và `App.tsx`.
3. **Đồng bộ Incident:**
   - `useSocTelemetry.ts` định kỳ fetch `/api/get-incident` để cập nhật bảng sự cố thời gian thực.
