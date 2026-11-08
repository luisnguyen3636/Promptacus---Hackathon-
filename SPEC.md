# ĐẶC TẢ KỸ THUẬT KIẾN TRÚC TOÀN DIỆN (SYSTEM SPECIFICATION v3.0)
## Hệ thống Giám sát An ninh & An toàn Đô thị Thông minh (Urban Safety AI-SOC)
**Tài liệu tham chiếu:** `AGENTS.md` (SDD & HITL Framework, Auto-Approve Mode)  
**Trạng thái:** [SPEC AUTO-APPROVED] (Tự động phê duyệt theo CD-01 & CD-04)  
**Phiên bản:** v3.0 — Tích hợp MMAction2, Mandatory NVIDIA VLM, Debug Logging, Rule Tội phạm, Danh sách Truy nã, Camera Manager, Suy luận Vùng mù Đa Camera  
**Ngày cập nhật:** 2026-11-08  

---

### 1. TỔNG QUAN HỆ THỐNG & CÁC TRỤ CỘT ĐỔI MỚI (EXECUTIVE SUMMARY)

Hệ thống **Urban Safety AI-SOC** được nâng cấp toàn diện lên phiên bản kiến trúc 3.0 với các thay đổi cốt lõi nhằm đáp ứng tiêu chuẩn tác chiến an ninh hiện đại:

1. **Thay thế Hoàn toàn Bộ Nhận diện Người & Hành vi bằng MMAction2 (OpenMMLab MMAction2 Architecture):**
   - Thay thế toàn bộ cơ chế pose/heuristic cũ bằng kiến trúc nhận diện hành động không-thời gian (Spatio-Temporal Action Detection) chuẩn MMAction2.
   - Hỗ trợ pipeline xử lý video clip/temporal window (8-32 frames), backbone trích xuất đặc trưng không-thời gian, và SpatioTemporal Action Classification Head.
   - Ánh xạ trực tiếp hành vi sang 10 nhóm hành động phạm tội nguy hiểm.

2. **NVIDIA NIM Multimodal VLM trở thành Lớp Bắt Buộc (Mandatory VLM Reasoning Layer):**
   - Mọi luồng sự kiện/khung hình phân tích từ camera và MMAction2 **bắt buộc phải đi qua** lớp suy luận NVIDIA VLM trước khi sự cố được phép tạo ra hoặc đẩy lên màn hình SOC.
   - Lớp VLM thực hiện kiểm toán pháp y hình ảnh, thẩm định ngữ cảnh (contextual verification), lọc 100% cảnh báo giả (5-Gate Falsification), và sinh biên bản suy luận (`vlm_reasoning`, `tactical_assessment`, `benign_probability`).

3. **Hệ Thống Debug Logging Toàn Diện (Unified SOC Debug Logging):**
   - Bổ sung các hàm ghi log debug đồng bộ đa tầng: Python Engine, Node.js Backend Gateway, React Frontend.
   - Ghi vết chi tiết từng khung hình, độ trễ, luồng MMAction2, phản hồi VLM, suy luận vùng mù, và thao tác HITL vào các file log chuyên biệt trong `output/logs/`.

4. **Bộ Rule Nhận Diện Các Hành Vi Tội Phạm Phổ Biến (Common Criminal Behavior Rules Engine):**
   - 10 quy tắc nghiệp vụ điều tra:
     1. `WEAPON_BRANDISHING`: Rút/cầm hung khí (dao, súng, gậy gộc).
     2. `VIOLENT_ASSAULT`: Ẩu đả, đánh nhau, đấm đá, bạo lực thể xác.
     3. `ROBBERY_SNATCHING`: Cướp giật tài sản (túi xách, điện thoại) rồi tháo chạy.
     4. `FLEEING_HIGH_SPEED`: Bỏ chạy tốc độ cao khỏi hiện trường.
     5. `LOITERING_SUSPICIOUS`: Lảng vảng tiền phạm tội tại mục tiêu nhạy cảm.
     6. `PERIMETER_INTRUSION`: Xâm nhập trái phép vùng cấm, trèo rào.
     7. `VANDALISM_TAMPERING`: Phá hoại tài sản công cộng, phá hỏng camera.
     8. `VICTIM_COLLAPSED`: Nạn nhân ngã quỵ/bất động sau tấn công.
     9. `HOSTAGE_CHOKEHOLD`: Bắt giữ, khống chế, siết cổ con tin.
     10. `STALKING_PURSUIT`: Bám đuôi, theo dõi mục tiêu cự ly gần khả nghi.

