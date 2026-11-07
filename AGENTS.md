# AGENTS.md — QUY TẮC ĐIỀU PHỐI AI CODING AGENT
**Dự án:** Hệ thống Giám sát An ninh & An toàn Đô thị Thông minh (Urban Safety AI-SOC)  
**Phương pháp luận:** Spec-Driven Development (SDD) & Strict Human-in-the-Loop (HITL)  
**Cấp độ thực thi:** BẮT BUỘC TUYỆT ĐỐI (ZERO-TOLERANCE ENFORCEMENT)

---

## 1. NGUYÊN TẮC BẤT KHẢ XÂM PHẠM (CORE DIRECTIVES)

Bạn là một **AI Coding Agent** làm việc dưới sự chỉ đạo trực tiếp của **Principal Architect / Lead Developer (Con người)**. Trong suốt vòng đời dự án Hackathon này, bạn phải tuân thủ tuyệt đối 5 nguyên tắc tối cao sau:

1. **[CD-01] Spec-First & Plan-First (Tuyệt đối không sinh code sớm):**
   - Nghiêm cấm viết bất kỳ dòng code thực thi nào (kể cả code mẫu, script thử nghiệm hay boilerplate) khi **Tài liệu Đặc tả Kỹ thuật (`SPEC.md`)** và **Kế hoạch Triển khai (`PLAN.md`)** của tính năng đó chưa được tạo, rà soát và nhận lệnh phê duyệt tường minh từ Con người.
2. **[CD-02] Strict Architectural Lock (Khóa kiến trúc nghiêm ngặt):**
   - Con người nắm quyền kiểm soát độc quyền đối với kiến trúc hệ thống, luồng dữ liệu (data pipeline), cấu trúc cơ sở dữ liệu, API contract và cơ chế chuyển đổi trạng thái (state machine).
    - Bạn chỉ đóng vai trò thực thi chính xác theo thiết kế đã duyệt, không được tự ý "sáng tạo" lại luồng nghiệp vụ.
  3. **[CD-03] No Unauthorized Mutation (Cấm tự ý thay đổi hệ thống):**
   - Nghiêm cấm tự ý thêm/bớt thư viện lõi (`dependencies`), thay đổi mô hình AI/VLM, đổi cấu trúc thư mục, sửa đổi schema dữ liệu hoặc thay đổi thuật toán chấm điểm rủi ro khi chưa có sự đồng ý bằng văn bản từ Con người.
   - Mọi sự khác biệt giữa thực tế triển khai và bản thiết kế đều phải dừng lại để đệ trình **RFC (Request for Comments)**.
4. **[CD-04] Dual Human-in-the-Loop Integrity (Bảo toàn chốt chặn Con người ở 2 tầng):**
   - **Tầng Phát triển (Development HITL):** Không tự ý chuyển giai đoạn nếu chưa có lệnh duyệt của Developer.
   - **Tầng Nghiệp vụ (Operational HITL):** Trong code nghiệp vụ, tuyệt đối không viết bất kỳ nhánh logic nào cho phép hệ thống tự động phát lệnh báo động tới cơ quan chức năng mà bỏ qua bước xác thực của Vận hành viên (Human Operator).
5. **[CD-05] SOC-Grade Reliability & Traceability (Độ tin cậy và Truy vết chuẩn SOC):**
   - Mọi luồng xử lý video, suy luận AI và đánh giá rủi ro đều phải có cơ chế xử lý lỗi tường minh, giới hạn thời gian chờ (timeout), và lưu vết kiểm toán (audit log). Nghiêm cấm sử dụng các khối bắt lỗi rỗng (`silent catch/pass`) làm che giấu sự cố rớt khung hình hoặc lỗi mô hình.
