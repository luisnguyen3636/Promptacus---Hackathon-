# KẾ HOẠCH TRIỂN KHAI: XÓA DATA SUMMARY TABLE TRONG AI ANALYZER
**Mã tài liệu:** `PLAN-REMOVE-AI-ANALYZER-DATA-SUMMARY-01`  
**Dựa trên:** [SPEC_REMOVE_DATA_SUMMARY.md](file:///c:/Users/admin/OneDrive/Tài%20liệu/SGU/Hackathon/Promptacus---Hackathon-/Dashboard/Front%20End/SPEC_REMOVE_DATA_SUMMARY.md)  
**Trạng thái:** Chờ phê duyệt (Stage 2 — Implementation Plan)

---

## 1. DANH SÁCH TỆP TIN THỰC THI (FILE MANIFEST)

| Tác vụ | Tệp | Mô tả công việc |
|---|---|---|
| **Sửa đổi** | `Dashboard/Front End/src/components/views/AiAnalyzerView.tsx` | Xóa bỏ khối JSX `grid grid-cols-4 gap-4` (dòng 69-114) chứa 4 thẻ phân lớp đối tượng `CLASS: PERSON`, `CLASS: VEHICLE`, `CLASS: LOITERING`, `CLASS: INTRUSION / BREACH`. |

---

## 2. CHI TIẾT THAY ĐỔI TRONG `AiAnalyzerView.tsx`

### Đoạn mã sẽ loại bỏ:
```tsx
      {/* 4 Thẻ Phân bố Phân lớp Đối tượng (Class Distribution Matrix) */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-[#0E131A] border border-[#1E2631] p-3 flex items-center justify-between">
          ... CLASS: PERSON ...
        </div>
        <div className="bg-[#0E131A] border border-[#1E2631] p-3 flex items-center justify-between">
          ... CLASS: VEHICLE ...
        </div>
        <div className="bg-[#0E131A] border border-[#1E2631] p-3 flex items-center justify-between">
          ... CLASS: LOITERING ...
        </div>
        <div className="bg-[#0E131A] border border-[#1E2631] p-3 flex items-center justify-between">
          ... CLASS: INTRUSION / BREACH ...
        </div>
      </div>
```

---

## 3. KỊCH BẢN KIỂM THỬ & KIỂM CHỨNG (VERIFICATION PLAN)

1. **Kiểm tra biên dịch Frontend & Worker:**
   - Chạy lệnh `pnpm run build` từ thư mục gốc để đảm bảo:
     - Vite compile sạch mã nguồn React 19 mà không có lỗi unused imports hay hỏng DOM.
     - `tsc --noEmit` hoàn tất không có lỗi.
2. **Kiểm tra tính toàn vẹn của các bài test:**
   - Chạy lại `node --experimental-strip-types CloudflareWorker/test_integrated_ai_layer.mjs` (26 test passed).
   - Chạy lại `node --experimental-strip-types CloudflareWorker/test_deepseek_pipeline.mjs` (20 test passed).
3. **Đồng bộ bộ 3 tài liệu theo [CD-06]:**
   - Cập nhật `AGENTS.md`, `README.md` và `PROJECT_STRUCTURE.md`.

---

**[WAITING FOR PLAN APPROVAL]**