5. **Tái Cấu Trúc SOC Dashboard:**
   - **Xóa bỏ Network Topology:** Loại bỏ giao diện Network Topology khỏi cả frontend và backend.
   - **Xóa bỏ AI Analyzer:** Loại bỏ tab AI Analyzer thừa thãi để tập trung tác chiến.
   - **Chuyển Threat Intelligence thành Danh Sách Truy Nã (Wanted Criminals Registry):** Quản lý hồ sơ tội phạm với đầy đủ chức năng Thêm / Sửa / Xóa (CRUD), xem chi tiết, và chức năng **Đóng Dấu Bằng Chứng (Evidence Stamping)** gắn trực tiếp snapshot/video bằng chứng forensic SHA-256 vào hồ sơ tội phạm.
   - **Chuyển Device Manager thành Camera Manager:** Quản trị và kiểm tra camera chuyên dụng: kiểm tra stream MJPEG/RTSP, đo ping/latency, điều khiển PTZ, kiểm tra đường truyền, kiểm tra AI pipeline và các camera lân cận.
   - **Tối ưu Bố Cục Dashboard:** Thu nhỏ khu vực camera matrix (sang 6 cột), mở rộng khu vực Newest Alert (sang 6 cột) với hình ảnh chứng cứ lớn, tóm tắt lý giải VLM, thẻ tội danh MMAction2, và nút duyệt HITL tức thì.
   - **Gán Threat Score Trực Tiếp Cho Từng Camera:** Xóa chỉ số threat score đơn lẻ tách rời của hệ thống; mỗi camera có threat score riêng biệt (0-100) được tính toán động từ các sự kiện diễn ra tại camera đó.
   - **Suy Luận Vùng Mù Đa Camera (Blind-Spot Reasoning Panel):** Panel chuyên biệt hiển thị luồng suy luận truy vết nghi phạm qua >= 2 camera dựa trên ảnh đầu vào, so khớp đặc trưng ngoại hình (re-ID), vận tốc di chuyển, ước lượng thời gian (ETA) và hành vi giấu kín trong vùng mù.

---

### 2. KIẾN TRÚC 4 TẦNG NÂNG CẤP (UPGRADED 4-LAYER PIPELINE)

```
[Camera Streams: CAM_01, CAM_02, ...] 
      │ (Non-blocking Ingestion, Rolling Evidence Buffer & Diagnostics)
      ▼
[TẦNG 1: INPUT & CAMERA MANAGER] 
      │ Frame Grabber & Per-Camera Health / Metrics
      ▼
[TẦNG 2: MMACTION2 + MANDATORY NVIDIA VLM LAYER]
      │ ├── MMAction2 Spatio-Temporal Action Detection (10 Criminal Behaviors)
      │ └── MANDATORY NVIDIA VLM REASONING (5-Gate Falsification & Forensic Certification)
      ▼
[TẦNG 3: DYNAMIC PER-CAMERA THREAT SCORING & MULTI-CAMERA BLIND-SPOT TRACKING]
      │ ├── Per-Camera Threat Score Engine (0-100 per camera)
      │ └── Multi-Camera Blind-Spot Reasoner (>= 2 Cameras, Re-ID & Trajectory Linkage)
      ▼
[TẦNG 4: OPERATIONAL HITL, WANTED REGISTRY & DISPATCH]
      │ ├── Newest Alert Command Panel (Prominent Large View & Operator Decisions)
      │ ├── Wanted Criminals CRUD & Forensic Evidence Stamping
      │ └── Formal Dispatch to Authorities with Immutable Audit Log
```