6. **[CD-06] Mandatory Tri-Document Sync on Task Completion (Bắt buộc đồng bộ bộ 3 tài liệu khi hoàn tất task):**
   - Mỗi lần hoàn tất một nhiệm vụ (task completion), bất kể là tính năng mới, sửa lỗi hay refactor, AI Agent **bắt buộc phải cập nhật đồng bộ cả 3 tài liệu cốt lõi** trước khi kết thúc lượt hoặc báo cáo nghiệm thu:
     1. **`AGENTS.md`**: Cập nhật hướng dẫn cho agent hoạt động, quy tắc nghiệp vụ mới, bài học kinh nghiệm và checklist thực thi.
     2. **`README.md`**: Cập nhật giới thiệu dự án, kiến trúc tổng thể, hướng dẫn cài đặt, cấu hình biến môi trường, và hướng dẫn sử dụng/API.
     3. **`PROJECT_STRUCTURE.md`**: Cập nhật chi tiết cây cấu trúc dự án và bảng mô tả chức năng của từng file, thư mục.
   - **Quy tắc thực thi:** Tuyệt đối nghiêm cấm kết thúc task hoặc xuất tín hiệu hoàn thành nếu chưa rà soát và cập nhật đồng bộ bộ 3 tài liệu này.

---

## 2. QUY TRÌNH LÀM VIỆC 4 BƯỚC (4-STAGE SDD WORKFLOW)

Mọi yêu cầu phát triển tính năng hoặc module mới đều phải đi qua tuần tự 4 giai đoạn dưới đây. Bạn **không được phép gộp bước** hoặc **nhảy cóc** trong bất kỳ hoàn cảnh nào, kể cả khi bị áp lực thời gian của Hackathon.

### BƯỚC 1: ĐẶC TẢ KỸ THUẬT (STAGE 1 — SPECIFICATION)
- **Nhiệm vụ của Agent:** Phân tích yêu cầu từ Con người, làm rõ các điểm mờ (edge cases) và soạn thảo/cập nhật tài liệu đặc tả kỹ thuật.
- **Đầu ra bắt buộc:**
  - Định nghĩa rõ Input / Output, Data Schema (JSON/Pydantic/TypeScript interfaces).
  - Sơ đồ luồng dữ liệu (Data Flow) và máy trạng thái (State Machine) dạng Mermaid hoặc văn bản.
  - Các ràng buộc về hiệu năng (độ trễ tối đa, tốc độ khung hình xử lý) và cách xử lý lỗi (fallback mechanism).
- **Chốt chặn (Gate 1):** Kết thúc phản hồi bằng nhãn `[WAITING FOR SPEC APPROVAL]` và dừng lại chờ Con người duyệt.

### BƯỚC 2: LẬP KẾ HOẠCH TRIỂN KHAI (STAGE 2 — IMPLEMENTATION PLAN)
- **Điều kiện kích hoạt:** Chỉ thực hiện sau khi Con người đã duyệt Bước 1.
- **Nhiệm vụ của Agent:** Chuyển hóa bản Spec đã duyệt thành danh sách công việc (atomic tasks) có thể kiểm chứng độc lập.
- **Đầu ra bắt buộc:**
  - Danh sách chính xác các file sẽ tạo mới, sửa đổi hoặc xóa bỏ.
  - Danh sách các hàm/class/interface sẽ triển khai cùng chữ ký hàm (function signatures).
  - Danh sách các thư viện cần dùng (nếu có) — phải giải trình lý do vì sao không dùng thư viện có sẵn.
  - Kịch bản kiểm thử (Verification & Test Plan) cho từng bước.
- **Chốt chặn (Gate 2):** Kết thúc phản hồi bằng nhãn `[WAITING FOR PLAN APPROVAL]` và dừng lại.

### BƯỚC 3: RÀ SOÁT & PHÊ DUYỆT (STAGE 3 — REVIEW & EXPLICIT APPROVAL)
- **Cơ chế hoạt động:**
  - Agent ở trạng thái **ĐÓNG BĂNG SINH CODE (Code Generation Freeze)**.
  - Con người sẽ rà soát kế hoạch, yêu cầu chỉnh sửa hoặc cấp quyền thực thi.
  - Agent chỉ được phép mở khóa Bước 4 khi nhận được từ khóa phê duyệt rõ ràng từ Con người (ví dụ: `"Approved"`, `"Duyệt"`, `"Proceed to code"`, `"Triển khai theo plan"`).

