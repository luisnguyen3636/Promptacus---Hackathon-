# URBAN SAFETY AI-SOC: HỆ THỐNG GIÁM SÁT AN NINH & BỘ LUẬT NHẬN DẠNG HÀNH VI NGUY HIỂM CHUẨN CAO

Hệ thống thị giác máy tính giám sát an ninh đô thị thông minh chuẩn SOC, tích hợp phát hiện người, ước lượng tư thế 2D (Pose Estimation), bám vết đối tượng (Multi-Object Tracking), phân tích động học chuỗi thời gian (Kinematics) để nhận diện **13 hành vi an ninh chuyên sâu**, gán 4 mức độ đe dọa động và tự động trích xuất bằng chứng video clip sự cố.

---

## 1. TÍNH NĂNG CỐT LÕI & DANH MỤC 13 HÀNH VI

### 1.1. Bảng Phân Loại Hành Vi Nguy Hiểm & Cơ Chế Khử False Positive

| STT | Mã Hành vi | Mức Đe dọa | Threat Score | Diễn giải Nhận dạng | Cơ chế Khử Báo Động Giả (Anti-False-Positive) |
| :-: | :--- | :---: | :---: | :--- | :--- |
| **1** | **`WEAPON_THREAT`** | `CRITICAL` | `0.96` | Cầm / chĩa súng 2 tay chiến thuật (Isosceles/Weaver), chĩa hung khí 1 tay vươn thẳng mục tiêu, hoặc vung vũ khí chuẩn bị bổ chém từ trên cao. | - Loại trừ vỗ tay: vỗ tay có vận tốc đối xứng nhưng không duỗi tay.<br>- Loại trừ nghe điện thoại: nghe điện thoại có khuỷu tay gập sâu ($\theta_{\text{elbow}} < 65^\circ$).<br>- Yêu cầu tư thế giữ ổn định để loại trừ vung tay chỉ đường. |
| **2** | **`FIGHTING`** | `CRITICAL` | `0.95` | Ẩu đả, đấm đá đối kháng 2 chiều hoặc một bên tấn công dồn dập trong cự ly hẹp ($< 1.35 \times \text{avg\_w}$). | - Loại trừ bắt tay / chào hỏi: vận tốc cổ tay êm dịu ($< 350\text{ px/s}$).<br>- Loại trừ đi bộ cạnh nhau: vận tốc tay tự nhiên $< 400\text{ px/s}$. |
| **3** | **`SNATCHING`** | `CRITICAL` | `0.94` | Cướp giật: tiếp cận sát mục tiêu $\to$ vung tay giật mạnh $\to$ bứt tốc tháo chạy tốc độ cao kèm phân kỳ khoảng cách đột ngột ($> 220\text{ px/s}$). | - Bắt buộc phải có đủ 2 pha: Tiếp xúc cự ly hẹp và Bứt tốc phân kỳ thoát ly ngay sau đó. |
| **4** | **`RESTRAINING`** | `CRITICAL` | `0.92` | Khống chế, kẹp cổ, giằng co ôm giữ nạn nhân: độ chồng lấn hộp bao cao ($\text{IoU} \ge 0.38$) kéo dài $\ge 12$ frames kèm động năng giằng co. | - Loại trừ đứng xếp hàng: người xếp hàng có IoU thấp và động năng tay bằng 0. |
| **5** | **`PURSUIT`** | `HIGH` | `0.88` | Rượt đuổi, truy sát: hai đối tượng cùng chạy tốc độ cao với hướng di chuyển đồng quy (Vector Cosine Similarity $\ge 0.65$). | - Hai người chạy ngược chiều lướt qua nhau có $\cos(\theta) < 0 \to$ Loại bỏ lập tức. |
| **6** | **`SURROUNDING`** | `HIGH` | `0.85` | Vây ráp mục tiêu: $\ge 3$ đối tượng khép vòng vây xung quanh 1 đối tượng mục tiêu trong bán kính $< 2.5 \times \text{body\_height}$. | - Kiểm tra đa giác bao quanh mục tiêu, loại trừ đám đông đi bộ cùng hướng. |
| **7** | **`INTRUSION`** | `HIGH` | `0.82` | Trèo tường, vượt rào: vị trí bàn chân và hông dâng cao liên tục theo phương thẳng đứng với tốc độ ngang gần bằng 0 và tay bám trên cao. | - Loại trừ người chạy nhảy: chạy nhảy có tốc độ ngang cao và chân chạm đất theo chu kỳ. |
| **8** | **`FALLEN`** | `CRITICAL` | `0.98` | Nạn nhân gục ngã / bất tỉnh: góc cột sống $\ge 55^\circ$ hoặc $H/W < 0.90$. Tự động nâng threat score lên $1.00$ nếu xảy ra ngay sau bạo lực. | - Bộ lọc EMA quán tính cột sống kết hợp kiểm tra gập gối để phân biệt với ngồi xổm. |
| **9** | **`HANDS_UP`** | `HIGH` | `0.78` | Cầu cứu, giơ tay đầu hàng khi bị đe dọa (cả 2 cổ tay giơ cao quá đầu). | - Yêu cầu cả 2 tay và duy trì ổn định. |
| **10**| **`RUNNING`** | `HIGH` | `0.80` | Di chuyển tốc độ cao $\ge 1.75$ chiều cao cơ thể/giây. | - Tính trên chuỗi 5 frames để loại trừ giật box nhất thời. |
| **11**| **`CROUCHING`**| `MEDIUM` | `0.55` | Cúi khom, ngồi xổm nghi vấn: $H/W < 1.30$, góc cột sống $< 45^\circ$, có gập gối. | - Kiểm tra khớp gối và hông. |
| **12**| **`LOITERING`** | `MEDIUM/HIGH` | `0.52 / 0.72` | Lảng vảng rình rập trong khu vực cục bộ trên 10s (leo thang rủi ro nếu $>20\text{s}$). | - Tính độ dịch chuyển ròng từ tâm ban đầu. |
| **13**| **`NORMAL`** | `LOW` | `0.10` | Sinh hoạt, đi lại bình thường. | - Trạng thái an toàn chuẩn. |

