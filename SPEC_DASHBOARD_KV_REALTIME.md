# SPEC_DASHBOARD_KV_REALTIME.md — ĐẶC TẢ KỸ THUẬT: ĐỒNG BỘ REALTIME TOÀN BỘ DASHBOARD VỚI CLOUDFLARE KV & CHUẨN HÓA SCHEMA DEEPSEEK OUTPUT

**Dự án:** Hệ thống Giám sát An ninh & An toàn Đô thị Thông minh (Urban Safety AI-SOC)  
**Tác giả:** AI Coding Agent & Human Architect  
**Giai đoạn:** STAGE 1 — SPECIFICATION  
**Trạng thái:** [WAITING FOR SPEC APPROVAL]  
**Tuân thủ:** AGENTS.md (CD-01 đến CD-06, Strict SDD & Dual HITL)

---

## 1. BỐI CẢNH & MỤC TIÊU (CONTEXT & OBJECTIVES)

### 1.1. Bối cảnh
Người dùng yêu cầu:
1. Kiểm tra tính hoạt động đúng của toàn bộ Dashboard khi lấy dữ liệu từ Cloudflare KV (`INCIDENT_CACHE`).
2. Tiến hành kết nối thời gian thực (realtime) cho toàn bộ Dashboard.
3. Render giao diện chuẩn xác 100% theo mẫu JSON output đã cung cấp:
```json
{
  "event_id": "EVT_20261107_213746_3e304691",
  "raw_response": "[DeepSeek Forensic Engine] Hoạt động quan sát định kỳ tại Laptop Client Zone. Tiếp tục giám sát.",
  "parsed_json": {
    "severity": "MEDIUM",
    "threat_verdict": "OBSERVED_ACTIVITY",
    "investigation_summary": "[DeepSeek Forensic Engine] Hoạt động quan sát định kỳ tại Laptop Client Zone. Tiếp tục giám sát.",
    "object_description": {
      "primary_action": "NORMAL",
      "role": "bystander",
      "posture_details": "Detected action: NORMAL (threat score: 0.10)",
      "weapon_detected": null,
      "weapon_confidence": 0,
      "kinematics_summary": "Góc khuỷu tay phải: N/A°, Độ duỗi tay: N/Am, Vận tốc cổ tay: N/Apx/s",
      "keypoints_count": 17
    }
  },
  "model_used": "@cf/deepseek-ai/deepseek-v4.1-flash-1017",
  "latency_ms": 925,
  "timestamp": "2026-11-07T14:37:50.049Z"
}
```

### 1.2. Mục tiêu kỹ thuật
- **Chuẩn hóa Dữ liệu KV & Endpoint:** Mọi bản ghi incident lưu trong Cloudflare KV (`deepseek:output:<id>`, `kv_recent_incidents`, `analyzed_incident:<id>`) cũng như phản hồi từ `GET /api/get-incident` và `GET /api/get-incidents` đều mang đầy đủ cấu trúc trên (hỗ trợ cả các trường phẳng lẫn đối tượng lồng `parsed_json`).
- **Realtime Toàn diện (Zero-Lag Dashboard):**
  - Kênh 1: WebSocket (`/ws/live-stream`) phát ngay gói tin `NEW_INCIDENT` và `TELEMETRY_AND_AI_TICK` khi có sự kiện được phân tích và lưu vào KV.
  - Kênh 2: Tối ưu chu kỳ REST Polling từ 2000ms xuống 1000ms đối với `/api/get-incident` và `/api/soc/overview`, đọc trực tiếp bộ đệm `kv_recent_incidents` từ Cloudflare KV với độ trễ `< 15ms`.
- **Render Chi tiết trên Toàn bộ Dashboard:**
  - `RecentThreatsTable` & `ThreatRow`: Hiển thị chuẩn `primary_action`, `posture_details`, `severity`, thời gian `timestamp`, mã sự cố `event_id`.
  - `EvidencePlaybackModal`: Hiển thị đầy đủ `raw_response`, `kinematics_summary` (góc khuỷu tay, độ duỗi tay, vận tốc cổ tay), `threat_verdict`, `model_used`, `latency_ms` cùng bộ nút bấm xác thực HITL.
  - `IncidentFeedView`: Hiển thị chi tiết từng incident theo đúng schema JSON, phân loại theo `severity`, `status`, kèm công cụ lọc và tìm kiếm tức thì.
  - `AiAnalyzerView`: Console stream thời gian thực nhận trực tiếp log phân tích VLM từ KV, thể hiện độ trễ `latency_ms` và tên `model_used`.
  - `AiMetricsGrid`: Cập nhật số tracks, phân bố sự cố và hiệu năng AI trực tiếp theo luồng sự kiện từ KV.

