# KẾ HOẠCH TRIỂN KHAI (IMPLEMENTATION PLAN)
## TRIỂN KHAI HỆ THỐNG ĐA CAMERA THEO MÔ HÌNH CLIENT - SERVER VỚI MÁY CHỦ SUY LUẬN TRUNG GIAN
**Mã kế hoạch:** `PLAN-URBANSOC-MULTICAM-06`  
**Dựa trên tài liệu đặc tả:** `SPEC-URBANSOC-MULTICAM-06`  
**Phương pháp luận:** Spec-Driven Development (SDD) & Strict Human-in-the-Loop (AGENTS.md)  
**Trạng thái:** Chờ phê duyệt từ Principal Architect / Lead Developer

---

## 1. DANH SÁCH FILE CẦN TẠO MỚI & CẬP NHẬT

### 1.1. Các File Tạo Mới
1. **`src/urbansoc/client/edge_client.py`:**
   - Triển khai lớp `EdgeCameraClient`:
     - Khởi tạo camera nguồn qua `CameraSource` (hỗ trợ webcam index, RTSP URL, hoặc video file).
     - Đăng ký thông tin định danh và vị trí địa lý với Central Server (`POST /api/v1/cameras/register`).
     - Vòng lặp gửi frame JPEG dạng binary raw qua `POST /api/v1/ingest/frame` với headers `X-Camera-ID`, `X-Timestamp-Ms`.
     - Tự động điều chỉnh FPS và cơ chế tự động kết nối lại (Auto-reconnect with exponential backoff).
2. **`src/urbansoc/server/camera_context.py`:**
   - Triển khai lớp `CameraContextManager` và `CameraContext`:
     - Quản lý độc lập từng camera: `BehaviorEngine` riêng, `EventThrottler` riêng, bộ đệm khung hình tươi mới nhất.
     - Đảm bảo cách ly 100% ID bám vết (Track IDs) giữa các camera khác nhau.
3. **`src/urbansoc/server/inference_server.py`:**
   - Triển khai máy chủ HTTP đa luồng (`ThreadingHTTPServer`):
     - Handler `POST /api/v1/cameras/register`: Tiếp nhận đăng ký camera.
     - Handler `POST /api/v1/ingest/frame`: Nhận raw binary JPEG, nạp vào `YOLOPoseDetector`, định tuyến kết quả sang đúng `CameraContext`.
     - Tích hợp `WebhookDispatcher` để khi bất kỳ camera nào phát hiện mối đe dọa thì lập tức đóng gói và bắn POST kèm mã băm SHA-256 + 17 keypoints.
     - Handler `GET /api/v1/cameras`: Trả về JSON danh sách camera và trạng thái.
     - Handler `GET /`: Trang Web Dashboard HTML trực quan hiển thị lưới đa camera và sự kiện thời gian thực.
4. **`client.py` (Script chạy riêng ở Edge Client):**
   - File thực thi độc lập tại máy biên: `python3 client.py --server-url http://... --camera 0 --camera-id CAM_01`.
5. **`tests/test_multicam.py`:**
   - Bộ test tự động kiểm thử toàn diện:
     - Dựng Central Inference Server nội bộ trong test suite.
     - Chạy đồng thời 2 Edge Clients mô phỏng (CAM_01 và CAM_02) gửi frame đồng thời.
     - Xác nhận server cách ly ngữ cảnh thành công, không va chạm Track ID.
     - Xác nhận phát hiện hành vi nguy hiểm trên một camera kích hoạt đúng sự kiện webhook mang đúng `camera_id` và tọa độ tương ứng.
     - Xác nhận cơ chế xử lý mất kết nối (client disconnect / timeout).

### 1.2. Các File Cần Sửa Đổi
1. **`src/urbansoc/cli.py` & `main.py`:**
   - Hỗ trợ thêm mode `server` và `client`:
     - `python3 main.py --mode server --port 8000 --weights yolo/yolo11n-pose.pt`
     - `python3 main.py --mode client --server-url http://localhost:8000 --camera 0 --camera-id CAM_01`
2. **`README.md`:**
   - Bổ sung sơ đồ kiến trúc và hướng dẫn triển khai thực tế đa camera Client-Server.

---

## 2. KỊCH BẢN KIỂM THỬ XÁC MINH (VERIFICATION PLAN)

### 2.1. Kiểm thử Đơn vị & Tích hợp Tự động (`pytest`)
- Lệnh chạy:
  ```bash
  /home/test/Hackathon-Test-/.venv/bin/pytest -v tests/test_multicam.py
  /home/test/Hackathon-Test-/.venv/bin/pytest -v
  ```
- Tiêu chí: **100% tests Passed** (Cả 42 tests cũ và toàn bộ tests đa camera mới).

### 2.2. Kiểm thử Thực Tế Client - Server Đa Camera
1. Khởi động Central Server: `python3 main.py --mode server --port 8000`.
2. Khởi động Edge Client 1 (Mô phỏng CAM_01):
   `python3 client.py --server-url http://127.0.0.1:8000 --camera output/EVIDENCE_20261107_133243_HUMAN.mp4 --camera-id CAM_EAST_01 --camera-name "Cổng Đông"`.
3. Khởi động Edge Client 2 (Mô phỏng CAM_02):
   `python3 client.py --server-url http://127.0.0.1:8000 --camera 0 --camera-id CAM_WEST_02 --camera-name "Cổng Tây"`.
4. Mở trình duyệt xem Dashboard: `http://127.0.0.1:8000` hiển thị lưới giám sát đa camera hoạt động mượt mà.

---

[WAITING FOR PLAN APPROVAL]