---

## 2. CẤU TRÚC THƯ MỤC DỰ ÁN

```
AI/Human/
├── main.py                      # Entrypoint thông minh duy nhất: tự động nạp venv & chạy camera
├── pyproject.toml               # Metadata package urbansoc, dependencies, pytest
├── requirements.txt             # Danh sách dependencies pip
├── README.md                    # Tài liệu hướng dẫn sử dụng
├── yolo/                        # THƯ MỤC RIÊNG CHỨA MODEL YOLO (User bỏ weights vào đây)
│   ├── README.md
│   └── yolo11n-pose.pt         # Trọng số YOLO11-Pose (tự động nhận diện)
├── configs/
│   └── default.yaml             # Cấu hình tập trung
├── docs/
│   ├── SPEC.md                  # Bản đặc tả kỹ thuật (SPEC-URBANSOC-RULES-02)
│   ├── PLAN.md                  # Kế hoạch triển khai (PLAN-URBANSOC-RULES-02)
│   └── REBUILD_PROMPT.md        # Bản lưu trữ truy vết promt.md
├── src/urbansoc/                # Package mã nguồn chuyên nghiệp
│   ├── domain/                  # Schemas, enums, BBox, keypoints
│   ├── detection/               # YOLO-Pose, MediaPipe, HOG
│   ├── behavior/                # Kinematics, 13 rules, interactions, state machine, engine
│   ├── telemetry/               # BehaviorAuditLogger (JSONL + Log text)
│   ├── io/                      # Non-blocking CameraSource, EvidenceClipRecorder
│   ├── render/                  # Skeleton, BBox vát góc, SOC HUD, Diagnostic Alert Box
│   └── apps/                    # CameraRecorder (live), BatchHumanDetector (offline)
├── tests/                       # 33 bài test tự động pytest (chạy độc lập không cần GPU/camera)
├── models/                      # Cache model MediaPipe (.task)
├── records/                     # Thư mục chứa video batch và SESSION_*_FULL.mp4
└── output/                      # Thư mục lưu JSONL, log, snapshot, và video clip bằng chứng
```

---

## 3. HƯỚNG DẪN CÀI ĐẶT & SỬ DỤNG

### 3.1. Chạy Giám Sát Camera Trực Tiếp (Live Stream)
Chỉ cần thực hiện 1 câu lệnh duy nhất:
```bash
python3 main.py
```
*(File `main.py` tích hợp sẵn cơ chế auto-handoff tự động nhận diện virtualenv, tự nạp mô hình từ `yolo/yolo11n-pose.pt` và khởi động camera).*

### 3.2. Bảng Phím Tắt Điều Khiển (Hotkeys)
Trong cửa sổ camera giám sát:

| Phím | Hành động | Mô tả |
| :---: | :--- | :--- |
| **`q`** | Thoát an toàn | Dừng hệ thống, giải phóng tài nguyên và finalize clip đang ghi. |
| **`s`** | Chụp snapshot | Lưu ảnh chụp đã vẽ bounding box vào `output/snapshot_YYYYMMDD_HHMMSS.jpg`. |
| **`h`** | Bật/Tắt Overlay | Ẩn/Hiện toàn bộ lớp phủ đồ họa (Khung xương, nhãn ID, thanh HUD). |
| **`d`** | Bật/Tắt Debug Box | Ẩn/Hiện bảng đo xa sinh trắc học (Diagnostic Telemetry Panel) ở góc màn hình. |
| **`r`** | Bật/Tắt Ghi toàn phiên | Bắt đầu hoặc dừng ghi video toàn bộ phiên làm việc vào `records/SESSION_*.mp4`. |

### 3.3. Chạy Quét Video Ngoại Tuyến (Batch Mode)
Đặt các video cần phân tích (`.mp4`, `.avi`, `.mov`, `.mkv`, `.wmv`) vào thư mục `records/`, sau đó chạy:
```bash
python3 main.py --mode batch
```
Hệ thống sử dụng cơ chế **Streaming VideoWriter** ghi trực tiếp ra đĩa, đảm bảo bộ nhớ RAM luôn ở mức thấp cố định ($<200\text{MB}$) ngay cả với video độ phân giải cao và thời lượng dài.

---

## 4. CHẠY KIỂM THỬ TỰ ĐỘNG (PYTEST)

Toàn bộ test suite được thiết kế tất định (deterministic), không cần phần cứng camera và không tải mô hình từ mạng:
```bash
pytest -v
```
Toàn bộ **33 test cases** kiểm chứng toàn diện từ schema, 13 luật hành vi nguy hiểm, khử false positive, ẩu đả cặp đôi, cướp giật, rượt đuổi, khống chế, vây ráp, ghi log kiểm toán, rolling buffer clip, cho đến render đa độ phân giải.
