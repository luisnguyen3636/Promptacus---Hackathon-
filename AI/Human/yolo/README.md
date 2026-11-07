# YOLO Model Weights Directory

Thư mục này được thiết kế riêng để chứa các file mô hình trọng số YOLO (ví dụ: `yolo11n-pose.pt`, `yolov8n-pose.pt`, v.v.).

### Cách sử dụng:
1. Đặt file mô hình YOLO của bạn vào đây (ví dụ: `yolo/yolo11n-pose.pt`).
2. Chạy `python main.py` ở thư mục gốc của dự án. Hệ thống sẽ tự động tìm và nạp mô hình từ thư mục này.
3. Nếu chưa có file mô hình nào trong thư mục `yolo/`, hệ thống sẽ:
   - Hiển thị thông báo hướng dẫn rõ ràng trên terminal.
   - Chuyển sang chế độ dự phòng an toàn (Fallback sang MediaPipe / OpenCV HOG / Luồng camera giả lập) để hệ thống không bị crash đột ngột.