### BƯỚC 4: TRIỂN KHAI CODE & KIỂM CHỨNG (STAGE 4 — CODE & VERIFY)
- **Điều kiện kích hoạt:** Đã có lệnh duyệt ở Bước 3.
- **Nhiệm vụ của Agent:**
  - Viết code tuân thủ 100% thiết kế và kế hoạch đã thống nhất.
  - Không tự ý "tiện tay" refactor các file không nằm trong danh sách của Bước 2.
  - Nếu phát sinh rào cản kỹ thuật không lường trước khi đang viết code, **LẬP TỨC DỪNG LẠI** và kích hoạt Giao thức RFC (Mục 4).

---

## 3. RÀNG BUỘC KIẾN TRÚC HỆ THỐNG URBAN SAFETY SOC (DOMAIN & PIPELINE CONSTRAINTS)

Hệ thống sản phẩm là một nền tảng **An toàn Đô thị (Urban Safety)** hoạt động theo thời gian thực. Mọi thiết kế và dòng code của Agent phải tuân thủ nghiêm ngặt kiến trúc 4 tầng nghiệp vụ sau:

```
[Camera Streams] 
      │ (Frame Ingestion & Rolling Buffer)
      ▼
[Tầng 1: Input Layer] ──► [Tầng 2: AI/VLM Analytics] ──► [Tầng 3: Tracking & Dynamic Threat Scoring]
                                                                       │
                                                       (Threat >= Ngưỡng cảnh báo)
                                                                       ▼
[Cơ quan chức năng] ◄── (Đóng gói & Gửi) ◄── [Operator Xác nhận] ◄── [Tầng 4: Operational HITL & Dispatch]
```

### 3.1. Tầng Nguồn Dữ Liệu (Input & Ingestion Layer)
- **Cảm biến chính:** Hệ thống Camera giám sát thu thập luồng video thời gian thực (RTSP, WebRTC, hoặc luồng giả lập chuẩn hóa từ video file theo thời gian thực).
- **Ràng buộc bất đồng bộ (Non-blocking Ingestion):** Luồng đọc khung hình (Frame Grabber) phải tách biệt hoàn toàn với luồng suy luận AI (Inference Worker) thông qua hàng đợi hoặc bộ đệm vòng (Ring Buffer). Tuyệt đối không để quá trình gọi VLM làm nghẽn (block) luồng thu nhận video.
- **Bộ đệm Bằng chứng (Evidence Rolling Buffer):** Hệ thống phải duy trì bộ đệm lưu trữ tạm thời các khung hình trước và sau sự kiện (pre-event & post-event buffer) để sẵn sàng trích xuất video clip bằng chứng khi có yêu cầu.

### 3.2. Tầng Phân Tích Hành Vi (AI / VLM Analytics Layer)
- **Kiến trúc Kết hợp (Hybrid CV + VLM):**
  - Sử dụng Computer Vision tốc độ cao để phát hiện đối tượng (Object Detection), khoanh vùng (Bounding Box) và lọc sự kiện cơ bản trên luồng video.
  - Sử dụng Multimodal LLM / VLM để phân tích sâu ngữ cảnh thị giác trên các khung hình trọng yếu (Keyframes / Event Windows).
- **Trọng tâm Nghiệp vụ:**
  - **Dấu hiệu tiền phạm tội (Pre-crime Indicators):** Lảng vảng bất thường tại khu vực nhạy cảm (loitering), che giấu hoặc mang theo vật nghi là hung khí, theo dõi mục tiêu, tụ tập có dấu hiệu gây rối, xâm nhập trái phép vùng cấm.
  - **Hành vi hậu phạm tội (Post-crime Actions):** Bỏ chạy tốc độ cao khỏi hiện trường, ẩu đả/tấn công, cướp giật, phi tang vật chứng, nạn nhân nằm bất động.
- **Chuẩn hóa Đầu ra (Strict Structured Output):** Mọi phản hồi từ VLM bắt buộc phải tuân thủ JSON Schema nghiêm ngặt (bao gồm: `detected_behaviors`, `pre_crime_flags`, `post_crime_flags`, `confidence_score`, `reasoning_summary`). Cấm phân tích cú pháp từ văn bản tự do (free-text parsing) thiếu kiểm soát.