---

## 2. DATA CONTRACT & SCHEMA CHUẨN HÓA

### 2.1. TypeScript Interface cho Incident chuẩn KV (Frontend & Backend đồng bộ)

```typescript
export interface IDeepSeekObjectDescription {
  primary_action: string;
  role: 'suspect' | 'victim' | 'bystander' | string;
  posture_details: string;
  weapon_detected: string | null;
  weapon_confidence: number;
  kinematics_summary: string;
  keypoints_count: number;
}

export interface IDeepSeekParsedJson {
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  threat_verdict: string;
  investigation_summary: string;
  object_description: IDeepSeekObjectDescription;
}

export interface IStandardKvIncidentOutput {
  event_id: string;
  raw_response: string;
  parsed_json: IDeepSeekParsedJson;
  model_used: string;
  latency_ms: number;
  timestamp: string;
  
  // Tương thích ngược với hệ thống SOC hiện hữu
  id?: string;
  camera_id?: string;
  location_name?: string;
  visual_evidence?: {
    snapshot_url?: string | null;
    crop_url?: string | null;
    sha256_hash?: string | null;
  };
  operator_status?: 'PENDING_VERIFICATION' | 'AWAITING_OPERATOR_VERIFICATION' | 'OPERATOR_CONFIRMED' | 'DISMISSED';
}
```

### 2.2. Frontend Model mở rộng (`types/soc.ts`)

```typescript
export interface IIncidentItem {
  id: string;
  title: string;
  subTitle?: string;
  sourceIp: string;
  category: IncidentCategory;
  severity: IncidentSeverity;
  timestamp: string;
  cameraId?: string | null;
  cameraSnapshots?: ICameraSnapshots | null;
  playbackUrl?: string | null;
  vlmAnalysis?: string;
  status: 'PENDING_VERIFICATION' | 'OPERATOR_CONFIRMED' | 'DISMISSED';
  
  // Các trường giàu thông tin trích xuất từ parsed_json
  eventId?: string;
  rawResponse?: string;
  threatVerdict?: string;
  role?: string;
  postureDetails?: string;
  kinematicsSummary?: string;
  weaponDetected?: string | null;
  weaponConfidence?: number;
  keypointsCount?: number;
  modelUsed?: string;
  latencyMs?: number;
  fullImageBase64?: string | null;
}
```

---

## 3. LUỒNG DỮ LIỆU THỜI GIAN THỰC (REALTIME KV PIPELINE)

```
[Camera Edge / AI Ingestion]
            │
            ▼ (POST /api/v1/ai/detection)
[Cloudflare Edge Worker]
            │
            ├─► In-Process AI Layer (analyzeSingleLogWithIntegratedAI)
            │      ├─ Tier 1: Direct DeepSeek API (với DEEPSEEK_API_KEY)
            │      ├─ Tier 2: Cloudflare Workers AI (@cf/deepseek-ai/...)
            │      └─ Tier 3: Local Kinematics Engine (Fallback)
            │
            ├─► Ghi vào Cloudflare KV (`INCIDENT_CACHE`):
            │      ├─ deepseek:input:<event_id>
            │      ├─ deepseek:output:<event_id>  (ĐÚNG FORMAT CHUẨN CỦA USER)
            │      ├─ deepseek:trace:<event_id>
            │      └─ kv_recent_incidents (Mảng cache 100 incident gần nhất)
            │
            ├─► Broadcast WebSocket (/ws/live-stream):
            │      └─ type: "NEW_INCIDENT" (Đẩy ngay lập tức incident đã phân tích)
            │
            ▼
[Dashboard Frontend (React 19)]
      ├─ Kênh 1: WebSocket onmessage (Nhận tức thời < 50ms)
      ├─ Kênh 2: Polling 1000ms (/api/get-incident -> đọc kv_recent_incidents từ KV < 15ms)
      ▼
[Toàn bộ 8 Màn hình Tác chiến SOC cập nhật đồng bộ]
```

---

## 4. BẢNG ĐỐI CHIẾU HIỂN THỊ TRÊN CÁC VIEW DASHBOARD

