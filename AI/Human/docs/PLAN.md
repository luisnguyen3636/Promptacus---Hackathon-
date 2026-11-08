# KẾ HOẠCH TRIỂN KHAI (IMPLEMENTATION PLAN)
## URBAN SAFETY AI-SOC: ĐỊNH KỲ MỖI 30 DETECT GỬI 1 POST REQUEST LÊN URBAN STRIKE
**Mã kế hoạch:** `PLAN-URBANSOC-PERIODIC-30-DETECTS-POST`  
**Dựa trên tài liệu đặc tả:** `SPEC-URBANSOC-PERIODIC-30-DETECTS-POST`  
**Phương pháp luận:** Spec-Driven Development (SDD) & Strict Human-in-the-Loop (AGENTS.md)  
**Trạng thái:** [PLAN AUTO-APPROVED] (Theo quy tắc CD-01 & CD-04 của AGENTS.md)

---

## 1. DANH SÁCH FILE VÀ MỤC TIÊU THAY ĐỔI (ATOMIC TASKS)

### 1.1. `src/urbansoc/server/camera_context.py`
- Lớp `CameraDetectionBatch`:
  - Đặt kích thước batch mặc định là **30** (hỗ trợ cấu hình `SOC_DETECTION_BATCH_SIZE=30`).
  - Lưu trữ detection events, chọn keyframe tốt nhất, và tính toán `batch_summary`.

### 1.2. `src/urbansoc/server/inference_server.py`
- Trong `_handle_ingest_frame()`:
  - Khi chưa đủ 30 detects: trả về nhanh `status: "processed"`, `batch_status: "accumulating"`, không gửi POST lên Urban Strike.
  - Khi đạt đủ 30 detects (`is_ready=True`):
    - Flush batch summary và trích xuất keyframe.
    - Gọi AI phân tích trên keyframe và dữ liệu chuỗi 30 detects.
    - **Sau mỗi 30 detects**: BẤT KỂ là sự cố hay hoạt động bình thường (`NORMAL`), **GỬI ĐÚNG 1 POST REQUEST** lên endpoint Urban Strike (`HARDCODED_MODEL_URL` / `INCIDENT_MODEL_URL`).

### 1.3. `src/urbansoc/telemetry/webhook_dispatcher.py`
- Bổ sung hoặc hỗ trợ cờ gửi định kỳ chu kỳ batch (`periodic_batch_post`):
  - Khi có `batch_summary` và được kích hoạt từ batch flush, cho phép gửi POST kể cả khi `action == NORMAL` hoặc `threat_level == LOW`.
  - Giữ nguyên cơ chế deduplication và throttling (0.5s) để chống gửi trùng lặp.

### 1.4. `server.py`, `src/urbansoc/config.py`
- Cập nhật tham số mặc định batch size sang **30**.

---

## 2. KỊCH BẢN KIỂM THỬ XÁC MINH (VERIFICATION & TEST PLAN: >= 30 TEST CASES)
- Bổ sung test kiểm tra:
  1. 30 detect toàn NORMAL -> Vẫn gửi ĐÚNG 1 POST request lên Urban Strike sau detect 30.
  2. 30 detect có WEAPON_THREAT -> Vẫn gửi ĐÚNG 1 POST request với thông tin threat.
  3. Detect 1 đến 29 -> Không gửi POST request.
  4. Chạy toàn bộ test suites đảm bảo $\ge 30$ test cases PASSED 100%.

---
[PLAN AUTO-APPROVED]

## 3. KẾT QUẢ XÁC MINH KIỂM THỬ (TEST VERIFICATION RESULTS)

- **Tổng số test cases kiểm chứng liên quan:** 31/31 PASSED (100%)
- **Kết quả chi tiết:**
  - `tests/test_detection_batch_20_30_urbanstrike.py`: 8/8 PASSED (100%)
  - `tests/test_multicam.py`: 5/5 PASSED (100%)
  - `tests/test_vlm_receiver_flow.py`: 1/1 PASSED (100%)
  - `tests/test_knife_threat_and_deepseek.py`: 6/6 PASSED (100%)
  - `tests/test_webhook.py`: 11/11 PASSED (100%)
- **Trạng thái:** [COMPLETED & FULLY VERIFIED]

## 4. KẾ HOẠCH BỔ SUNG — PROVENANCE CHO ALERT NVIDIA

- Phân biệt kết quả NVIDIA đã hoàn tất với kết quả local/mock/fallback bằng `source`, `analysis_status` và `model`.
- Đưa kết quả nền qua SSE hiện có để Dashboard cập nhật alert mà không block nhận frame.
- Bảo toàn toàn bộ `nvidia_vlm_analysis` trong webhook; chỉ kết quả NVIDIA hợp lệ, không bị suppress và mức HIGH/CRITICAL mới tạo alert.
- Chặn `CONFIRM_AND_DISPATCH` khi incident chưa được xác thực bởi NVIDIA.
- Xác minh bằng các test nguồn NVIDIA thành công, JSON không hợp lệ, test-action giả lập, và candidate chưa xác thực.

**[PLAN AUTO-APPROVED]**