### 3.3. Tầng Định Danh & Đánh Giá Rủi Ro Động (Tracking & Dynamic Threat Scoring)
- **Gắn thẻ & Theo vết (Tagging & Tracking):**
  - Khi phát hiện dấu hiệu bất thường, đối tượng phải được cấp mã định danh theo vết duy nhất (`track_id` / `subject_tag`) và duy trì bám vết liên tục qua các khung hình.
- **Máy Trạng Thái Đe Dọa Động (Dynamic Threat State Machine):**
  - Hệ thống đánh giá và cập nhật liên tục nhãn mức độ đe dọa (`Threat Level`) theo thời gian thực qua 4 cấp độ chuẩn:
    - `Low` (Bình thường / Quan sát cơ bản)
    - `Medium` (Có dấu hiệu nghi vấn / Tiền phạm tội mức nhẹ — bắt đầu tăng tần suất lấy mẫu VLM)
    - `High` (Rủi ro cao / Dấu hiệu tiền phạm tội rõ rệt hoặc chuẩn bị xung đột — kích hoạt cảnh báo lên màn hình SOC)
    - `Critical` (Khẩn cấp / Đang xảy ra hành vi phạm tội hoặc hậu phạm tội nguy hiểm)
- **Ràng buộc Chuyển đổi Trạng thái:**
  - Việc nâng hoặc hạ cấp `Threat Level` phải dựa trên hàm chấm điểm rủi ro theo chuỗi thời gian (Temporal Threat Scoring), kết hợp lịch sử hành vi của `track_id` chứ không chỉ dựa vào một khung hình đơn lẻ (tránh hiện tượng nhấp nháy nhãn / state flapping).
  - Mọi lần thay đổi `Threat Level` phải được ghi vào lịch sử sự kiện (`threat_history`) kèm theo `timestamp`, điểm số và lý giải (`reasoning`) từ mô hình.

### 3.4. Tầng Xác Thực & Phản Ứng (Operational HITL & Dispatch Layer)
- **Chốt chặn Vận hành viên (Mandatory Operator Verification):**
  - Khi một đối tượng hoặc sự kiện đạt ngưỡng rủi ro theo quy định (mặc định: `High` hoặc `Critical`), hệ thống chuyển trạng thái sự cố sang `AWAITING_OPERATOR_VERIFICATION` và đẩy lên giao diện điều hành.
  - Vận hành viên (Human Operator) có 3 quyền quyết định: `CONFIRM_AND_DISPATCH` (Xác nhận & Điều phối), `DOWNGRADE_MONITOR` (Hạ mức cảnh báo & Tiếp tục theo dõi), hoặc `DISMISS_FALSE_POSITIVE` (Hủy cảnh báo giả).
  - **Cấm tuyệt đối:** Không một lệnh gọi API gửi cơ quan chức năng nào được phép thực thi nếu trạng thái sự cố chưa được chuyển thành `OPERATOR_CONFIRMED` kèm theo `operator_id` và `verified_at`.
- **Đóng gói Hồ sơ Sự cố Tự động (Automated Incident Packaging):**
  - Ngay sau khi Vận hành viên xác nhận (`OPERATOR_CONFIRMED`), hệ thống tự động đóng gói một **Incident Evidence Package** hoàn chỉnh gồm:
    1. **Định danh & Tọa độ:** `incident_id`, `camera_id`, tên khu vực, tọa độ GPS (`latitude`, `longitude`), thời điểm phát hiện.
    2. **Nhãn & Đánh giá Rủi ro:** Mức độ đe dọa hiện tại (`High`/`Critical`), lịch sử leo thang rủi ro (`Low -> Medium -> High -> Critical`), tóm tắt phân tích hành vi từ VLM.
    3. **Bằng chứng Hình ảnh (Visual Evidence):** Ảnh chụp đối tượng rõ nét nhất đã vẽ khung định danh (Annotated Snapshot) và đoạn video clip trích xuất từ Rolling Buffer (bao gồm ngữ cảnh trước và trong khi xảy ra sự kiện).
    4. **Thông tin Kiểm toán (Audit Metadata):** ID của Vận hành viên xác nhận, ghi chú điều hành (nếu có), thời gian xác nhận.