| View / Component | Dữ liệu từ Output mẫu của User | Cách Render trên Giao diện |
| :--- | :--- | :--- |
| **RecentThreatsTable** | `parsed_json.object_description.primary_action`, `parsed_json.severity`, `timestamp`, `event_id` | Render hàng sự cố với màu sắc severity (MEDIUM: Vàng, HIGH: Cam, CRITICAL: Đỏ), tiêu đề hành vi rõ ràng, nút `PLAYBACK`. |
| **EvidencePlaybackModal** | `raw_response`, `investigation_summary`, `kinematics_summary`, `posture_details`, `model_used`, `latency_ms` | Hiển thị chi tiết góc khuỷu tay, độ duỗi tay, vận tốc cổ tay, tóm tắt điều tra DeepSeek, model và thời gian phản hồi (ms), cùng 3 nút HITL. |
| **IncidentFeedView** | Toàn bộ object `parsed_json`, `threat_verdict`, `role`, `keypoints_count` | Thẻ sự cố mở rộng, hiển thị huy hiệu xác thực, bộ lọc thời gian thực theo mức độ và trạng thái. |
| **AiAnalyzerView** | `raw_response`, `model_used`, `latency_ms`, `timestamp` | Live VLM Console cập nhật từng dòng log phân tích từ KV kèm độ trễ và tên mô hình. |
| **AiMetricsGrid** | `severity`, `threat_score`, `keypoints_count` | Đếm tổng số tracks và tỷ lệ phân bố sự cố theo thời gian thực. |
| **ThreatScoreModule** | `parsed_json.severity` -> cập nhật Threat Score toàn hệ thống | Kim đồng hồ đe dọa (0 - 100) phản ánh mức độ nguy cơ đô thị. |

---

## 5. RÀNG BUỘC KIẾN TRÚC & CHỐT CHẶN HITL

1. **Bảo toàn Chốt chặn Operational HITL [CD-04]:**
   - Mọi bản ghi từ KV khi hiển thị trên giao diện đều có trạng thái khởi tạo là `PENDING_VERIFICATION` (hoặc `AWAITING_OPERATOR_VERIFICATION`).
   - Các hành động dispatch cơ quan chức năng chỉ kích hoạt khi Operator click `XÁC NHẬN & ĐIỀU PHỐI (DISPATCH)` trong `EvidencePlaybackModal`.
2. **Khả năng Chịu lỗi Cao (Fault-Tolerant Parsing):**
   - Bộ parser trong `useSocTelemetry.ts` hỗ trợ linh hoạt 3 kịch bản:
     - Kịch bản A: API trả về đối tượng đơn lẻ chứa `parsed_json`.
     - Kịch bản B: API trả về `{ incidents: [...] }` trong đó mỗi phần tử chứa `parsed_json`.
     - Kịch bản C: Dữ liệu fallback dạng phẳng truyền thống.
   - Không bao giờ gây crash giao diện nếu thiếu một trường con.

---

## 6. KỊCH BẢN KIỂM THỬ & KIỂM CHỨNG (VERIFICATION PLAN)

1. **Kiểm thử Đọc/Ghi KV:**
   - Viết kịch bản test nạp đúng mẫu JSON của người dùng vào KV (`kv_recent_incidents` và `deepseek:output:<id>`).
   - Gọi `GET /api/get-incident` và `GET /api/get-incidents` để kiểm chứng dữ liệu trả về giữ nguyên vẹn 100% cấu trúc `parsed_json`, `raw_response`, `model_used`, `latency_ms`.
2. **Kiểm thử Realtime:**
   - Kiểm tra kết nối WebSocket nhận message `NEW_INCIDENT`.
   - Kiểm tra chu kỳ polling 1000ms đọc dữ liệu tức thì từ KV cache.
3. **Kiểm thử Render Giao diện:**
   - Kiểm tra `RecentThreatsTable`, `EvidencePlaybackModal`, `IncidentFeedView`, `AiAnalyzerView` render chính xác các trường dữ liệu mới.
4. **Kiểm thử Bản Build (Clean Build):**
   - Chạy `pnpm run build` đảm bảo 0 lỗi TypeScript, 0 lỗi cảnh báo.

---

**[STATUS: WAITING FOR SPEC APPROVAL]**
*Vui lòng duyệt tài liệu Đặc tả Kỹ thuật trên để Agent chuyển sang Bước 2 (Lập Kế hoạch Triển khai - PLAN).*