---

### 3. ĐẶC TẢ CHI TIẾT CÁC MODULE CHỦ CHỐT

#### 3.1. Module MMAction2: `urbansoc.mmaction2`
- **Class:** `MMAction2DetectorAndRecognizer`
  - Đầu vào: Chuỗi khung hình (temporal window: 8 - 32 frames), camera ID, timestamp.
  - Xử lý: Phân đoạn đối tượng người (Human Spatio-Temporal Localization), trích xuất đặc trưng không-thời gian (3D Spatiotemporal Representation), phân loại hành động phạm tội bằng Action Classification Head.
  - Đầu ra: Danh sách `MMActionDetectionResult` chứa `bbox`, `track_id`, `action_name`, `confidence`, `criminal_category`, `is_criminal_flag`.
  - Cơ chế tự thích nghi: Khởi chạy mô hình MMAction2 tương thích với cấu hình PyTorch/CPU/GPU của môi trường thực thi, có fallback nội tại bảo đảm không bao giờ sập luồng.

#### 3.2. Module NVIDIA VLM Bắt Buộc: `urbansoc.ai.nvidia_vlm`
- Mọi khung hình có tín hiệu hành vi khả nghi hoặc định kỳ đều **bắt buộc** đi qua `NvidiaVisionClient.analyze_surveillance_event()`.
- Cấm tạo sự cố hoặc cảnh báo tới SOC nếu không có chứng nhận `vlm_verified = True`.
- Trả về payload cấu trúc JSON:
  - `vlm_verified`: boolean.
  - `behavior_category`: tên hành vi chuẩn hóa.
  - `threat_level`: `"LOW" | "MEDIUM" | "HIGH" | "CRITICAL"`.
  - `confidence_score`: float [0.0 - 1.0].
  - `benign_probability`: float [0.0 - 1.0] (nếu >= 0.25 -> tự động bác bỏ hoặc hạ cấp).
  - `reasoning_summary`: Tóm tắt pháp y chi tiết.
  - `tactical_assessment`: Khuyến cáo tác chiến cho điều hành viên.

#### 3.3. Module Debug Logging: `urbansoc.telemetry.debug_logger` & `src/debugLogger.js`
- Ghi log định dạng chuẩn: `[TIMESTAMP] [LEVEL] [MODULE] [CAMERA_ID] [TRACE_ID] - MESSAGE {EXTRA_JSON}`
- File đầu ra:
  - `output/logs/soc_debug.log`: Toàn bộ sự kiện hệ thống.
  - `output/logs/mmaction2_detection.log`: Nhận diện người và hành động MMAction2.
  - `output/logs/nvidia_vlm_mandatory.log`: Toàn bộ lượt kiểm định qua VLM.
  - `output/logs/blind_spot_reasoning.log`: Suy luận vùng mù và so khớp đa camera.
  - `output/logs/wanted_registry.log`: Thao tác CRUD và đóng dấu bằng chứng truy nã.

#### 3.4. Module Quản Lý Danh Sách Truy Nã & Đóng Dấu Bằng Chứng
- **Data Model:** `WantedPerson`
  - `id`: chuỗi định danh duy nhất (VD: `WNT-2026-001`).
  - `name`: Họ và tên đối tượng.
  - `alias`: Bí danh / Biệt danh.
  - `threatLevel`: `"CRITICAL" | "HIGH" | "MEDIUM"`.
  - `charges`: Danh sách tội danh (VD: `["Cướp giật tài sản", "Cố ý gây thương tích"]`).
  - `status`: `"WANTED" | "APPREHENDED" | "RED_ALERT" | "MONITORING"`.
  - `avatarUrl`: Ảnh nhận dạng / chân dung.
  - `identificationFeatures`: Đặc điểm nhận dạng thể chất (chiều cao, vóc dáng, vết sẹo, hình xăm, trang phục).
  - `lastSeenCameraId`: Camera phát hiện gần nhất.
  - `lastSeenTimestamp`: Thời gian phát hiện gần nhất.
  - `evidenceStamps`: Danh sách các bằng chứng đã đóng dấu:
    - `stampId`: Mã dấu bằng chứng.
    - `incidentId`: Mã sự cố gắn liền.
    - `evidenceType`: `"KEYFRAME_SNAPSHOT" | "VIDEO_CLIP" | "FORENSIC_CROP"`.
    - `evidenceUrl`: Đường dẫn xem bằng chứng.
    - `sha256Hash`: Mã băm chứng thực pháp y.
    - `stampedBy`: ID Vận hành viên đóng dấu.
    - `stampedAt`: Thời gian đóng dấu.
    - `notes`: Ghi chú điều tra.