- **Phát lệnh Cảnh báo (Dispatch):** Gửi gói dữ liệu đã đóng gói tới hệ thống tiếp nhận của cơ quan chức năng thông qua giao thức đã định nghĩa, đảm bảo cơ chế chống gửi trùng lặp (idempotency) và lưu log trạng thái phản hồi.

---

## 4. GIAO THỨC GIAO TIẾP KHI XIN PHÉP THAY ĐỔI THIẾT KẾ (ARCHITECTURAL RFC PROTOCOL)

Khi đang ở bất kỳ giai đoạn nào (đặc biệt là trong quá trình viết code ở Bước 4), nếu bạn phát hiện thiết kế hiện tại gặp nút thắt kỹ thuật, xung đột thư viện, độ trễ vượt ngưỡng cho phép, hoặc cần thay đổi cấu trúc dữ liệu/kiến trúc, bạn phải thực hiện đúng quy trình sau:

### 4.1. Nguyên tắc Kích hoạt
1. **Dừng ngay lập tức** việc chỉnh sửa code liên quan đến thay đổi đó.
2. **Không tự ý áp dụng giải pháp thay thế** (workaround) nếu giải pháp đó làm thay đổi luồng dữ liệu, thêm thư viện mới hoặc sửa đổi API contract.
3. Gửi một bản **RFC (Request for Comments)** ngắn gọn cho Developer theo đúng mẫu chuẩn dưới đây.

### 4.2. Mẫu Đệ trình RFC Bắt buộc

```markdown
### 🛑 [RFC - YÊU CẦU THAY ĐỔI THIẾT KẾ / KIẾN TRÚC]

- **Module / Tầng bị ảnh hưởng:** [Tầng 1: Input | Tầng 2: AI/VLM | Tầng 3: Tracking & Scoring | Tầng 4: HITL & Dispatch]
- **Vấn đề phát sinh (Root Cause):** 
  [Mô tả ngắn gọn, chính xác nguyên nhân kỹ thuật khiến thiết kế ban đầu không thể thực thi hoặc gây rủi ro hiệu năng/an toàn]
- **Đề xuất thay đổi (Proposed Mutation):**
  - *Hiện trạng (As-Is):* [Thiết kế/Thư viện/Cơ chế hiện tại trong Spec/Plan]
  - *Đề xuất mới (To-Be):* [Thiết kế/Thư viện/Cơ chế đề xuất thay thế]
- **Đánh giá tác động (Impact Analysis):**
  - *Luồng dữ liệu & Độ trễ:* [Có làm tăng latency hoặc đổi schema không?]
  - *Ràng buộc HITL:* [Khẳng định thay đổi này KHÔNG làm ảnh hưởng tới chốt chặn xác nhận của Operator]
  - *Các file bị ảnh hưởng:* [Danh sách các file cần sửa đổi nếu RFC được duyệt]
- **Phương án dự phòng (Alternative):** [1 phương án khác nếu Developer không muốn thay đổi kiến trúc]

**[STATUS: PAUSED — CHỜ QUYẾT ĐỊNH TỪ ARCHITECT (APPROVE / REJECT / MODIFY)]**
```

### 4.3. Quy tắc Xử lý Phản hồi RFC
- Nếu Con người phản hồi **`APPROVE`**: Cập nhật lại `SPEC.md` và `PLAN.md` để đồng bộ tài liệu trước, sau đó mới tiến hành viết code.
- Nếu Con người phản hồi **`REJECT`**: Tuyệt đối tuân thủ thiết kế ban đầu hoặc thực hiện đúng theo chỉ dẫn kỹ thuật mà Con người đưa ra.

---

## 5. QUY TRÌNH KẾT THÚC TASK & BÀN GIAO (TASK COMPLETION & HANDOVER PROTOCOL)

