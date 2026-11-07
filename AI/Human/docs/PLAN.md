# KẾ HOẠCH TRIỂN KHAI (IMPLEMENTATION PLAN)
## MỞ RỘNG BỘ LUẬT NHẬN DẠNG HÀNH VI NGUY HIỂM & KHỬ FALSE POSITIVE
**Mã kế hoạch:** `PLAN-URBANSOC-RULES-02`  
**Dựa trên tài liệu đặc tả:** `SPEC-URBANSOC-RULES-02`  
**Phương pháp luận:** Spec-Driven Development (SDD) & Strict Human-in-the-Loop (AGENTS.md)  
**Trạng thái:** Triển khai (Execution Stage)

---

## 1. DANH SÁCH FILE CẦN CẬP NHẬT & TẠO MỚI

1. **`src/urbansoc/domain/enums.py`:**
   - Bổ sung các giá trị mới vào `BehaviorType`:
     - `WEAPON_THREAT = "WEAPON_THREAT"`
     - `SNATCHING = "SNATCHING"`
     - `PURSUIT = "PURSUIT"`
     - `RESTRAINING = "RESTRAINING"`
     - `SURROUNDING = "SURROUNDING"`
     - `INTRUSION = "INTRUSION"`
2. **`src/urbansoc/behavior/kinematics.py`:**
   - Bổ sung các hàm tính toán góc và độ vươn khớp xương:
     - `compute_joint_angle(p1, p2, p3)`: Tính góc khớp (ví dụ góc khuỷu tay $\theta_{\text{elbow}}$ từ Shoulder-Elbow-Wrist).
     - `compute_arm_extension(shoulder, wrist, body_height)`: Tính tỷ lệ vươn cánh tay so với chiều cao cơ thể.
     - `compute_wrist_distance(left_wrist, right_wrist)`: Tính khoảng cách giữa hai cổ tay để xác định tư thế cầm vũ khí 2 tay (tactical two-handed grip).
   - Mở rộng `TrackHistoryState` để lưu vết các đặc trưng động học mới này.
3. **`src/urbansoc/behavior/rules.py`:**
   - Bổ sung hàm kiểm tra vũ khí:
     - `check_weapon_threat(pose, current_state, history, ...)`: Nhận diện chĩa súng 2 tay, chĩa hung khí 1 tay vươn thẳng, và tư thế vung hung khí từ trên cao.
   - Bổ sung hàm kiểm tra đột nhập:
     - `check_intrusion(pose, current_state, history, ...)`: Nhận diện trèo tường / leo rào dựa trên việc tăng cao tọa độ chân và hông theo trục dọc.
   - Tích hợp vào hàm tổng thể `evaluate_single_track_behavior`.
4. **`src/urbansoc/behavior/interactions.py`:**
   - Nâng cấp phát hiện ẩu đả `analyze_fighting` (hỗ trợ cả đối kháng 2 chiều và tấn công 1 chiều).
   - Thêm `analyze_snatching`: Nhận diện cướp giật (tiếp cận sát $\to$ giằng giật $\to$ bứt tốc tháo chạy phân kỳ cự ly).
   - Thêm `analyze_pursuit`: Nhận diện rượt đuổi / truy sát (cùng chạy tốc độ cao $\ge 1.6\text{ bh/s}$ theo hướng đồng quy $\cos(\theta) \ge 0.70$).
   - Thêm `analyze_restraining`: Nhận diện khống chế / kẹp cổ / giằng co ôm giữ (độ chồng lấn IoU $\ge 0.38$ kéo dài $\ge 12$ frames).
   - Thêm `analyze_surrounding`: Nhận diện vây ráp mục tiêu ($\ge 3$ người khép góc xung quanh 1 người).
5. **`src/urbansoc/behavior/state_machine.py`:**
   - Cập nhật nhóm Fast-Track (6 frames): Thêm `WEAPON_THREAT`, `SNATCHING`, `RESTRAINING`.
6. **`src/urbansoc/behavior/engine.py`:**
   - Tích hợp toàn bộ các kết quả từ đơn lẻ và tương tác đa người vào Hysteresis State Machine và Audit Logging.
7. **`tests/`:**
   - `tests/test_rules.py`: Bổ sung kiểm thử `WEAPON_THREAT`, `INTRUSION`, và các ca khử false positive (vỗ tay, nghe điện thoại, đi bộ).
   - `tests/test_interactions.py`: Bổ sung kiểm thử `SNATCHING`, `PURSUIT`, `RESTRAINING`, `SURROUNDING`, `FIGHTING`.
   - `tests/test_state_machine.py`: Kiểm thử fast-track cho các hành vi nguy hiểm mới.

---

## 2. KỊCH BẢN KIỂM THỬ XÁC MINH (VERIFICATION PLAN)

- Chạy `pytest -v` đảm bảo toàn bộ các bài test mới và cũ đều đạt 100% Passed.
- Kiểm tra kịch bản triệt tiêu False Positive:
  1. Hai người đi bộ bình thường cạnh nhau $\to$ Không báo `FIGHTING` / `PURSUIT`.
  2. Một người đưa tay lên nghe điện thoại $\to$ Không báo `WEAPON_THREAT`.
  3. Hai người chạy ngược chiều lướt qua nhau $\to$ Không báo `PURSUIT`.
  4. Người vỗ tay chúc mừng $\to$ Không báo `WEAPON_THREAT`.
- Kiểm tra các kịch bản hành vi nguy hiểm thật:
  1. Hai người đối đầu vung tay mạnh $\to$ Báo `FIGHTING` / `CRITICAL`.
  2. Người chĩa cánh tay duỗi thẳng hướng mục tiêu $\to$ Báo `WEAPON_THREAT` / `CRITICAL`.
  3. Người tiếp cận giật rồi bứt tốc chạy phân kỳ $\to$ Báo `SNATCHING` / `CRITICAL`.
  4. Hai người cùng chạy theo một hướng $\to$ Báo `PURSUIT` / `HIGH`.
  5. Hai người ôm dính giằng co $\to$ Báo `RESTRAINING` / `CRITICAL`.
  6. Ba người vây một người $\to$ Báo `SURROUNDING` / `HIGH`.
  7. Người leo tường trèo cao $\to$ Báo `INTRUSION` / `HIGH`.