- **REST APIs:**
  - `GET /api/v1/wanted`: Lấy danh sách hồ sơ truy nã.
  - `POST /api/v1/wanted`: Tạo hồ sơ truy nã mới.
  - `PUT /api/v1/wanted/:id`: Cập nhật thông tin hồ sơ.
  - `DELETE /api/v1/wanted/:id`: Xóa hồ sơ truy nã.
  - `POST /api/v1/wanted/:id/evidence`: Đóng dấu bằng chứng mới vào hồ sơ.

#### 3.5. Module Camera Manager & Gán Threat Score Cho Từng Camera
- Mỗi camera trong danh sách fleet sở hữu:
  - `threatScore`: Giá trị số nguyên từ 0 đến 100 phản ánh rủi ro hiện tại của camera.
  - `threatLevel`: `"LOW" | "MEDIUM" | "HIGH" | "CRITICAL"`.
  - `streamDiagnostics`: Độ trễ ping (ms), FPS, Bitrate, Resolution, Trạng thái (ONLINE / DEGRADED / OFFLINE).
  - `connectedBlindSpots`: Danh sách vùng mù tiếp giáp camera này.
- APIs:
  - `GET /api/devices/cameras`: Trả về danh sách camera kèm `threatScore` và telemetry.
  - `POST /api/devices/cameras/:id/ping`: Kiểm tra đường truyền và đo độ trễ tức thời.
  - `POST /api/devices/cameras/:id/ptz`: Điều khiển PTZ kiểm tra góc quay.

#### 3.6. Module Suy Luận Vùng Mù Đa Camera (Blind-Spot Reasoning Panel)
- Dữ liệu so khớp đa camera:
  - `sessionId`: Mã phiên truy vết vùng mù.
  - `sourceCameraId`: Camera nghi phạm vừa rời đi.
  - `sourceKeyframeUrl`: Ảnh nghi phạm tại camera nguồn.
  - `exitGate`: Hướng/cổng thoát của camera nguồn.
  - `blindSpotZone`: Vùng mù nghi phạm đi vào (khoảng cách, hành lang, vật cản).
  - `targetCandidates`: Danh sách camera đích khả dĩ kèm xác suất (Softmax), ETA dự kiến.
  - `destinationCameraId`: Camera đích nghi phạm xuất hiện.
  - `destinationKeyframeUrl`: Ảnh nghi phạm xuất hiện tại camera đích.
  - `reidSimilarityScore`: Độ tương đồng ngoại hình/quần áo giữa 2 ảnh (0 - 100%).
  - `verified`: Trạng thái xác thực của điều hành viên (`AWAITING_CONFIRMATION` / `CONFIRMED` / `REJECTED`).

---

### 4. ĐÁNH GIÁ VÀ PHÊ DUYỆT TỰ ĐỘNG
Tài liệu Đặc tả Kỹ thuật v3.0 đã hoàn chỉnh, bao quát toàn bộ 12 yêu cầu của người dùng, sẵn sàng chuyển ngay sang Bước 2: Lập Kế hoạch Triển khai (`PLAN.md`).

`[SPEC AUTO-APPROVED]`