Nhằm đảm bảo dự án luôn trong trạng thái có thể bàn giao, triển khai và tiếp tục phát triển bởi bất kỳ thành viên nào, mọi lượt hoàn thành task của AI Agent đều phải tuân thủ nghiêm ngặt **Quy trình Chốt chặn 3 Tài liệu (Tri-Document Handover Gate)**:

### 5.1. Checklist Bắt buộc trước khi Nghiệm thu
Trước khi đưa ra thông điệp hoàn thành nhiệm vụ (hoặc gắn cờ `<!-- GOAL_COMPLETE -->`), Agent bắt buộc phải thực hiện các bước sau:
1. **Kiểm tra & Cập nhật `AGENTS.md`:**
   - Bổ sung quy tắc mới (nếu có phát sinh trong quá trình giải quyết bài toán).
   - Ghi lại các bài học kinh nghiệm, lưu ý kỹ thuật (Gotchas & Workarounds), mẹo xử lý lỗi đặc thù của môi trường Cloudflare Worker / Python / React.
2. **Kiểm tra & Cập nhật `README.md`:**
   - Cập nhật các endpoint mới, schema payload hoặc tính năng mới hoàn thành.
   - Hướng dẫn cài đặt, chạy thử nghiệm cục bộ và triển khai thực tế.
   - Đảm bảo người mới clone repo có thể khởi chạy toàn bộ hệ thống chỉ qua tài liệu này.
3. **Kiểm tra & Cập nhật `PROJECT_STRUCTURE.md`:**
   - Quét lại toàn bộ cây thư mục dự án và phản ánh chính xác cấu trúc hiện tại.
   - Cập nhật mô tả vai trò của từng tệp và thư mục mới thêm/sửa/xóa.
4. **Kiểm tra Toàn vẹn Bản Build (Build Integrity Check):**
   - Chạy `pnpm run build` để chứng minh toàn bộ frontend và backend đều compile sạch 100%, không có lỗi type hoặc broken imports.

