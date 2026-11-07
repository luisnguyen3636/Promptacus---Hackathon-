# KẾ HOẠCH TRIỂN KHAI HOÀN THIỆN GIAO DIỆN 8 PHÂN HỆ MENU
# CYBERGUARD AI · SOC v2.1

---

> **Tài liệu căn cứ:** `AGENTS.md` & `Dashboard/Front End/SPEC.md`  
> **Mục tiêu:** Mở rộng và làm phong phú toàn bộ 8 giao diện phân hệ tác chiến trên menu  
> **Giai đoạn:** `STAGE 2 & 4 — IMPLEMENTATION & VERIFICATION`

---

## 1. DANH MỤC CÁC TỆP TIN TRIỂN KHAI
1. `src/components/views/DashboardView.tsx`: Bổ sung thanh tác vụ nhanh (Mute Siren, Export Report, Emergency Lockdown).
2. `src/components/views/LiveVideoWallView.tsx`: Mở rộng 6 camera, Layout 3x2/2x2/1x1, IR/CCTV filter, Audio Level meters, Presets P1-P3.
3. `src/components/views/NetworkTopologyView.tsx`: Bổ sung sơ đồ SVG tương tác, luồng dữ liệu hạt xung, bảng 6 cổng switch chi tiết.
4. `src/components/views/ThreatIntelligenceView.tsx`: Bổ sung ma trận MITRE ATT&CK đô thị, 4 thẻ IoC, bảng Blacklist có nút chặn IP tương tác.
5. `src/components/views/IncidentFeedView.tsx`: Bổ sung timeline tác chiến, bộ lọc đa cấp độ, tìm kiếm thời gian thực, liên kết HITL modal.
6. `src/components/views/AiAnalyzerView.tsx`: Bổ sung ma trận phân bổ lớp đối tượng (Person, Vehicle, Loitering, Intrusion), 3 thanh trượt độ nhạy và console VLM.
7. `src/components/views/DeviceManagerView.tsx`: Bổ sung bộ lọc danh mục thiết bị, bảng 43 thiết bị, thao tác PING đo RTT và REBOOT.
8. `src/components/views/SettingsView.tsx`: Bổ sung 4 khối cấu hình nền tảng SOC hoàn chỉnh (Operator, Ngưỡng rủi ro, Buffer, Dispatch Webhook).
9. `src/components/TopHeader.tsx` & `src/App.tsx`: Hoàn thiện đồng bộ breadcrumbs và điều phối router.

---

## 2. KỊCH BẢN KIỂM THỬ (TEST PLAN)
- Kiểm tra trực quan từng view không lỗi cú pháp hoặc tràn chữ.
- Chạy `npm run build` đạt 100% không lỗi.
- Đảm bảo chốt chặn Operational HITL (CD-04) hoạt động xuyên suốt.
