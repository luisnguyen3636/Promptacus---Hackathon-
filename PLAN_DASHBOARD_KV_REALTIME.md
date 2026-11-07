# PLAN_DASHBOARD_KV_REALTIME.md — KẾ HOẠCH TRIỂN KHAI: ĐỒNG BỘ REALTIME TOÀN BỘ DASHBOARD VỚI CLOUDFLARE KV & CHUẨN HÓA SCHEMA DEEPSEEK OUTPUT

**Dự án:** Hệ thống Giám sát An ninh & An toàn Đô thị Thông minh (Urban Safety AI-SOC)  
**Tác giả:** AI Coding Agent & Human Architect  
**Giai đoạn:** STAGE 2 — IMPLEMENTATION PLAN  
**Trạng thái:** [WAITING FOR PLAN APPROVAL]  
**Tham chiếu Đặc tả:** [SPEC_DASHBOARD_KV_REALTIME.md](file:///c:/Users/admin/OneDrive/Tài%20liệu/SGU/Hackathon/Promptacus---Hackathon-/SPEC_DASHBOARD_KV_REALTIME.md)  
**Tuân thủ:** AGENTS.md (CD-01 đến CD-06, Strict SDD & Dual HITL)

---

## 1. MỤC TIÊU CÔNG VIỆC (TASK BREAKDOWN)

Chuyển đổi toàn diện hệ thống tiếp nhận và render dữ liệu trên Dashboard sang kiến trúc thời gian thực (Dual-channel Realtime: WebSocket + 1s KV Polling) và chuẩn hóa hiển thị dữ liệu theo đúng định dạng JSON output của DeepSeek lưu trong Cloudflare KV.

---

## 2. DANH SÁCH TỆP ẢNH HƯỞNG (FILE MUTATION MANIFEST)

| STT | Tệp tin | Thao tác | Mục đích |
| :--- | :--- | :--- | :--- |
| 1 | `Dashboard/Front End/src/types/soc.ts` | **SỬA ĐỔI** | Mở rộng kiểu dữ liệu `IIncidentItem`, thêm `IDeepSeekParsedJson`, `IDeepSeekObjectDescription`, `IStandardKvIncidentOutput`. |
| 2 | `Dashboard/Front End/src/hooks/useSocTelemetry.ts` | **SỬA ĐỔI** | Viết hàm trích xuất đa hình `mapKvIncidentItem`, giảm chu kỳ polling xuống 1000ms, xử lý tức thì sự kiện `NEW_INCIDENT` từ WebSocket. |
| 3 | `Dashboard/Front End/src/components/Modal/EvidencePlaybackModal.tsx` | **SỬA ĐỔI** | Hiển thị chi tiết động học (`kinematics_summary`), tư thế (`posture_details`), tên mô hình (`model_used`), độ trễ (`latency_ms`), phán quyết (`threat_verdict`). |
| 4 | `Dashboard/Front End/src/components/RecentThreats/ThreatRow.tsx` | **SỬA ĐỔI** | Hiển thị `primary_action`, `posture_details`, `severity`, `event_id`, nhãn thời gian từ cấu trúc `parsed_json`. |
| 5 | `Dashboard/Front End/src/components/views/IncidentFeedView.tsx` | **SỬA ĐỔI** | Render thông tin động học và phân tích VLM chi tiết trên danh sách sự cố đầy đủ. |
| 6 | `Dashboard/Front End/src/components/views/AiAnalyzerView.tsx` | **SỬA ĐỔI** | Kết nối Live VLM Reasoning Console với dữ liệu sự cố thời gian thực từ KV. |
| 7 | `CloudflareWorker/src/deepseek_analyzer.ts` | **SỬA ĐỔI** | Đảm bảo `getDeepSeekIncidentsResponse` đọc trực tiếp từ `kv_recent_incidents` trong KV, chuẩn hóa cấu trúc trả về tương thích 100% với JSON mẫu. |
| 8 | `CloudflareWorker/test_dashboard_kv_realtime.mjs` | **TẠO MỚI** | Script kiểm thử tự động xác minh luồng đọc/ghi KV và độ toàn vẹn của dữ liệu render. |

---

## 3. THIẾT KẾ CHI TIẾT CÁC HÀM VÀ CHỮ KÝ HÀM (DETAILED FUNCTION SIGNATURES)

### 3.1. `Dashboard/Front End/src/types/soc.ts`
Mở rộng interface `IIncidentItem`:
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

export interface IIncidentItem {
  id: string;
  eventId?: string;
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
  rawResponse?: string;
  status: 'PENDING_VERIFICATION' | 'OPERATOR_CONFIRMED' | 'DISMISSED';
  
  // Dữ liệu mở rộng từ parsed_json
  threatVerdict?: string;
  role?: string;
  postureDetails?: string;
  kinematicsSummary?: string;
  weaponDetected?: string | null;
  weaponConfidence?: number;
  keypointsCount?: number;
  modelUsed?: string;
  latencyMs?: number;
  parsedJson?: IDeepSeekParsedJson;
  fullImageBase64?: string | null;
}
```

### 3.2. `Dashboard/Front End/src/hooks/useSocTelemetry.ts`
Hàm ánh xạ dữ liệu đa năng:
```typescript
export function mapKvIncidentItem(item: any): IIncidentItem {
  const parsed = item.parsed_json || {};
  const objDesc = parsed.object_description || item.object_description || {};
  const eventId = item.event_id || item.id || `EVT_${Date.now()}`;
  
  const primaryAction = objDesc.primary_action || item.title || item.engine_behavior || 'Sự cố an ninh';
  const postureDetails = objDesc.posture_details || item.vlmAnalysis || 'Quan sát hành vi đối tượng';
  const kinematicsSummary = objDesc.kinematics_summary || 'Đã phân tích tư thế sinh học';
  const severity = parsed.severity || item.severity || 'MEDIUM';
  const investigationSummary = parsed.investigation_summary || item.raw_response || item.vlmAnalysis || item.deepseek_analysis?.investigation_summary;

  return {
    id: eventId,
    eventId: eventId,
    title: primaryAction,
    subTitle: item.location_name || item.camera_id || 'Laptop Client Zone',
    sourceIp: item.camera_id || item.sourceIp || '127.0.0.1',
    category: 'PHYSICAL_CAMERA',
    severity: severity,
    timestamp: item.timestamp || item.evidence_timeline?.event_trigger || 'Vừa xong',
    cameraId: item.camera_id || null,
    cameraSnapshots: {
      eventPeakSnapshotUrl: item.visual_evidence?.snapshot_url || item.snapshot_url || null,
      preEventSnapshotUrl: item.visual_evidence?.crop_url || item.crop_url || null,
    },
    playbackUrl: item.visual_evidence?.snapshot_url || item.snapshot_url || null,
    status: item.operator_status || 'PENDING_VERIFICATION',
    vlmAnalysis: investigationSummary,
    rawResponse: item.raw_response || investigationSummary,
    threatVerdict: parsed.threat_verdict || item.deepseek_analysis?.threat_verdict || 'OBSERVED_ACTIVITY',
    role: objDesc.role || 'bystander',
    postureDetails: postureDetails,
    kinematicsSummary: kinematicsSummary,
    weaponDetected: objDesc.weapon_detected || null,
    weaponConfidence: objDesc.weapon_confidence || 0,
    keypointsCount: objDesc.keypoints_count || 17,
    modelUsed: item.model_used || item.deepseek_analysis?.model || '@cf/deepseek-ai/deepseek-v4.1-flash-1017',
    latencyMs: item.latency_ms || 925,
    parsedJson: parsed,
    fullImageBase64: item.visual_evidence?.snapshot_url || null
  };
}
```

### 3.3. `CloudflareWorker/src/deepseek_analyzer.ts`
Cập nhật `getDeepSeekIncidentsResponse`:
```typescript
export async function getDeepSeekIncidentsResponse(
  env: Env,
  windowSeconds = 120
): Promise<IDeepSeekGetIncidentsResponse> {
  // 1. Đọc danh sách sự cố lưu sẵn từ Cloudflare KV
  const kvIncidents = (await readFromKv<any[]>(env, "kv_recent_incidents")) || [];

  // 2. Chạy quét sliding window
  const windowIncidents = await analyzeWindowWithDeepSeek(env, windowSeconds);

  // 3. Hợp nhất, loại bỏ trùng lặp theo ID/event_id
  const mergedMap = new Map<string, any>();
  for (const inc of kvIncidents) {
    const key = inc.event_id || inc.id;
    if (key) mergedMap.set(key, inc);
  }
  for (const inc of windowIncidents) {
    const key = inc.id || inc.event_id;
    if (key) mergedMap.set(key, inc);
  }

  // 4. Chuẩn hóa từng phần tử: đảm bảo có đầy đủ cả trường phẳng và parsed_json theo mẫu user
  const formattedList = Array.from(mergedMap.values()).map(formatToStandardUserOutput);

  return {
    success: true,
    count: formattedList.length,
    window_seconds: windowSeconds,
    timestamp: new Date().toISOString(),
    provider: activeProvider,
    model: activeModel,
    incidents: formattedList
  };
}
```

---

## 4. KỊCH BẢN KIỂM THỬ VÀ NGHIỆM THU (TEST & VERIFICATION PLAN)

### 4.1. Kịch bản 1: Kiểm thử Unit & Integration với Mock KV (`test_dashboard_kv_realtime.mjs`)
- **Bước 1:** Nạp bản ghi mẫu chuẩn của người dùng vào Mock KV:
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
- **Bước 2:** Gọi hàm `getDeepSeekIncidentsResponse` và kiểm tra:
  - Có trả về `count >= 1`.
  - Phần tử đầu tiên có `event_id === "EVT_20261107_213746_3e304691"`.
  - Khối `parsed_json` giữ nguyên 100% cấu trúc, `primary_action === "NORMAL"`, `latency_ms === 925`.
- **Bước 3:** Kiểm tra hàm ánh xạ frontend `mapKvIncidentItem`:
  - `title` nhận giá trị `"NORMAL"`.
  - `kinematicsSummary` nhận `"Góc khuỷu tay phải: N/A°, Độ duỗi tay: N/Am, Vận tốc cổ tay: N/Apx/s"`.
  - `status` mặc định là `"PENDING_VERIFICATION"`.

### 4.2. Kịch bản 2: Kiểm thử Biên dịch Frontend & Worker (`Build Integrity Check`)
- Chạy `pnpm run build` để kiểm tra TypeScript compilation sạch 100% không có lỗi type nào trong cả Frontend (`tsc -b`) và Cloudflare Worker.

### 4.3. Kịch bản 3: Đồng bộ Bộ Ba Tài liệu [CD-06]
- Cập nhật `AGENTS.md`, `README.md`, `PROJECT_STRUCTURE.md`.

---

**[STATUS: WAITING FOR PLAN APPROVAL]**  
*Vui lòng duyệt Kế hoạch Triển khai trên để Agent tiến hành viết code và kiểm chứng (STAGE 4 — CODE & VERIFY).*
