# KẾ HOẠCH TRIỂN KHAI (IMPLEMENTATION PLAN)
## TÍCH HỢP MÃ BĂM MẬT MÃ HỌC SHA-256 + TIMESTAMP & GỬI TRỌN VẸN METADATA ĐỐI TƯỢNG (FORENSIC EVIDENCE & COMPREHENSIVE SUBJECT TELEMETRY)
**Mã kế hoạch:** `PLAN-URBANSOC-DISPATCH-05`  
**Dựa trên tài liệu đặc tả:** `SPEC-URBANSOC-DISPATCH-05`  
**Phương pháp luận:** Spec-Driven Development (SDD) & Strict Human-in-the-Loop (AGENTS.md)  
**Trạng thái:** Chờ phê duyệt từ Principal Architect / Lead Developer

---

## 1. DANH SÁCH FILE CẦN CẬP NHẬT & TẠO MỚI

1. **`src/urbansoc/domain/webhook_models.py`:**
   - Mở rộng `SubjectCropData`:
     - Thêm `bbox_width`, `bbox_height`, `bbox_aspect_ratio`, `bbox_area`.
     - Thêm `dwell_time_seconds`.
     - Thêm `velocity_vector: List[float]`.
     - Thêm `kinematics: Dict[str, float]` (spine_angle, wrist_velocity, elbow angles, arm extension, wrist distance).
     - Thêm `keypoints: List[Dict[str, Any]]` (danh sách 17 khớp xương COCO: id, name, x, y, conf).
     - Thêm `crop_image_sha256: str` và `crop_image_size_bytes: int`.
   - Mở rộng `full_image` trong `WebhookIncidentPayload`:
     - Thêm `sha256_hash: str` (SHA-256 của JPEG bytes + timestamp_ms).
     - Thêm `image_size_bytes: int`.
2. **`src/urbansoc/telemetry/webhook_dispatcher.py`:**
   - Thêm hàm `compute_forensic_sha256(raw_bytes: bytes, timestamp_ms: int) -> str`.
   - Cập nhật `dispatch_frame_event`:
     - Trích xuất toàn bộ 17 keypoints của đối tượng từ `track.keypoints`.
     - Trích xuất các chỉ số động học từ telemetry/history (`spine_angle`, `wrist_velocity`, `elbow_angles`, `arm_extensions`, `wrist_distance`, `velocity_vector`).
     - Tính toán `crop_image_sha256` cho từng ảnh đối tượng kết hợp với `timestamp_ms`.
     - Tính toán `sha256_hash` cho ảnh toàn cảnh kết hợp với `timestamp_ms`.
3. **`server.py`:**
   - Cập nhật hiển thị log và xác thực mã băm SHA-256 của ảnh nhận được.
   - In ra toàn bộ thông tin keypoints, telemetry động học, và xác thực khớp mã băm.
4. **`tests/test_webhook.py`:**
   - Bổ sung các bài kiểm thử tự động:
     - Kiểm thử hàm `compute_forensic_sha256` tạo đúng mã băm chuẩn xác.
     - Kiểm thử payload nhận được tại mock server có đầy đủ các trường: `sha256_hash`, `crop_image_sha256`, `keypoints` (17 khớp), `kinematics` (động học), `bbox_area`, `dwell_time_seconds`.
     - Kiểm thử tính toán lại mã hash tại server để xác nhận bằng chứng không bị sai lệch (Tamper verification test).

---

## 2. KỊCH BẢN KIỂM THỬ XÁC MINH (VERIFICATION PLAN)

- Chạy `pytest -v tests/test_webhook.py` và `pytest -v` đảm bảo 100% tests Passed.
- Chạy thử nghiệm thực tế với `server.py` trên port 8000 và xác nhận màn hình in ra mã băm SHA-256 kèm toàn bộ thông tin chi tiết của đối tượng.

---

[WAITING FOR PLAN APPROVAL]
