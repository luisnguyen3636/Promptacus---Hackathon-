# KẾ HOẠCH TRIỂN KHAI: ĐƯỜNG ỐNG CLOUDFLARE KV LƯU TRỮ INPUT & OUTPUT DEEPSEEK VÀ ĐỒNG BỘ DASHBOARD
**Mã tài liệu:** `PLAN-KV-INCIDENT-PIPELINE-01`  
**Dựa trên:** [SPEC_KV_INCIDENT_PIPELINE.md](file:///c:/Users/admin/OneDrive/Tài%20liệu/SGU/Hackathon/Promptacus---Hackathon-/CloudflareWorker/SPEC_KV_INCIDENT_PIPELINE.md)  
**Trạng thái:** Chờ phê duyệt (Stage 2 — Implementation Plan)

---

## 1. DANH SÁCH TỆP THỰC THI (FILE MANIFEST)

| Tác vụ | Tệp | Mô tả trách nhiệm |
|---|---|---|
| **Sửa đổi** | `CloudflareWorker/src/types.ts` | Thêm kiểu dữ liệu `IDeepSeekDebugTrace` chứa cấu trúc `input` và `output` phục vụ debug nhanh; bổ sung trường `debug_trace?: IDeepSeekDebugTrace` vào `IDeepSeekIncidentItem`. |
| **Sửa đổi** | `CloudflareWorker/src/deepseek_analyzer.ts` | Bổ sung hàm thao tác an toàn với Cloudflare KV (`writeToKv`, `readFromKv`), ghi nhận song song cả **Input** (`deepseek:input:<id>`) và **Output** (`deepseek:output:<id>`), lưu vết tổng hợp `deepseek:trace:<id>`, cập nhật `kv_recent_incidents` và ưu tiên đọc từ KV khi phục vụ Dashboard. |
| **Sửa đổi** | `CloudflareWorker/src/index.ts` | Ghi nhận log incident thô vào KV khi nhận POST, kích hoạt phân tích DeepSeek lưu Input/Output vào KV, phát WebSocket broadcast tới Dashboard và bổ sung endpoint debug tức thì `GET /api/kv/trace/:id`. |
| **Tạo mới** | `CloudflareWorker/test_kv_pipeline.mjs` | Bộ kịch bản kiểm thử tự động kiểm chứng việc lưu trữ KV (cả Input & Output), cơ chế fallback, endpoint trace và dữ liệu trả về cho Dashboard. |

---

## 2. THIẾT KẾ SCHEMA LƯU TRỮ INPUT VÀ OUTPUT TRONG KV

### 2.1. Cấu trúc Debug Trace (`IDeepSeekDebugTrace`):
```typescript
export interface IDeepSeekDebugTrace {
  event_id: string;
  timestamp: string;
  input: {
    prompt: string;
    raw_payload: Record<string, any>;
    model_target: string;
    timestamp: string;
  };
  output: {
    raw_response?: string;
    parsed_json?: any;
    model_used: string;
    latency_ms: number;
    timestamp: string;
  };
  status: "SUCCESS" | "FALLBACK" | "FAILED";
  error?: string | null;
}
```

### 2.2. Danh Sách Khóa KV Sẽ Được Tạo Tự Động:
1. `raw_incident:<event_id>`: Payload gốc gửi từ edge camera.
2. `deepseek:input:<event_id>`: Prompt văn bản, thông số khớp xương và payload gửi vào DeepSeek.
3. `deepseek:output:<event_id>`: Raw response text và JSON đã parse từ DeepSeek kèm thời gian phản hồi (latency).
4. `deepseek:trace:<event_id>`: Bản ghi hợp nhất cả Input và Output để debug trong 1 click.
5. `analyzed_incident:<event_id>`: Bản ghi sự cố hoàn chỉnh đã qua phân tích.
6. `kv_recent_incidents`: Mảng JSON danh sách sự cố gần nhất để Dashboard fetch với độ trễ `< 15ms`.

---

## 3. CÁC HÀM SẼ TRIỂN KHAI

### Trong `CloudflareWorker/src/deepseek_analyzer.ts`:
```typescript
// 1. Thao tác ghi/đọc KV an toàn với cơ chế fallback bộ nhớ
export async function writeToKv(env: Env, key: string, value: any, ttlSeconds?: number): Promise<boolean>;
export async function readFromKv<T>(env: Env, key: string): Promise<T | null>;

// 2. Lấy chi tiết Debug Trace (Input + Output) của một sự cố
export async function getDeepSeekTrace(env: Env, eventId: string): Promise<IDeepSeekDebugTrace | null>;

// 3. Tích hợp ghi Input & Output vào analyzeSingleLogWithIntegratedAI
// Lưu deepseek:input:<id> trước khi gọi model, lưu deepseek:output:<id> sau khi hoàn thành
```

### Trong `CloudflareWorker/src/index.ts`:
- Endpoint Debug nhanh: `GET /api/kv/trace/:id` (hoặc `GET /api/v1/debug/trace/:id`):
  Trả về JSON chứa toàn bộ `input` và `output` DeepSeek của sự cố để lập trình viên/vận hành viên kiểm tra tức thì.

---

## 4. KỊCH BẢN KIỂM THỬ (VERIFICATION PLAN)

1. **Chạy bài kiểm thử tự động:**
   `node --experimental-strip-types CloudflareWorker/test_kv_pipeline.mjs`
   - Xác thực `writeToKv` và `readFromKv` hoạt động chính xác.
   - Xác thực Input prompt và raw payload được ghi vào KV.
   - Xác thực Output JSON và latency được ghi vào KV.
   - Xác thực `deepseek:trace:<id>` hợp nhất cả Input và Output.
   - Xác thực Dashboard đọc `kv_recent_incidents` từ KV thành công.
   - Xác thực trạng thái `operator_status === "AWAITING_OPERATOR_VERIFICATION"` ([CD-04]).
2. **Kiểm tra biên dịch toàn hệ thống:**
   - Chạy `pnpm run build` đảm bảo `vite build` và `npx tsc --noEmit` đạt 100% exit code 0.
3. **Đồng bộ bộ ba tài liệu:**
   - Cập nhật `AGENTS.md`, `README.md` và `PROJECT_STRUCTURE.md` ([CD-06]).

---

**[WAITING FOR PLAN APPROVAL]**
