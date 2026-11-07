# PLAN — KẾ HOẠCH TRIỂN KHAI CẬP NHẬT JSON SERVER V2
**Mã tài liệu:** `PLAN-SERVER-JSON-V2`  
**Trạng thái:** `[PLAN AUTO-APPROVED]`

---

## 1. DANH SÁCH FILE SỬA ĐỔI
1. `CloudflareWorker/src/types.ts`: Cập nhật `IServerIngestPayload`, `IActionValidation`, `IWeaponInfo`, `IAuditMetadata`, `IIncidentItem`, `ICameraDevice`, `IAISubjectKinematics`.
2. `CloudflareWorker/src/camera_manager.ts`: Cập nhật `upsertCameraFromServerPayload` để đọc `camera_name`, `camera` (`zone_id`, `address`, `latitude`, `longitude`), `audit` (`frame_index`, `human_count`), `detection.subjects` (`bbox`, `keypoints`, `kinematics`) và ảnh `image` / `image_base64`.
3. `CloudflareWorker/src/incident_manager.ts`: Hợp nhất luồng `ingestServerPayloadToKv` để lưu trữ đầy đủ cấu trúc JSON mới vào KV (`kv_recent_incidents`, `incident:<id>`), ánh xạ `action_validation`, `weapon_info`, `subject_crop_base64`, `hand_crop_base64`, `forensic_hash`, `detection.subjects`, `audit`.
4. `CloudflareWorker/src/index.ts`: Bổ sung route phục vụ ảnh trực tiếp `GET /api/v1/incidents/:id/image.jpg`, `GET /api/v1/incidents/:id/hand_crop.jpg`, `GET /api/v1/incidents/:id/subject_crop.jpg` từ dữ liệu Base64 trong KV.
5. `Dashboard/Front End/src/types/soc.ts` & `src/hooks/useSocTelemetry.ts`: Cập nhật kiểu dữ liệu và hàm `mapKvIncidentItem` để giữ nguyên toàn bộ trường mới từ Server JSON.
6. `Dashboard/Front End/src/components/Modal/EvidencePlaybackModal.tsx`, `IncidentFeedView.tsx`, `ThreatIntelligenceView.tsx`, `DeviceManagerView.tsx`, `ThreatRow.tsx`, `AlertLogModule.tsx`: Hiển thị đầy đủ `action_validation` (reasoning tiếng Việt & xác suất giả thuyết lành tính), `weapon_info`, 3 ảnh bằng chứng (`image_base64`, `subject_crop_base64`, `hand_crop_base64`), `forensic_hash`, thông số động học `kinematics` (`spine_angle`, `left/right_elbow_angle`, `left/right_arm_extension`), `keypoints`, tọa độ GPS camera và `audit` (`ai_model`, `hash_algorithm`).

## 2. KỊCH BẢN KIỂM THỬ (> 30 TEST CASES)
- Kiểm thử nạp JSON `WEAPON_THREAT` mẫu từ Server và kiểm tra hơn 32 assertions cho toàn bộ trường camera, incident, action_validation, weapon_info, kinematics, keypoints, forensic_hash, endpoints ảnh `.jpg`, Auth, Settings và HITL.
