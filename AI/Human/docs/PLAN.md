# KẾ HOẠCH TRIỂN KHAI (IMPLEMENTATION PLAN)
## MÔ HÌNH CLIENT - SERVER ĐA LAPTOP/CAMERA VỚI MÁY CHỦ SUY LUẬN TRUNG GIAN
**Mã kế hoạch:** `PLAN-URBANSOC-MULTICAM-06`  
**Dựa trên tài liệu đặc tả:** `SPEC-URBANSOC-MULTICAM-06`  
**Phương pháp luận:** Spec-Driven Development (SDD) & Strict Human-in-the-Loop (AGENTS.md)  
**Trạng thái:** Chờ phê duyệt từ Principal Architect / Lead Developer

---

## 1. DANH SÁCH FILE CẦN TẠO MỚI & CẬP NHẬT

### 1.1. Các File Tạo Mới
1. **`src/urbansoc/client/edge_client.py`:**
   - Triển khai `EdgeCameraClient`:
     - Mở webcam trên laptop client bằng `CameraSource(camera_index)`.
     - Vòng lặp đọc frame, nén JPEG (chất lượng 75-80%), gửi `POST /api/v1/ingest/frame` lên server.
     - Cơ chế tự động kết nối lại (Auto-reconnect with exponential backoff).
2. **`client.py`:**
   - Script chạy trực tiếp trên laptop khác:
     ```bash
     python3 client.py --server-url http://192.168.1.xxx:8000 --camera 0 --camera-id LAPTOP_01
     ```
3. **`src/urbansoc/server/camera_context.py`:**
   - Triển khai `CameraContext` và `CameraContextManager`:
     - Cấp phát và quản lý riêng cho từng laptop kết nối: `BehaviorEngine` riêng, `EventThrottler` riêng, bộ nhớ frame mới nhất.
     - Đảm bảo cách ly 100% Track ID giữa các laptop.
4. **`src/urbansoc/server/inference_server.py`:**
   - Triển khai server trung gian đa luồng `ThreadingHTTPServer`:
     - Nhận frame từ nhiều laptop gửi về song song.
     - Chia sẻ chung 1 thực thể `YOLOPoseDetector` trên server để tối ưu GPU/CPU.
     - Định tuyến kết quả suy luận vào đúng `CameraContext`.
     - Tích hợp `WebhookDispatcher` tự động bắn webhook kèm mã băm SHA-256 + 17 keypoints khi phát hiện nguy hiểm.
     - Giao diện Web Dashboard (`GET /`) xem trực tiếp trạng thái và hình ảnh các camera.
5. **`tests/test_multicam.py`:**
   - Unit & Integration tests cho Client-Server đa camera:
     - Dựng Server trung gian giả lập trong test suite.
     - Kết nối đồng thời 2 Client mô phỏng (Laptop 1 và Laptop 2).
     - Kiểm tra không va chạm Track ID.
     - Kiểm tra nhận dạng và kích hoạt webhook.

### 1.2. Các File Cần Sửa Đổi
1. **`server.py`:**
   - Tích hợp sẵn `InferenceServer` để khi chạy `python3 server.py 8000`, server vừa có thể nhận webhook vừa có thể làm Server trung gian phân tích AI đa camera!
2. **`src/urbansoc/cli.py` & `main.py`:**
   - Thêm `--mode server` và `--mode client` vào CLI parser.
3. **`README.md`:**
   - Bổ sung hướng dẫn chi tiết cách kết nối 2 chiếc laptop trong cùng mạng Wi-Fi.

---

## 2. KỊCH BẢN KIỂM THỬ XÁC MINH (VERIFICATION PLAN)

- Chạy `pytest -v tests/test_multicam.py` và `pytest -v` đảm bảo 100% Passed.
- Chạy thử nghiệm thực tế với 2 tiến trình Client (mô phỏng 2 laptop) gửi frame lên Server 8000 và xác nhận server hiển thị đầy đủ cả 2 luồng camera độc lập.

---

[WAITING FOR PLAN APPROVAL]
