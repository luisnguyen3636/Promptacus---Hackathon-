# KẾ HOẠCH TRIỂN KHAI (IMPLEMENTATION PLAN)
## TÍCH HỢP BỘ GỬI SỰ KIỆN POST WEBHOOK ĐẾN SERVER NGOÀI VỚI ĐẦY ĐỦ METADATA & ẢNH ĐỐI TƯỢNG
**Mã kế hoạch:** `PLAN-URBANSOC-DISPATCH-04`  
**Dựa trên tài liệu đặc tả:** `SPEC-URBANSOC-DISPATCH-04`  
**Phương pháp luận:** Spec-Driven Development (SDD) & Strict Human-in-the-Loop (AGENTS.md)  
**Trạng thái:** Chờ phê duyệt từ Principal Architect / Lead Developer

---

## 1. DANH SÁCH FILE CẦN TẠO MỚI & CẬP NHẬT

### 1.1. Các File Tạo Mới
1. **`src/urbansoc/domain/webhook_models.py`:**
   - Định nghĩa `CameraLocationConfig` (cấu hình camera ID, tên, địa chỉ, GPS lat/lon).
   - Định nghĩa `SubjectCropData` (thông tin đối tượng, hành vi, vai trò, bounding box, ảnh crop base64).
   - Định nghĩa `WebhookIncidentPayload` (schema đầy đủ đóng gói toàn bộ metadata theo yêu cầu).
2. **`src/urbansoc/telemetry/webhook_dispatcher.py`:**
   - Triển khai lớp `WebhookDispatcher`:
     - Worker thread nền bất đồng bộ (`threading.Thread` + `queue.Queue`).
     - Hàm cắt ảnh đối tượng an toàn `crop_subject_image(frame, bbox, margin=0.10)`.
     - Hàm mã hóa ảnh JPEG chất lượng cao sang Base64 `encode_image_to_base64(image, quality=85)`.
     - Bộ lọc chống gửi lặp / Cooldown theo Track ID & Behavior (`EventThrottler`).
     - Cơ chế gửi HTTP POST với timeout (3.5s), tự động thử lại (2 lần retry) khi gặp sự cố mạng tạm thời.
     - Graceful shutdown đảm bảo dọn sạch hàng đợi trước khi thoát chương trình.
3. **`tests/test_webhook.py`:**
   - Bộ test tự động kiểm thử toàn diện:
     - Dựng Mock HTTP Server nội bộ (`http.server.HTTPServer` trong test).
     - Kiểm thử payload gửi đi có đầy đủ tất cả các trường: `timestamp`, `camera` (lat, lon, address), `primary_action`, `weapon`, `subjects` (kèm ảnh crop base64), `full_image` (base64).
     - Kiểm thử cơ chế không nghẽn pipeline (non-blocking) khi server nhận bị trễ hoặc ngắt kết nối.
     - Kiểm thử cơ chế chống gửi lặp (cooldown throttling).

### 1.2. Các File Cần Sửa Đổi
1. **`src/urbansoc/domain/__init__.py`:**
   - Export các schema `CameraLocationConfig`, `SubjectCropData`, `WebhookIncidentPayload`.
2. **`src/urbansoc/telemetry/__init__.py`:**
   - Export `WebhookDispatcher`.
3. **`src/urbansoc/apps/live.py`:**
   - Khởi tạo `WebhookDispatcher` nếu `--webhook-url` được cung cấp (hoặc cấu hình sẵn).
   - Gọi `webhook_dispatcher.dispatch_frame_event(...)` mỗi khi phát hiện hành vi để đẩy sự kiện sang server ngoài.
   - Thêm xử lý `webhook_dispatcher.shutdown()` khi dừng camera.
4. **`src/urbansoc/cli.py`:**
   - Bổ sung các cờ dòng lệnh CLI:
     - `--webhook-url`: URL server nhận POST (ví dụ: `http://localhost:8000/api/incidents`).
     - `--camera-id`: Mã camera (mặc định: `CAM_01`).
     - `--camera-name`: Tên camera / Vị trí hiển thị (mặc định: `Camera Trung Tâm`).
     - `--camera-lat`: Tọa độ vĩ độ GPS (mặc định: `10.776889`).
     - `--camera-lon`: Tọa độ kinh độ GPS (mặc định: `106.700806`).
     - `--camera-address`: Địa chỉ lắp đặt camera (mặc định: `Khu vực Trung Tâm`).
     - `--webhook-min-threat`: Mức đe dọa tối thiểu để gửi webhook (`ALL`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` - mặc định `ALL` để gửi mọi hành vi được phát hiện theo đúng yêu cầu).
     - `--webhook-cooldown`: Thời gian giãn cách giữa các lần gửi cho cùng đối tượng (giây, mặc định `3.0`).

---

## 2. KỊCH BẢN KIỂM THỬ XÁC MINH (VERIFICATION PLAN)

### 2.1. Kiểm thử Đơn vị & Tích hợp Tự động (`pytest`)
- Chạy toàn bộ test suite bằng lệnh:
  ```bash
  /home/test/Hackathon-Test-/.venv/bin/pytest -v tests/test_webhook.py
  /home/test/Hackathon-Test-/.venv/bin/pytest -v
  ```
- Tiêu chí: **100% tests Passed** (Tất cả bài test cũ và bài test webhook mới).

### 2.2. Kiểm thử Thực tế với Mock Server Tự Sinh
- Chạy thử một server HTTP giả lập nhận `POST`:
  - Khởi chạy một session mô phỏng nhận diện sự kiện hành vi.
  - Xác nhận Server nhận được đúng chuẩn JSON:
    1. `timestamp` chuẩn ISO 8601.
    2. `camera`: tọa độ GPS, mã camera, tên địa chỉ.
    3. `weapon`: hung khí có được phát hiện hay không.
    4. `subjects`: danh sách các đối tượng kèm ảnh crop base64 hợp lệ (giải mã được bằng OpenCV/PIL).
    5. `full_image`: ảnh toàn cảnh base64 hợp lệ.

### 2.3. Kiểm thử CLI & Khởi chạy Tích hợp
- Chạy `python3 main.py --help` xác nhận toàn bộ các tham số webhook mới xuất hiện đầy đủ.
- Xác nhận chạy lệnh `python3 main.py` tiếp tục là single entry point ổn định.

---

[WAITING FOR PLAN APPROVAL]
