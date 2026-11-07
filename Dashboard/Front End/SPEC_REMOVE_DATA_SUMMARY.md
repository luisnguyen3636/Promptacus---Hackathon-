# ĐẶC TẢ KỸ THUẬT: XÓA DATA SUMMARY TABLE TRONG PHÂN HỆ AI ANALYZER
**Mã tài liệu:** `SPEC-REMOVE-AI-ANALYZER-DATA-SUMMARY-01`  
**Dự án:** Urban Safety AI-SOC (CyberGuard AI v2.1)  
**Phân hệ ảnh hưởng:** `Dashboard/Front End/src/components/views/AiAnalyzerView.tsx`  
**Phương pháp:** Spec-Driven Development (SDD) & Strict HITL  
**Trạng thái:** Chờ phê duyệt (Stage 1 — Specification)

---

## 1. MỤC TIÊU & PHẠM VI YÊU CẦU

Theo yêu cầu từ Kiến trúc sư: *"xóa data summary table trong AI Analyzer"*.

### Hiện trạng trong `AiAnalyzerView.tsx`:
Giao diện `AI Analyzer` hiện tại gồm 3 khối:
1. **Khối 1 (Hiệu năng Hệ thống AI):** 4 thẻ đo lường: `INFERENCE TIME`, `GPU CLUSTER LOAD`, `ACCURACY (mAP@50)`, `ACTIVE THREADS`.
2. **Khối 2 (Bảng Tóm tắt Dữ liệu Phân lớp - Data Summary / Class Distribution Matrix):** 4 thẻ thống kê số lượng dữ liệu đối tượng nhận diện:
   - `CLASS: PERSON` (2,410 lượt - 72.4% Detection Share)
   - `CLASS: VEHICLE` (890 lượt - 24.1% Detection Share)
   - `CLASS: LOITERING` (42 cảnh báo - 3.2% Anomaly Share)
   - `CLASS: INTRUSION / BREACH` (8 cảnh báo - 0.3% Critical Trigger)
3. **Khối 3 (Tương tác Điều khiển & Console):**
   - Cột trái (5/12): Bộ chỉnh ngưỡng tin cậy `AI CONFIDENCE THRESHOLD TUNER`.
   - Cột phải (7/12): Dòng lệnh suy luận trực tiếp `LIVE VLM REASONING STREAM CONSOLE`.

---

## 2. ĐỀ XUẤT THAY ĐỔI (SPECIFICATION OF REMOVAL)

### 2.1. Phương án Thực thi (Khuyến nghị):
- **Xóa bỏ hoàn toàn Khối 2 (Class Distribution Matrix / Data Summary):**
  - Gỡ bỏ khối `div.grid-cols-4` chứa 4 thẻ phân lớp (`CLASS: PERSON`, `CLASS: VEHICLE`, `CLASS: LOITERING`, `CLASS: INTRUSION / BREACH`) khỏi `AiAnalyzerView.tsx` (dòng 69 đến 114).
  - Khối này đã được chuyển sang hiển thị chính thức tại giao diện trung tâm `SOC Dashboard` (thông qua component `AiMetricsGrid.tsx`). Việc xóa khỏi `AI Analyzer` giúp loại bỏ dữ liệu thống kê trùng lặp, tối ưu không gian hiển thị cho Console VLM và Bộ chỉnh ngưỡng.
- **Giữ lại:**
  - Khối 1: 4 thẻ chỉ số hiệu năng AI (`INFERENCE TIME`, `GPU CLUSTER LOAD`, `ACCURACY`, `ACTIVE THREADS`).
  - Khối 3: `AI CONFIDENCE THRESHOLD TUNER` và `LIVE VLM REASONING STREAM CONSOLE`.

*(Lưu ý: Nếu Kiến trúc sư muốn xóa luôn cả Khối 1 thẻ hiệu năng để giao diện chỉ còn Bộ chỉnh ngưỡng và Console, xin vui lòng phản hồi; mặc định Phương án trên sẽ xóa đúng bảng dữ liệu tóm tắt phân lớp Data Summary).*

---

## 3. THIẾT KẾ GIAO DIỆN SAU KHI XÓA (AS-IS VS TO-BE)

### As-Is (Hiện tại):
```
[ Khối 1: 4 Thẻ Hiệu năng AI (Inference, GPU, Accuracy, Threads) ]
[ Khối 2: 4 Thẻ Tóm tắt Dữ liệu (Class Person, Vehicle, Loitering, Intrusion) ]  <-- XÓA BỎ
[ Khối 3: Bộ Chỉnh Ngưỡng (5 cols) | Console VLM Streaming (7 cols) ]
```

### To-Be (Sau khi chỉnh sửa):
```
[ Khối 1: 4 Thẻ Hiệu năng AI (Inference, GPU, Accuracy, Threads) ]
[ Khối 3: Bộ Chỉnh Ngưỡng (5 cols) | Console VLM Streaming (7 cols) ]
```

---

## 4. RÀNG BUỘC KIỂM TRA (VERIFICATION CRITERIA)
1. Giao diện `AI Analyzer` không bị vỡ layout, responsive mượt mà trên mọi độ phân giải.
2. `pnpm run build` đạt kết quả 100% không có lỗi TypeScript hay broken imports.
3. Đồng bộ lại `AGENTS.md`, `README.md` và `PROJECT_STRUCTURE.md` theo chỉ thị [CD-06].

---

**[WAITING FOR SPEC APPROVAL]**
