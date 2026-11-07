# KẾ HOẠCH TRIỂN KHAI: TÍCH HỢP CLOUDFLARE WORKER AI & KHO LƯU TRỮ SỰ CỐ
**Mã tài liệu:** `PLAN-CLOUDFLARE-WORKER-AI-01`  
**Dự án:** Hệ thống Giám sát An ninh & An toàn Đô thị Thông minh (Urban Safety AI-SOC)  
**Phân hệ:** Tầng 2 & Tầng 4 (Cloud Edge AI Analytics & Cloudflare D1 Vault)  
**Căn cứ kỹ thuật:** Tuân thủ `AGENTS.md` (Stage 2 SDD) và `SPEC-CLOUDFLARE-WORKER-AI-01`.

---

## 1. DANH MỤC TỆP TIN TRIỂN KHAI (FILE MANIFEST)

| Thao tác | Đường dẫn tệp | Trách nhiệm chính / Nội dung thực hiện |
| :--- | :--- | :--- |
| **Tạo mới** | `CloudflareWorker/wrangler.toml` | Cấu hình Cloudflare Worker Paid: bindings cho Workers AI (`env.AI`), D1 Database (`env.DB`), KV Cache. |
| **Tạo mới** | `CloudflareWorker/package.json` | Khai báo dependencies cho Cloudflare Worker (TypeScript, `@cloudflare/workers-types`). |
| **Tạo mới** | `CloudflareWorker/tsconfig.json` | Cấu hình TypeScript compiler cho Cloudflare Worker Edge Runtime. |
| **Tạo mới** | `CloudflareWorker/schema.sql` | Mã SQL DDL khởi tạo bảng `incidents` và `audit_logs` trên Cloudflare D1. |
| **Tạo mới** | `CloudflareWorker/src/types.ts` | Định nghĩa TypeScript Interfaces: Payload đầu vào, kết quả AI thang điểm 10, False Positive, Hung khí, Nạn nhân, HITL Record. |
| **Tạo mới** | `CloudflareWorker/src/ai_evaluator.ts` | Module gọi Cloudflare Workers AI (`@cf/meta/llama-3.3-70b-instruct-fp8-fast` hoặc `@cf/meta/llama-3.1-8b-instruct`), ép khuôn JSON nghiêm ngặt. |
| **Tạo mới** | `CloudflareWorker/src/db.ts` | Module thao tác với Cloudflare D1 SQL: chèn sự cố, truy vấn danh sách lọc theo camera/status, cập nhật trạng thái HITL Operator. |
| **Tạo mới** | `CloudflareWorker/src/index.ts` | Entrypoint router của Worker xử lý các route `/api/v1/engine/evaluate`, `/api/v1/incidents`, `/api/v1/incidents/:id/verify`. |
| **Tạo mới** | `Engine/cloudflare_client.py` | Python Client kết nối Engine cục bộ với Cloudflare Worker, tích hợp bộ lọc chống tràn và hàng đợi ngoại tuyến. |
| **Tạo mới** | `test_cloudflare_worker_integration.py` | Kịch bản kiểm thử tự động toàn diện kiểm chứng toàn bộ luồng tích hợp, thẩm định thang 10, false positive, và chốt chặn HITL. |

---

## 2. KỊCH BẢN KIỂM THỬ XÁC MINH (VERIFICATION & TEST PLAN)

1. **Test 1: Schema & Data Contract Validation:** Kiểm chứng cấu trúc payload từ Python Client khớp 100% với TypeScript interface của Cloudflare Worker.
2. **Test 2: Workers AI Evaluation Logic:** Kiểm thử hàm trích xuất AI trả về đúng điểm Severity trên thang 10, đo xác suất False Positive, trích xuất đặc điểm đối tượng, hung khí và nạn nhân.
3. **Test 3: Cloudflare D1 Vault Persistence:** Kiểm chứng chèn và truy vấn hồ sơ sự cố từ bảng `incidents` với đầy đủ metadata mở rộng.
4. **Test 4: Operational HITL Verification Gate:** Kiểm chứng sự cố khởi tạo với trạng thái `AWAITING_OPERATOR_VERIFICATION`, chỉ được chuyển sang `OPERATOR_CONFIRMED` khi có lệnh duyệt từ Operator.
5. **Test 5: Python Client Offline Queue & Retry:** Giả lập lỗi mạng, kiểm chứng sự cố được lưu an toàn vào `output/offline_incidents.jsonl` và tự động gửi lại khi có mạng.
