# KẾ HOẠCH TRIỂN KHAI (STAGE 2 — IMPLEMENTATION PLAN)
**Mã kế hoạch:** `PLAN-DEEPSEEK-INCIDENT-PIPELINE-01`  
**Dự án:** Urban Safety AI-SOC (CyberGuard AI)

---

### 1. Danh Sách Các File Cần Tạo Mới & Sửa Đổi

| File | Hành động | Mục đích |
|---|---|---|
| `CloudflareWorker/src/deepseek_analyzer.ts` | **Tạo mới** | Bộ đệm log POST request, bộ gom nhóm cửa sổ 2 phút, tích hợp DeepSeek AI (`@cf/deepseek-ai/deepseek-v4.1-flash-1017`) phân tích logs và ảnh |
| `CloudflareWorker/src/types.ts` | **Sửa đổi** | Khai báo interface `IPostRequestLog`, `IDeepSeekIncidentResponse`, `IIncidentTimeline` |
| `CloudflareWorker/src/index.ts` | **Sửa đổi** | Lưu log mọi POST request, triển khai endpoint `GET /api/get-incident` và trigger phân tích DeepSeek |
| `Dashboard/Front End/src/components/AiMetricsGrid/AiMetricsGrid.tsx` | **Tạo mới** | Component hiển thị 8 thẻ AI & Phân bố đối tượng theo đúng bản hình đính kèm |
| `Dashboard/Front End/src/components/views/DashboardView.tsx` | **Sửa đổi** | Xóa component `TrafficCharts`, nhúng `AiMetricsGrid` vào vị trí trung tâm |
| `Dashboard/Front End/src/components/Sidebar.tsx` | **Sửa đổi** | Xóa mục 'Network Topology' khỏi danh sách thao tác |
| `Dashboard/Front End/src/App.tsx` | **Sửa đổi** | Gỡ bỏ routing 'Network Topology' |
| `Dashboard/Front End/src/hooks/useSocTelemetry.ts` | **Sửa đổi** | Bổ sung polling liên tục endpoint `/api/get-incident` để cập nhật bảng sự cố |
| `CloudflareWorker/test_deepseek_pipeline.mjs` | **Tạo mới** | Test script kiểm thử tự động toàn diện pipeline DeepSeek & endpoint `/api/get-incident` |
| `AGENTS.md`, `README.md`, `PROJECT_STRUCTURE.md` | **Đồng bộ** | Cập nhật đồng bộ bộ ba tài liệu dự án theo quy tắc bắt buộc `[CD-06]` |

---

### 2. Kịch Bản Kiểm Thử & Nghiệm Thu
1. **Kiểm thử Lưu Log POST Request:** Gửi các request POST tới `/api/v1/ai/detection` và `/api/incidents`, xác nhận log được lưu với đầy đủ timestamp, IP và hình ảnh.
2. **Kiểm thử Phân Tích DeepSeek 2 Phút:** Gọi bộ phân tích DeepSeek, xác minh output có `severity`, `evidence_timeline`, `object_description`, và phân tích DeepSeek.
3. **Kiểm thử Endpoint `GET /api/get-incident`:** Gọi endpoint và xác nhận JSON hợp lệ, có đầy đủ các trường yêu cầu.
4. **Kiểm thử Giao Diện Frontend:** Xác minh 'SOC Dashboard' hiển thị 8 thẻ AI mới, không còn biểu đồ traffic, không còn tab 'Network Topology'.
5. **Kiểm tra Toàn vẹn Bản Build:** Chạy `pnpm run build` hoàn tất 100% không lỗi.