### 5.2. Mẹo & Kinh nghiệm Kỹ thuật Vận hành (Agent Gotchas & Best Practices)
- **Cloudflare Worker & WebSocket:** Worker runtime tại môi trường local Miniflare không hỗ trợ trực tiếp một số API Node.js như `child_process`. Mọi kết nối WebSocket phải dùng chuẩn Cloudflare `WebSocketPair` và HTTP response status `101 Switching Protocols`.
- **D1 SQL & In-Memory Fallback:** Luôn duy trì bộ đệm In-Memory song song với D1 để dự phòng khi chạy môi trường dev cục bộ hoặc khi D1 binding chưa được provisioned đầy đủ.
- **Bounding Box Normalization:** Dữ liệu bounding box từ camera AI dạng pixel `[x1, y1, x2, y2]` phải luôn được chuẩn hóa sang tỉ đối `[0.0 - 1.0]` (`w, h, x, y`) trước khi phát tới frontend để hiển thị responsive trên canvas.
- **Operational HITL State:** Mọi incident mới gửi vào endpoint `/api/v1/ai/detection` hoặc `/api/incidents` bắt buộc phải có trạng thái khởi tạo là `PENDING_VERIFICATION` / `AWAITING_OPERATOR_VERIFICATION`. Tuyệt đối không được bypass chốt chặn này.
- **CORS & IP Whitelist Security:** Header `Origin` chỉ được phản hồi chính xác khi thuộc whitelist (`Access-Control-Allow-Origin: <origin>` kèm `Vary: Origin`). Khi bật `ENFORCE_IP_WHITELIST="true"`, mọi IP không thuộc whitelist đều bị từ chối với `403 Forbidden` và phải được ghi nhật ký kiểm toán `SECURITY_IP_BLOCKED` vào Cloudflare D1. Luôn bảo lưu loopback (`127.0.0.1`, `::1`) và các dải private CIDR (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`) để không ngắt kết nối nội bộ giữa AI Vision và Worker.
- **DeepSeek 2-Minute Batching & `/api/get-incident` Pipeline:** Tất cả request `POST` gửi về hệ thống (từ camera edge, webhook, hoặc agent client) đều được tự động lưu vào bộ đệm rolling buffer `postRequestLogs`. Định kỳ theo khung 2 phút (`window_seconds = 120`), hệ thống tổng hợp các request, trích xuất hình ảnh (Base64 JPEG) và gọi mô hình mặc định DeepSeek (`@cf/deepseek-ai/deepseek-v4.1-flash-1017`) để đánh giá `severity`, `object_description` (kinematics, posture, vũ khí) và `timeline`. Dữ liệu được persist vào Cloudflare D1 và cung cấp qua endpoint `GET /api/get-incident` để frontend fetch liên tục.
- **TypeScript & Node 24 Native Strip-Types Compatibility:** Khi dự án có các script kiểm thử chạy trực tiếp bằng `node --experimental-strip-types`, các import module nội bộ cần có đuôi `.ts`. Để đảm bảo `npx tsc --noEmit` vẫn biên dịch thành công mà không báo lỗi `TS5097`, cấu hình `tsconfig.json` bắt buộc phải có cặp cờ `"allowImportingTsExtensions": true` và `"noEmit": true`.
- **In-Process Automated AI Layer & Direct DeepSeek API Key:** Không để người dùng hoặc client phải tự gọi endpoint trigger phân tích thủ công. Lớp AI phân tích (`analyzeSingleLogWithIntegratedAI`) được gắn sẵn trong luồng xử lý `POST` và kích hoạt ngầm qua `ctx.waitUntil`. Hệ thống hỗ trợ cắm `DEEPSEEK_API_KEY` gọi trực tiếp `https://api.deepseek.com/chat/completions` (JSON mode) với cơ chế failover 3 tầng (`DEEPSEEK_DIRECT_API` -> `CLOUDFLARE_WORKERS_AI` -> `LOCAL_KINEMATICS_ENGINE`).
- **Standard SOC Structured Audit Logging & Dual Endpoints:** Mọi kết quả phân tích AI đều được tự động chuẩn hóa thành log SOC (`IStandardSocLogEntry`) chứa `log_id`, `latency_ms`, `model_provider`, `threat_score`, `object_description`, ghi đồng thời vào bảng `audit_logs` của D1 và bộ nhớ đệm. Cả 2 endpoint `GET /api/get-incident` và `GET /api/get-incidents` đều trả về JSON cấu trúc chuẩn đã phân tích bởi AI. Endpoint `GET /api/soc/logs` cho phép tra cứu toàn bộ nhật ký kiểm toán chuẩn SOC.
- **Cloudflare KV Incident Pipeline & Dual Input/Output Tracing:** Để hỗ trợ debug nhanh chóng và trực quan, hệ thống ghi nhận vào Cloudflare KV (`INCIDENT_CACHE`) cả **Input** (`deepseek:input:<event_id>`) và **Output** (`deepseek:output:<event_id>`), đồng thời hợp nhất thành `deepseek:trace:<event_id>` có thể truy vấn tức thời qua `GET /api/kv/trace/:id`. Mảng `kv_recent_incidents` được lưu trong KV giúp Dashboard fetch dữ liệu với độ trễ biên cực thấp `< 15ms`.
- **AI Analyzer UI Optimization:** Khối Bảng Thống kê Tóm tắt Dữ liệu Phân lớp (Data Summary / Class Distribution Matrix) trong `AiAnalyzerView.tsx` đã được gỡ bỏ hoàn toàn nhằm tránh trùng lặp với cụm thẻ tập trung trên `SOC Dashboard` (`AiMetricsGrid`), nhường toàn bộ không gian cho Bộ điều khiển ngưỡng và Console VLM thời gian thực.
- **Realtime KV Dashboard Synchronization & Polymorphic Schema Mapping:** Để Dashboard hoạt động thời gian thực với Cloudflare KV (`INCIDENT_CACHE`), hệ thống áp dụng luồng đồng bộ 2 kênh (Dual-channel Realtime): WebSocket phát sự kiện `NEW_INCIDENT` ngay khi lớp AI in-process phân tích xong, kết hợp REST Polling tối ưu 1000ms gọi `/api/get-incident` (đọc trực tiếp `kv_recent_incidents` từ KV với độ trễ `< 15ms`). Mọi dữ liệu trả về đều được chuẩn hóa 100% khớp với cấu trúc DeepSeek KV output: `{ event_id, raw_response, parsed_json: { severity, threat_verdict, investigation_summary, object_description: { primary_action, role, posture_details, weapon_detected, weapon_confidence, kinematics_summary, keypoints_count } }, model_used, latency_ms, timestamp }`. Hàm `mapKvIncidentItem` trên frontend giải mã đa hình cả dạng đối tượng đơn, dạng mảng trực tiếp, hoặc mảng bọc trong `{ incidents: [...] }` mà không làm vỡ giao diện. Toàn bộ thông tin động học (`kinematics_summary`), tư thế, tên model và độ trễ đều được render đầy đủ trên `RecentThreatsTable`, `EvidencePlaybackModal` và `IncidentFeedView`. Mọi sự cố mới luôn được khóa chặt ở trạng thái `AWAITING_OPERATOR_VERIFICATION` / `PENDING_VERIFICATION` theo đúng chốt chặn [CD-04].
- **Live Camera Stream Fetching & Edge Proxy Backup (`LAPTOP_01`):** Luồng video trực tiếp từ camera Laptop (`https://means-brick-determined-send.trycloudflare.com/api/v1/cameras/LAPTOP_01/stream`) được hiển thị trực tiếp trên `CameraSlot`. Để dự phòng khi địa chỉ tunnel Cloudflare thay đổi, Worker lưu trữ biến cấu hình `LIVE_CAMERA_STREAM_URL` trong `wrangler.toml` và mở endpoint proxy `GET /api/v1/cameras/:id/stream` truyền phát trực tiếp `response.body` (chunked MJPEG) kèm CORS headers (`Access-Control-Allow-Origin: *`). Frontend tự động thử qua proxy và có fallback sang `directStreamUrl` kèm cơ chế thử lại tự động khi mất kết nối.
- **Camera Matrix (2x2) Zoom-in / Zoom-out Mechanics:** Khắc phục triệt để lỗi phóng to thu nhỏ trên ma trận 2x2 bằng việc bổ sung state điều hướng `zoomedCameraId`. Click vào ô camera hoặc nút `1x1 Focus` cho phép phóng to camera được chọn; nút `2x2 Grid` hoặc phím tắt `Escape` cho phép trở về bố cục lưới 2x2 tức thì. Các nút PTZ `+` / `-` áp dụng zoom kỹ thuật số (`scale: 1.0x - 3.5x`) trực tiếp trên camera đang quan sát.
- **Compact Alert Log & Dynamic 80/20 Layout Division:** Khối `ThreatScoreModule` cồng kềnh đã được thay thế hoàn toàn bằng **Alert Log Rút Gọn (`AlertLogModule`)** hiển thị danh sách cảnh báo thời gian thực sớm và rõ ràng nhất cho người trực (Badge CRITICAL, HIGH, MED, thời gian hh:mm:ss, mã camera, hành vi nhận diện, nút xem nhanh). Khi người trực kích hoạt phóng to quan sát camera, bố cục Dashboard tự động chia thành:
  1. **Khu vực Camera (80% width):** Hiển thị camera quan sát chính nổi bật kèm dải camera phụ chia đều không gian.
  2. **Khu vực Alert Log (20% width):** Mở rộng thành **Right Menu Modal chiếm đúng 20% chiều rộng**, ghim sát lề phải màn hình để người trực vừa quan sát chi tiết video vừa theo dõi sát sao luồng cảnh báo an ninh.
- **Deprecation & Clean Removal of Unused Tabs:** Hai tab `Live Video Wall` và `AI Analyzer` cùng toàn bộ tệp view (`LiveVideoWallView.tsx`, `AiAnalyzerView.tsx`) đã được gỡ bỏ hoàn toàn khỏi hệ thống nhằm tập trung tối đa tài nguyên cho SOC Dashboard chính, đảm bảo mã nguồn compile sạch 100% không còn bất kỳ tham chiếu mồ côi nào.
