# KẾ HOẠCH TRIỂN KHAI: TÍCH HỢP TỰ ĐỘNG LỚP AI PHÂN TÍCH & DEEPSEEK API KEY
**Mã tài liệu:** `PLAN-INTEGRATED-AI-LAYER-01`  
**Dựa trên:** [SPEC_INTEGRATED_AI_LAYER.md](file:///c:/Users/admin/OneDrive/Tài%20liệu/SGU/Hackathon/Promptacus---Hackathon-/CloudflareWorker/SPEC_INTEGRATED_AI_LAYER.md)  
**Trạng thái:** Chờ phê duyệt (Stage 2 — Implementation Plan)

---

## 1. DANH SÁCH TỆP THỰC THI (FILE MANIFEST)

| Tác vụ | Tệp | Mô tả trách nhiệm |
|---|---|---|
| **Sửa đổi** | `CloudflareWorker/src/types.ts` | Thêm kiểu `IStandardSocLogEntry`, cập nhật `Env` (thêm `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL`, `DEEPSEEK_API_URL`), bổ sung `soc_audit_log` vào `IDeepSeekIncidentItem`. |
| **Sửa đổi** | `CloudflareWorker/src/deepseek_analyzer.ts` | Triển khai client gọi trực tiếp DeepSeek API (`callDeepSeekDirectApi`), hàm phân tích nội tại tự động (`analyzeSingleLogWithIntegratedAI`), bộ tạo log kiểm toán chuẩn SOC (`formatStandardSocLog`), và quản lý bộ nhớ đệm log chuẩn. |
| **Sửa đổi** | `CloudflareWorker/src/index.ts` | Kích hoạt tự động phân tích AI ngay khi nhận POST (`/api/v1/ai/detection` & `/api/incidents`), định tuyến cả 2 endpoint `GET /api/get-incident` và `GET /api/get-incidents` sinh JSON do AI phân tích. |
| **Sửa đổi** | `CloudflareWorker/wrangler.toml` | Khai báo biến môi trường mẫu `DEEPSEEK_API_KEY` và `DEEPSEEK_MODEL` để người dùng dễ dàng gắn API Key. |
| **Tạo mới** | `CloudflareWorker/test_integrated_ai_layer.mjs` | Kịch bản kiểm thử tự động toàn diện kiểm chứng Direct API Key, in-process auto AI trigger, chuẩn log SOC và endpoint JSON. |

---

## 2. CHỮ KÝ HÀM & CẤU TRÚC GIAO DIỆN (FUNCTION SIGNATURES)

### 2.1. Trong `CloudflareWorker/src/types.ts`:
```typescript
// Chuẩn hóa bản ghi log kiểm toán SOC
export interface IStandardSocLogEntry {
  log_id: string;
  timestamp: string;
  log_level: "INFO" | "WARNING" | "CRITICAL";
  source: "AI_INTEGRATED_LAYER";
  event_id: string;
  camera_id: string;
  model_provider: "DEEPSEEK_DIRECT_API" | "CLOUDFLARE_WORKERS_AI" | "LOCAL_KINEMATICS_ENGINE";
  model_name: string;
  latency_ms: number;
  threat_score: number;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  object_description: IIncidentObjectDescription;
  investigation_summary: string;
  evidence_timeline: IIncidentTimeline;
  sha256_hash: string | null;
  operator_status: "AWAITING_OPERATOR_VERIFICATION";
}
```

### 2.2. Trong `CloudflareWorker/src/deepseek_analyzer.ts`:
```typescript
// 1. Gọi trực tiếp DeepSeek REST API bằng API Key (JSON Mode)
export async function callDeepSeekDirectApi(
  prompt: string,
  apiKey: string,
  modelName?: string,
  apiUrl?: string
): Promise<{ success: boolean; data?: any; error?: string; latencyMs: number }>;

// 2. Phân tích tự động 1 bản ghi log ngay khi tiếp nhận (In-process AI Trigger)
export async function analyzeSingleLogWithIntegratedAI(
  log: IPostRequestLog,
  env: Env
): Promise<IDeepSeekIncidentItem>;

// 3. Chuẩn hóa bản ghi log kiểm toán SOC
export function formatStandardSocLog(
  item: IDeepSeekIncidentItem,
  provider: "DEEPSEEK_DIRECT_API" | "CLOUDFLARE_WORKERS_AI" | "LOCAL_KINEMATICS_ENGINE",
  modelName: string,
  latencyMs: number
): IStandardSocLogEntry;

// 4. Lấy danh sách log kiểm toán SOC chuẩn
export function getStandardSocAuditLogs(): IStandardSocLogEntry[];

// 5. Cung cấp dữ liệu JSON hoàn chỉnh cho GET /api/get-incidents & /api/get-incident
export async function getDeepSeekIncidentsResponse(
  env: Env,
  windowSeconds?: number
): Promise<IDeepSeekGetIncidentsResponse>;
```

---

## 3. THƯ VIỆN & PHỤ THUỘC (DEPENDENCIES)
- Sử dụng 100% native Web `fetch`, `JSON.parse` và `crypto.randomUUID()` có sẵn trong runtime của Cloudflare Workers và Node.js `>= 20`.
- **Không cài đặt thêm bất kỳ thư viện bên ngoài nào** nhằm giữ cho bundle siêu nhẹ, an toàn và tối ưu thời gian khởi động Cold Start.

---

## 4. KỊCH BẢN KIỂM THỬ & KIỂM CHỨNG (VERIFICATION PLAN)

Tạo tệp kiểm thử tự động `CloudflareWorker/test_integrated_ai_layer.mjs`:
1. **Test 1 — Direct DeepSeek API Client:**
   - Xác thực cấu trúc request gửi đi: URL `https://api.deepseek.com/chat/completions`, header `Authorization: Bearer <key>`, payload `response_format: { type: "json_object" }`.
   - Xác thực parse JSON an toàn khi AI trả về.
2. **Test 2 — In-Process Integrated AI Layer:**
   - Bơm một POST request mẫu vào `recordPostRequestLog`.
   - Gọi `analyzeSingleLogWithIntegratedAI` và xác minh rằng sự cố được phân tích tự động ngay trong code mà không cần gọi endpoint trigger thủ công.
3. **Test 3 — Chuẩn Hóa Nhật Ký Kiểm Toán SOC:**
   - Xác thực bản ghi log sinh ra tuân thủ đầy đủ schema `IStandardSocLogEntry`.
   - Kiểm tra các trường: `log_id`, `timestamp`, `log_level`, `model_provider`, `latency_ms`, `object_description`, `threat_score`.
4. **Test 4 — Định Tuyến Cả 2 Endpoint:**
   - Kiểm tra `GET /api/get-incidents` và `GET /api/get-incident`.
   - Xác thực JSON trả về có `success: true`, `provider`, `model`, và mảng `incidents` chứa dữ liệu phân tích từ AI.
5. **Test 5 — Chốt Chặn HITL [CD-04]:**
   - Đảm bảo toàn bộ sự cố sinh ra từ AI layer đều có `operator_status === "AWAITING_OPERATOR_VERIFICATION"`.
6. **Kiểm Tra Build Toàn Dự Án:**
   - Chạy `pnpm run build` để xác nhận `tsc --noEmit` và `vite build` compile sạch 100%.

---

**[WAITING FOR PLAN APPROVAL]**
