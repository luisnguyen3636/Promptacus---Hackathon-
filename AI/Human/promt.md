# PROMPT TÁI KIẾN TRÚC TOÀN DIỆN — URBAN SAFETY AI-SOC / HUMAN DETECT

> **Cách dùng:** Đưa toàn bộ nội dung file này cho AI Coding Agent (Claude Code, Cursor, Copilot Workspace...) làm prompt duy nhất. Prompt mô tả **đầy đủ 100% thành phần** của dự án hiện tại (không bỏ sót module, class, hàm, tham số, ngưỡng, hằng số, định dạng output, phím tắt, luồng dữ liệu, artifact) và yêu cầu **viết lại từ đầu theo cấu trúc gọn gàng hơn** nhưng **bảo toàn nguyên vẹn hành vi nghiệp vụ**.

---

## 0. BỐI CẢNH VÀ MỤC TIÊU

### 0.1. Hiện trạng

Repo `Hackathon-Test-` chứa một dự án Python duy nhất nằm trong thư mục `HUMAN DETECT/` (có dấu cách trong tên — cần loại bỏ khi viết lại). Ngoài thư mục dự án, repo root còn các file rác không liên quan: `hello.md`, `te` (nội dung `123`), `test` (rỗng), `tett` (đoạn code `n = int(input()) / print(n)`), `output/behavior_events.jsonl` (199 KB log rò rỉ ra ngoài dự án), `yolo11n-pose.pt` (6.0 MB weights), và `AGENTS.md` (đang bị xoá ở working tree nhưng vẫn có trong git HEAD).

**Chín file Python hiện tại, tất cả nằm phẳng ở một cấp thư mục:**

| File | Dòng | Vai trò |
| :--- | ---: | :--- |
| `models.py` | 201 | Toàn bộ dataclass/enum schema (SOC + legacy) |
| `behavior_detector.py` | 574 | `BehaviorEngine` + `BehaviorAuditLogger` |
| `yolo_pose_detector.py` | 584 | Pipeline YOLO11-Pose + ByteTrack + HUD + Debug Box |
| `pose_detector.py` | 640 | Fallback MediaPipe PoseLandmarker + tracker nội bộ |
| `camera_recorder.py` | 254 | Ứng dụng camera trực tiếp, vòng lặp GUI, hotkey |
| `human_detection.py` | 201 | Ứng dụng batch quét video ngoại tuyến |
| `clip_recorder.py` | 155 | Rolling buffer trích xuất clip bằng chứng |
| `main.py` | 113 | Entrypoint CLI hợp nhất |
| `test_system.py` | 406 | Bộ 7 test tự động kiểu script (print + assert) |

### 0.2. Mục tiêu của lần viết lại

1. **Bảo toàn 100% hành vi nghiệp vụ** — mọi ngưỡng, công thức, luật phân loại, định dạng log, phím tắt, tham số CLI, bố cục HUD phải giữ nguyên (trừ khi mục 11 yêu cầu sửa).
2. **Cấu trúc package gọn gàng** — tách domain / detection / behavior / render / io / apps, không còn 9 file phẳng.
3. **Loại bỏ trùng lặp** — hai hệ toạ độ bounding box, hai bộ hằng số skeleton, hai bộ màu, hai đoạn vẽ HUD gần giống nhau phải hợp nhất.
4. **Sửa các lỗi kiến trúc đã xác định** ở mục 11.
5. **Test chạy được bằng `pytest`, tất định, không tải model trong unit test.**
6. **Không phá vỡ tài liệu SDD** — vẫn giữ `SPEC.md`, `PLAN.md`, `AGENTS.md` và quy trình 4 bước.

---

## 1. MÔ TẢ HỆ THỐNG

**Tên:** Urban Safety AI-SOC — Human Detection, Pose & Behavior Recognition.
**Loại:** Ứng dụng thị giác máy tính thời gian thực (Python) cho giám sát an ninh đô thị.
**Chức năng cốt lõi:** Nhận frame từ webcam hoặc file video → phát hiện người bằng YOLO11-Pose (17 keypoint COCO) → bám vết đa đối tượng bằng Supervision ByteTrack → phân tích động học chuỗi thời gian để phân loại 1 trong 7 hành vi → gán 1 trong 4 mức đe dọa → ghi audit log JSONL/text → vẽ HUD → tự động trích xuất clip bằng chứng MP4 khi phát hiện người.

**Kiến trúc nghiệp vụ 4 tầng theo `AGENTS.md` (bắt buộc tôn trọng khi viết lại):**

```
[Camera Streams]
      │ (Frame Ingestion & Rolling Buffer)
      ▼
[Tầng 1: Input Layer] ──► [Tầng 2: AI/VLM Analytics] ──► [Tầng 3: Tracking & Dynamic Threat Scoring]
                                                                       │
                                                       (Threat >= ngưỡng cảnh báo)
                                                                       ▼
[Cơ quan chức năng] ◄── (Đóng gói & Gửi) ◄── [Operator xác nhận] ◄── [Tầng 4: Operational HITL & Dispatch]
```

Dự án hiện thực **Tầng 1, 2, 3 và một phần quan sát của Tầng 5 (Audit & Observability)**. **Tầng 4 (HITL & Dispatch) CHƯA tồn tại trong code** — chỉ có trong `AGENTS.md`. Khi viết lại, giữ nguyên ranh giới này: không tự thêm logic gửi cảnh báo ra bên ngoài, không thêm nhánh bỏ qua xác nhận của vận hành viên (vi phạm CD-04).

**Mô hình AI:** `yolo11n-pose.pt` (Ultralytics YOLO11 nano pose, tự tải về khi thiếu). **Fallback:** MediaPipe `pose_landmarker_full.task` / `pose_landmarker_lite.task` (đã có sẵn `models/pose_landmarker_lite.task`, 5.5 MB). **Fallback cuối:** OpenCV HOG + SVM people detector.

---

## 2. TECH STACK VÀ PHỤ THUỘC

`requirements.txt` hiện tại:

```
opencv-python>=4.8.0
numpy>=1.24.0
ultralytics>=8.3.0
supervision>=0.22.0
torch>=2.0.0
```

**Thiếu phụ thuộc:** `mediapipe` (bắt buộc cho nhánh fallback `pose_detector.py`), `pytest` (cho test). Khi viết lại **phải bổ sung** `mediapipe>=0.10.0` và `pytest>=8.0` (dev), hoặc chuyển sang `pyproject.toml` với extras `[dev]`.

Yêu cầu khác:
- Python **3.10+**.
- Đa nền tảng: Linux/macOS dùng `cv2.VideoCapture(index)`; Windows ưu tiên `cv2.CAP_DSHOW` rồi mới fallback (giữ nguyên hành vi này).
- GPU optional: tự dò `torch.cuda.is_available()` nếu `--device` không được truyền.
- **Không phụ thuộc binary `ffmpeg` bên ngoài** — chỉ dùng `cv2.VideoWriter` với fourcc `mp4v`.

---

## 3. SCHEMA DỮ LIỆU — `models.py` → `src/<pkg>/domain/schemas.py` + `enums.py`

### 3.1. Enums

```python
class ThreatLevel(str, Enum):
    LOW = "LOW"; MEDIUM = "MEDIUM"; HIGH = "HIGH"; CRITICAL = "CRITICAL"

class BehaviorType(str, Enum):
    NORMAL = "NORMAL"
    CROUCHING = "CROUCHING"
    LOITERING = "LOITERING"
    HANDS_UP = "HANDS_UP"
    RUNNING = "RUNNING"
    FIGHTING = "FIGHTING"
    FALLEN = "FALLEN"
```

Cả hai là `str, Enum` để serialize JSON trực tiếp.

### 3.2. Dataclass hiện đại (SOC)

```python
@dataclass
class KeypointCOCO:
    id: int            # 0..16
    name: str          # "nose", "left_shoulder", ...
    x: float           # pixel
    y: float           # pixel
    confidence: float  # 0.0..1.0

@dataclass
class BehaviorPrediction:
    primary_behavior: BehaviorType
    confidence: float
    threat_level: ThreatLevel
    threat_score: float                      # 0.00..1.00
    reasoning: str                           # chuỗi giải thích phục vụ kiểm toán
    interacting_with_track_id: Optional[int] = None

@dataclass
class TrackHistoryState:
    timestamp: float
    bbox: Tuple[int, int, int, int]
    centroid: Tuple[float, float]
    keypoints: List[KeypointCOCO]
    spine_angle: float
    wrist_velocity: float
    body_velocity: float

@dataclass
class TrackKinematicsTelemetry:
    track_id: int
    spine_angle: float
    aspect_ratio: float
    speed: float
    wrist_energy: float
    dwell_time: float
    confirmed_behavior: str
    threat_level: ThreatLevel
    threat_score: float

@dataclass
class BehaviorAuditLogEntry:
    event_id: str                            # EVT_YYYYMMDD_HHMMSS_<track_id>
    timestamp: str                           # "YYYY-MM-DD HH:MM:SS.mmm"
    frame_index: int
    track_id: int
    event_type: str                          # TRACK_INITIALIZED | STATE_TRANSITION | THREAT_ESCALATION | CRITICAL_ALERT | HEARTBEAT_ALERT
    previous_behavior: Optional[str]
    current_behavior: str
    threat_level: str
    threat_score: float
    telemetry: Dict[str, float]              # {"spine_angle", "aspect_ratio", "speed", "wrist_velocity"}
    reasoning: str
    dwell_time_seconds: float

@dataclass
class HumanPoseTrack:
    track_id: int
    bbox: Tuple[int, int, int, int]          # (x1, y1, x2, y2)
    detection_conf: float
    keypoints: List[KeypointCOCO] = field(default_factory=list)
    behavior: BehaviorPrediction = field(default_factory=lambda: BehaviorPrediction(
        primary_behavior=BehaviorType.NORMAL, confidence=1.0,
        threat_level=ThreatLevel.LOW, threat_score=0.1, reasoning="Normal activity"))
    dwell_time_seconds: float = 0.0

    @property
    def posture_label(self) -> str: return self.behavior.primary_behavior.value
    @property
    def confidence(self) -> float: return self.detection_conf

@dataclass
class SOCFrameAnalysisResult:
    frame_index: int
    timestamp: str                           # "YYYY-MM-DD HH:MM:SS.mmm"
    human_count: int
    humans: List[HumanPoseTrack] = field(default_factory=list)
    highest_threat_level: ThreatLevel = ThreatLevel.LOW
    highest_threat_score: float = 0.0
    critical_events: List[str] = field(default_factory=list)
    telemetry_list: List[TrackKinematicsTelemetry] = field(default_factory=list)
    recent_alerts: List[str] = field(default_factory=list)
    inference_time_ms: float = 0.0
    tracking_time_ms: float = 0.0
    behavior_time_ms: float = 0.0
    is_recording_evidence: bool = False

    @property
    def has_human(self) -> bool: return self.human_count > 0
    @property
    def requires_operator_attention(self) -> bool:
        return self.highest_threat_level in (ThreatLevel.HIGH, ThreatLevel.CRITICAL)
```

### 3.3. Dataclass legacy (giữ để tương thích nhánh MediaPipe)

```python
@dataclass
class Keypoint:              # MediaPipe 33 landmark
    id: int; name: str; x: int; y: int; z: float; visibility: float

@dataclass
class HumanPose:
    track_id: int
    bbox: Tuple[int, int, int, int]     # ⚠️ (x, y, w, h) — KHÁC HumanPoseTrack
    confidence: float
    keypoints: List[Keypoint] = field(default_factory=list)
    posture_label: str = "Standing"     # "Standing" | "Sitting" | "Observed"

@dataclass
class FrameAnalysisResult:
    frame_index: int; timestamp: str; human_count: int
    humans: List[HumanPose] = field(default_factory=list)
    inference_time_ms: float = 0.0
    is_recording_evidence: bool = False
    @property
    def has_human(self) -> bool: return self.human_count > 0

@dataclass
class HumanIncidentClip:    # metadata clip sự cố — hiện KHÔNG được dùng ở đâu
    event_id: str; source_video: str; start_time: str; end_time: str
    start_frame: int; end_frame: int; duration_seconds: float
    output_filepath: str
    max_confidence: float = 0.0
    primary_behavior: str = "NORMAL"
    threat_level: str = "LOW"
```

> **Quyết định tái kiến trúc bắt buộc:** hai quy ước bbox (`xyxy` vs `xywh`) đang là nguồn lỗi tiềm ẩn. Khi viết lại, định nghĩa **một** type `BBox` duy nhất với trường có tên (`x1, y1, x2, y2`) và **hai hàm chuyển đổi tường minh** `bbox_from_xywh()`, `bbox_to_xywh()` cho nhánh MediaPipe. Không được để `Tuple[int,int,int,int]` trần truồng mà không nói rõ quy ước. `HumanIncidentClip` hoặc phải được dùng thật (batch mode ghi metadata clip sự cố) hoặc bị loại bỏ — không giữ code chết.

---

## 4. ĐỘNG CƠ HÀNH VI — `behavior_detector.py` → `src/<pkg>/behavior/`

### 4.1. Hằng số keypoint COCO-17 (dùng chung toàn hệ thống)

```python
NOSE=0; LEFT_EYE=1; RIGHT_EYE=2; LEFT_EAR=3; RIGHT_EAR=4
LEFT_SHOULDER=5; RIGHT_SHOULDER=6; LEFT_ELBOW=7; RIGHT_ELBOW=8
LEFT_WRIST=9; RIGHT_WRIST=10; LEFT_HIP=11; RIGHT_HIP=12
LEFT_KNEE=13; RIGHT_KNEE=14; LEFT_ANKLE=15; RIGHT_ANKLE=16
```

Danh sách tên tương ứng (thứ tự cố định):
`["nose","left_eye","right_eye","left_ear","right_ear","left_shoulder","right_shoulder","left_elbow","right_elbow","left_wrist","right_wrist","left_hip","right_hip","left_knee","right_knee","left_ankle","right_ankle"]`

Cặp xương COCO-17 (16 cặp, dùng để vẽ):
```python
# Đầu: (0,1) (0,2) (1,3) (2,4)
# Thân: (5,6) (5,11) (6,12) (11,12)
# Tay trái: (5,7) (7,9)     Tay phải: (6,8) (8,10)
# Chân trái: (11,13) (13,15) Chân phải: (12,14) (14,16)
```

**Gate tin cậy keypoint: `confidence > 0.25`** — dùng ở mọi nơi (kinematics, vẽ xương, vẽ khớp). Phải là **một hằng số cấu hình duy nhất**, không hard-code rải rác.

### 4.2. `BehaviorAuditLogger`

```python
BehaviorAuditLogger(output_dir: str = "output", heartbeat_interval: float = 1.0)
```

- `os.makedirs(output_dir, exist_ok=True)`.
- Hai file, mở append, `encoding="utf-8"`, `buffering=1` (line-buffered):
  - `output/behavior_events.jsonl` — mỗi dòng `json.dumps(asdict(entry), ensure_ascii=False)`.
  - `output/behavior_audit.log` — định dạng người đọc được:
    ```
    [2026-11-06 22:10:28.809] [CRITICAL_ALERT] ID #2: NORMAL -> FALLEN (CRITICAL 98%) | Spine:90° Spd:0.00 | Reason: Torso angle 90° (>= 55°) or H/W 0.32 horizontal
    ```
    Công thức: `[{timestamp}] [{event_type}] ID #{track_id}: {prev or "INIT"} -> {current} ({threat_level} {score*100:.0f}%) | Spine:{spine:.0f}° Spd:{speed:.2f} | Reason: {reasoning}`
- `log_event(entry)` ghi cả hai file rồi `flush()` cả hai. Ngoại lệ được **in cảnh báo ra stdout, không raise** (giữ nguyên — nhưng xem mục 11: không được nuốt lỗi im lặng kiểu `except: pass`).
- `close()` đóng an toàn cả hai handle, có guard `if not file.closed`.

### 4.3. `BehaviorEngine` — tham số khởi tạo (giữ nguyên giá trị mặc định)

```python
BehaviorEngine(
    fps: float = 20.0,
    history_window_size: int = 30,            # ~1.5s @20fps
    fall_angle_threshold: float = 55.0,       # độ, tính từ trục dọc
    fall_aspect_ratio_thresh: float = 0.90,   # H/W < 0.90
    run_speed_multiplier: float = 1.75,       # body-heights / sec
    loiter_time_threshold: float = 10.0,      # giây
    fight_wrist_energy_thresh: float = 1200.0,
    fight_distance_norm: float = 1.35,
    enter_debounce_frames: int = 8,
    exit_debounce_frames: int = 12,
    bbox_ema_alpha: float = 0.65,
    output_dir: str = "output",
)
```

### 4.4. Trạng thái nội bộ mỗi track (`tracks_meta: Dict[int, dict]`)

Mỗi `track_id` giữ:
```
first_seen, last_seen, initial_centroid,
history: deque(maxlen=history_window_size),
smooth_bbox,
confirmed_behavior, confirmed_threat_level, confirmed_threat_score, confirmed_since,
candidate_behavior, candidate_streak,
last_heartbeat_time
```
Track mới → log event `TRACK_INITIALIZED` với `reasoning="Initial track identity assigned by ByteTrack"`, `threat_level=LOW`, `threat_score=0.10`, `telemetry={"spine_angle":0.0,"speed":0.0}`.
Track không thấy quá **5.0 giây** (`curr_time - last_seen > 5.0`) → xoá khỏi `tracks_meta`.

`recent_alerts: Deque[str]` với `maxlen=5`, dùng `appendleft`.

### 4.5. API `update()`

```python
def update(
    self,
    tracked_poses: List[HumanPoseTrack],
    timestamp: Optional[float] = None,
    frame_index: int = 0
) -> Tuple[List[HumanPoseTrack], List[TrackKinematicsTelemetry], List[str]]
```
Trả về `(poses_đã_làm_mượt_và_gắn_nhãn_ổn_định, telemetry_list, recent_alerts)`.

Thứ tự xử lý **bắt buộc** cho mỗi pose:
1. Khởi tạo meta nếu track mới (+ log `TRACK_INITIALIZED`).
2. `pose.dwell_time_seconds = curr_time - first_seen`.
3. **Làm mượt bbox bằng EMA**, ghi đè `pose.bbox`:
   ```
   smooth[k] = int(alpha * raw[k] + (1 - alpha) * prev_smooth[k])   với alpha = 0.65
   ```
   áp dụng cho cả 4 toạ độ.
4. `state = _extract_state(...)`; `history.append(state)`.
5. `raw_pred, norm_speed, aspect_ratio = _analyze_single_track(...)`.
6. Áp máy trạng thái hysteresis (mục 4.7).
7. Ghi heartbeat nếu đe dọa HIGH/CRITICAL (mục 4.8).
8. Gán `pose.behavior = BehaviorPrediction(...)` với **hành vi đã confirmed**, không phải hành vi thô.
9. Append `TrackKinematicsTelemetry` (làm tròn: `spine_angle` 1 chữ số, `aspect_ratio` 2, `speed` 2, `wrist_energy` 1, `dwell_time` 1).

Sau vòng lặp: `_analyze_multi_person_interactions(...)` (mục 4.9), dọn track cũ, trả kết quả.

### 4.6. Trích xuất động học — `_extract_state()`

Với `bx1,by1,bx2,by2 = pose.bbox`, `cx=(bx1+bx2)/2`, `cy=(by1+by2)/2`:

**a) Góc nghiêng cột sống `spine_angle` (độ):**
- Lấy trung bình toạ độ vai (`LEFT_SHOULDER`/`RIGHT_SHOULDER` có mặt, chia cho số điểm có mặt) → `(s_x, s_y)`.
- Tương tự hông (`LEFT_HIP`/`RIGHT_HIP`) → `(h_x, h_y)`.
- `spine_angle = degrees(atan2(abs(s_x - h_x), max(1e-4, abs(s_y - h_y))))`
- Nếu thiếu cả vai hoặc cả hông → `0.0`.
- **EMA với quán tính cũ:** `spine_angle = 0.70 * spine_angle + 0.30 * history[-1].spine_angle` (chỉ khi history không rỗng).

**b) Vận tốc thân `body_velocity` (px/s):**
- `dt = max(1e-4, timestamp - prev.timestamp)`
- `dist = hypot(cx - prev.centroid[0], cy - prev.centroid[1])`
- `body_velocity = 0.70 * (dist / dt) + 0.30 * prev.body_velocity`

**c) Vận tốc cổ tay `wrist_velocity` (px/s):**
- Với mỗi cổ tay có mặt ở cả frame hiện tại và frame trước: `d_w = hypot(dx, dy)`, cộng `(d_w / dt) ** 2`.
- `raw = sqrt(sum / count)`; `wrist_velocity = 0.70 * raw + 0.30 * prev.wrist_velocity`.

### 4.7. Luật phân loại — `_analyze_single_track()`

Đầu vào: `aspect_ratio = bh / bw` (với `bw = max(1, x2-x1)`, `bh = max(1, y2-y1)`), `spine_angle` từ state mới nhất.

**Tốc độ chuẩn hoá `norm_speed`:**
```
nếu len(history) >= 5:
    dt   = max(1e-4, history[-1].timestamp - history[-5].timestamp)
    disp = hypot(dx_centroid, dy_centroid)  giữa -1 và -5
    norm_speed = (disp / dt) / max(10.0, bh)     # đơn vị: body-heights/giây
ngược lại: 0.0
```

**Sáu luật, thứ tự ưu tiên tuyệt đối (luật đầu tiên khớp sẽ return ngay):**

| # | Luật | Điều kiện | `BehaviorType` | Threat | `threat_score` | `confidence` | `reasoning` |
| :-: | :--- | :--- | :--- | :--- | ---: | ---: | :--- |
| 1 | **FALLEN** | `spine_angle >= 55.0` **HOẶC** `aspect_ratio < 0.90` | `FALLEN` | `CRITICAL` | `0.98` | `0.95` | `"Torso angle {angle:.0f}° (>= 55°) or H/W {ar:.2f} horizontal"` |
| 2 | **HANDS_UP** | `head_y = min(y của NOSE/LEFT_EYE/RIGHT_EYE có mặt)`; **cả hai** cổ tay có `y < head_y` | `HANDS_UP` | `HIGH` | `0.78` | `0.90` | `"Both hands raised above head in distress / surrender gesture"` |
| 3 | **RUNNING** | `norm_speed >= 1.75` | `RUNNING` | `HIGH` | `0.82` | `0.88` | `"High movement speed: {v:.1f} body-heights/sec (> 1.75)"` |
| 4 | **CROUCHING** | `aspect_ratio < 1.30` **VÀ** `spine_angle < 45.0` **VÀ** (có ít nhất 1 đầu gối) **VÀ** (có ít nhất 1 hông) | `CROUCHING` | `MEDIUM` | `0.55` | `0.75` | `"Compressed posture H/W {ar:.2f} with bent knees"` |
| 5 | **LOITERING** | `dwell_time >= 10.0` **VÀ** `len(history) >= 20` **VÀ** `net_disp < max(120.0, bw * 2.5)` với `net_disp = hypot(centroid - initial_centroid)` | `LOITERING` | `HIGH` nếu `dwell > 20.0`, ngược lại `MEDIUM` | `0.72` / `0.52` | `0.82` | `"Lingering in local area for {t:.1f}s (disp: {d:.0f}px)"` |
| 6 | **NORMAL** | mặc định | `NORMAL` | `LOW` | `0.12` | `0.95` | `"Normal upright posture and standard gait speed"` |

### 4.8. Máy trạng thái Hysteresis / Debounce (chống nhảy nhãn)

Với `new_candidate = raw_pred.primary_behavior`:

```
nếu new_candidate == confirmed_behavior:
        candidate_behavior = None ; candidate_streak = 0
ngược lại:
        nếu new_candidate == candidate_behavior: candidate_streak += 1
        ngược lại:                               candidate_behavior = new_candidate ; candidate_streak = 1

        req_streak = 6                            nếu new_candidate in (FALLEN, FIGHTING)   # fast-track khẩn cấp ~0.3s
                   = exit_debounce_frames (=12)   nếu new_candidate == NORMAL               # cần bằng chứng chắc để trở về bình thường
                   = enter_debounce_frames (=8)   còn lại

        nếu candidate_streak >= req_streak:
                commit: confirmed_behavior / confirmed_threat_level / confirmed_threat_score = raw_pred.*
                        confirmed_since = curr_time ; reset candidate
```

Khi commit, **ghi audit event ngay lập tức** với `event_type`:
- `CRITICAL_ALERT` nếu `raw_pred.threat_level == CRITICAL`
- `THREAT_ESCALATION` nếu `HIGH`
- `STATE_TRANSITION` còn lại

và đẩy badge vào `recent_alerts`: `"[{HH:MM:SS}] ID #{tid} {prev} -> {new}"`.

### 4.9. Heartbeat và tương tác đa người

**Heartbeat:** nếu `confirmed_threat_level in (HIGH, CRITICAL)` và `curr_time - last_heartbeat_time >= 1.0` → ghi event `HEARTBEAT_ALERT` (event_id tiền tố `HB_`), `reasoning="Ongoing {behavior} event"`, `dwell_time_seconds = now - confirmed_since`.

**Tương tác đa người (`_analyze_multi_person_interactions`):** duyệt mọi cặp `(i, j)`, bỏ qua nếu một trong hai đang `FALLEN`. Tính:
- `dist = hypot(c1 - c2)` giữa tâm hai bbox; `avg_w = trung bình chiều rộng hai bbox`.
- Nếu `dist < avg_w * 1.35` **VÀ** (`w_vel1 + w_vel2 > 1200.0` **HOẶC** (`w_vel1 > 800.0` **VÀ** `w_vel2 > 800.0`)) → gán **cả hai** thành `FIGHTING`, `CRITICAL`, `threat_score=0.95`, `confidence=0.92`, `reasoning="Violent physical confrontation with ID #{opponent}"`, `interacting_with_track_id=opponent`.

> ⚠️ **Lỗi kiến trúc hiện tại:** hàm này chạy **sau** khi `pose.behavior` đã được gán từ state machine, nên nó **ghi đè trực tiếp** kết quả đã debounce — phá vỡ chính cơ chế chống nhảy nhãn vừa xây. Hành vi FIGHTING cũng không bao giờ đi qua debounce, không bao giờ tạo audit event, và có thể bật/tắt 1 frame. **Khi viết lại: đưa kết quả pairwise vào cùng pipeline state machine** (coi FIGHTING là một `raw_pred` có độ ưu tiên cao nhất, hoặc một overlay score cộng dồn) để mọi chuyển trạng thái đều qua debounce và đều được log.

`close()` → đóng audit logger.

---

## 5. PIPELINE NHẬN DẠNG — `yolo_pose_detector.py` → `src/<pkg>/detection/yolo_pose.py`

### 5.1. Tham số khởi tạo

```python
YOLOPoseDetector(
    model_path: str = "yolo11n-pose.pt",
    device: Optional[str] = None,              # None = tự dò CUDA
    conf_threshold: float = 0.25,
    iou_threshold: float = 0.45,
    track_activation_threshold: float = 0.25,
    lost_track_buffer: int = 45,               # tăng để giữ ID khi bị che khuất
    minimum_matching_threshold: float = 0.80,  # siết ngưỡng liên kết ByteTrack
    fps: float = 20.0,
    output_dir: str = "output",
)
```

### 5.2. Khởi tạo

- Nếu `device is None`: thử `import torch`; `"cuda" if torch.cuda.is_available() else "cpu"`; lỗi import → `"cpu"`.
- `from ultralytics import YOLO; self.model = YOLO(model_path)`, rồi `self.model.to(device)` (bọc try/except, in ghi chú nếu không chuyển được).
- `sv.ByteTrack(track_activation_threshold=..., lost_track_buffer=45, minimum_matching_threshold=0.80, frame_rate=int(fps))`, đặt trong `warnings.catch_warnings()` lọc `FutureWarning`.
- **Toàn bộ khối này bọc trong try/except:** lỗi → `self.use_fallback = True`, in cảnh báo "Operating in resilient fallback mode", pipeline vẫn trả frame không annotation thay vì crash.
- `self.behavior_engine = BehaviorEngine(fps=fps, enter_debounce_frames=8, exit_debounce_frames=12, bbox_ema_alpha=0.65, output_dir=output_dir)`.
- `self.show_debug_box = True`.
- FPS moving average: `_fps_history` (giữ tối đa **15** mẫu), `self.fps`.

### 5.3. `process_frame(frame_bgr, frame_index=0) -> (SOCFrameAnalysisResult, np.ndarray)`

```
now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

1. YOLO inference:  self.model(frame, conf=0.25, iou=0.45, device=..., verbose=False)[0]
                    → đo t_infer (ms)
2. detections = sv.Detections.from_ultralytics(results)
   tracked    = self.tracker.update_with_detections(detections)      → đo t_track (ms)
3. Lấy raw_kpts_data = results.keypoints.data.cpu().numpy()
   raw_boxes_xyxy  = results.boxes.xyxy.cpu().numpy()
4. Với mỗi (xyxy, mask, confidence, class_id, tracker_id, data) trong tracked:
      bỏ qua nếu tracker_id is None
      gán keypoint: tìm box gốc có IoU lớn nhất với box đã track (greedy O(n²)),
                    lấy 17 keypoint của box đó → List[KeypointCOCO]
      tạo HumanPoseTrack(track_id, bbox=(x1,y1,x2,y2), detection_conf, keypoints)
5. tracked_poses, telemetry, alerts = behavior_engine.update(raw_poses, time.time(), frame_idx)
                                                                      → đo t_beh (ms)
6. Tổng hợp threat: duyệt poses, chọn highest_threat theo rank {LOW:0, MEDIUM:1, HIGH:2, CRITICAL:3}
   critical_events: mọi pose HIGH/CRITICAL → "ID #{id} [{BEHAVIOR}]: {reasoning}"
7. Cập nhật FPS moving average 15 mẫu
8. Dựng SOCFrameAnalysisResult
9. annotated = draw_soc_hud_and_indicators(frame_bgr.copy(), analysis)
```

### 5.4. Vẽ — `draw_soc_hud_and_indicators()`

**Bảng màu BGR theo mức đe dọa (giữ nguyên mã màu):**

```python
LOW:      {"box": (0,220,0),   "bone": (0,255,127),  "joint": (0,255,0),   "label": (0,180,0)}
MEDIUM:   {"box": (0,215,255), "bone": (0,215,255),  "joint": (0,255,255), "label": (0,165,255)}
HIGH:     {"box": (0,120,255), "bone": (0,140,255),  "joint": (0,165,255), "label": (0,100,255)}
CRITICAL: {"box": (0,0,255),   "bone": (50,50,255),  "joint": (0,0,255),   "label": (0,0,220)}
```

Với mỗi `human`:
1. **Xương:** 16 cặp COCO, chỉ vẽ khi **cả hai** keypoint có `confidence > 0.25` **VÀ** `bone_len < max(50.0, 0.85 * hypot(bw, bh))` (chống nối xương sang người bên cạnh). Nét `2px`, `cv2.LINE_AA`.
2. **Khớp:** chấm đặc bán kính `3`, viền trắng bán kính `5` độ dày `1`.
3. **Bounding box góc vát** (`_draw_corner_box`): viền `1px`; `corner_len = min(20, max(8, int(min(w,h) * 0.15)))`; 4 góc × 2 nét, độ dày `2`.
4. **Nhãn header:** text `"ID #{id} | {BEHAVIOR} [{score*100}%]"`; nếu có `interacting_with_track_id` thì nối thêm `" vs #{id}"`. Nền `(15,15,15)` đặc, viền `box_color`, chữ trắng `FONT_HERSHEY_SIMPLEX 0.42`, đặt tại `(x1, y1-22)..(x1+tw+10, y1)`.

**HUD trên cùng (44 px):**
- Nền `(12,12,16)` alpha `0.78`, đường kẻ dưới `(55,55,65)`.
- Dòng 1 (y=18): `"URBAN SAFETY SOC | YOLO11-POSE + BYTETRACK + BEHAVIOR ENGINE"`, scale `0.40`, màu `(220,220,220)`.
- Dòng 2 (y=35): `"TIME: {timestamp}"`, scale `0.38`, màu cyan `(0,255,255)` — đây là **đồng hồ kiểm toán bắt buộc của SOC**.
- **Badge trạng thái** (phải):
  - `CRITICAL` → `"[ CRITICAL: {critical_events[0] hoặc 'EMERGENCY'} ]"`, đỏ `(0,0,255)`
  - `HIGH` → `"[ HIGH ALERT: {... hoặc 'SUSPICIOUS'} ]"`, cam `(0,140,255)`
  - `MEDIUM` → `"[ ELEVATED: {n} PERSON(S) MONITORED ]"`, vàng `(0,215,255)`
  - `LOW` → `"[ NORMAL: {n} PERSON(S) CLEAR ]"` nếu có người, `"[ CLEAR: NO ACTIVITY ]"` nếu không — xanh `(0,220,0)`
  - Cắt bớt còn 48 ký tự (`[:45] + "... ]"`).
- **Metrics** (y=38): `"FPS: {fps:.1f} | INFER: {infer:.0f}ms | BEH: {beh:.0f}ms"`, scale `0.33`, xám `(180,180,180)`.
- **Chỉ báo REC:** nếu `analysis.is_recording_evidence` → chấm đỏ bán kính `6` + chữ `"REC"` màu đỏ.

**Debug Alert Box (`_draw_debug_alert_box`)** — toggle bằng phím `d`:
- Kích thước **410 × 165 px**, đặt tại `(12, h - 165 - 12)` (góc dưới trái).
- Nền `(8,8,12)` alpha `0.85`, viền `(65,65,75)` 1px.
- Tiêu đề: `"[ DIAGNOSTIC TELEMETRY - TOGGLE 'd' ]"`, scale `0.38`, cyan; đường kẻ phân cách ở `y+24`.
- Nếu không có đối tượng: `"No subjects in field of view."` xám `(140,140,140)`.
- Ngược lại, tối đa **4** dòng, mỗi dòng `ID#{id}: Ang={spine:.0f}° | Spd={speed:.1f} | H/W={ar:.1f} | {BEHAVIOR}`, scale `0.34`, bước dòng `18px`, màu theo threat (đỏ / cam / vàng / xanh).
- Đường kẻ phân cách trên ticker, rồi dòng cuối: `"ALERT: {recent_alerts[0]}"` hoặc `"ALERT: STATUS: ALL MONITORED SUBJECTS STABLE"`, scale `0.33`, cắt còn 52 ký tự. Màu suy ra từ chuỗi: chứa `"CRITICAL"` → đỏ, chứa `"HIGH"` → vàng cam, còn lại xanh.

`close()` → giải phóng model/tracker, đóng `behavior_engine` (audit logger).

---

## 6. RECORDER BẰNG CHỨNG — `clip_recorder.py` → `src/<pkg>/io/evidence.py`

```python
EvidenceClipRecorder(
    output_dir: str = "output",
    fps: float = 20.0,
    frame_size: Tuple[int, int] = (640, 480),
    pre_roll_seconds: float = 1.5,
    post_roll_seconds: float = 2.0,
)
```

**Máy trạng thái:** `pre_roll_limit = int(fps * 1.5) = 30`, `post_roll_limit = int(fps * 2.0) = 40`.
`pre_roll_buffer = deque(maxlen=30)`.

`update(frame, is_human_present: bool, timestamp_str: str) -> Optional[str]`:

```
nếu is_human_present:
        nếu chưa ghi:  _start_recording(timestamp_str)
        writer.write(frame) ; clip_frame_count += 1 ; cooldown_counter = 0
ngược lại:
        nếu đang ghi (giai đoạn post-roll):
                writer.write(frame) ; clip_frame_count += 1 ; cooldown_counter += 1
                nếu cooldown_counter >= post_roll_limit: finalized = _finalize_clip(timestamp_str)
        ngược lại:
                pre_roll_buffer.append(frame.copy())
```

`_start_recording`: `event_counter += 1`, tên file `EVIDENCE_{YYYYmmdd_HHMMSS}_HUMAN.mp4`, fourcc `mp4v` @ `fps` & `frame_size`, **flush toàn bộ pre-roll buffer** vào file trước khi ghi frame hiện tại, in `">>> TRIGGERED RECORDING: {path}"`.

`_finalize_clip`: release writer, tính `duration = clip_frame_count / fps`, append vào `output/detection_events.jsonl`:

```json
{"event_id": "EVT-20261106221029-001", "type": "HUMAN_PRESENCE_DETECTED",
 "start_time": "...", "end_time": "...", "duration_seconds": 3.5,
 "frame_count": 70, "output_file": "/abs/path/output/EVIDENCE_....mp4"}
```
`event_id` dạng `EVT-{YYYYmmddHHMMSS}-{counter:03d}`. In `"<<< SAVED EVIDENCE CLIP: ..."`. Reset toàn bộ state.

`release()` → nếu đang ghi thì `_finalize_clip` với timestamp hiện tại.

> **Lưu ý khi viết lại:** trigger hiện tại là **`is_human_present` bất kỳ**, không phải mức đe dọa. README quảng cáo "trích xuất khi đạt mức đe dọa cao hoặc khẩn cấp" — **không đúng với code**. Xem mục 11.

---

## 7. ỨNG DỤNG — `camera_recorder.py` + `human_detection.py` + `main.py` → `src/<pkg>/apps/` + `cli.py`

### 7.1. `CameraRecorder` (live)

```python
CameraRecorder(
    camera_index: int = 0,
    resolution: Tuple[int, int] = (640, 480),
    record_full_session: bool = True,
    auto_extract_evidence: bool = True,
    model_weights: str = "yolo11n-pose.pt",
    device: Optional[str] = None,
    min_confidence: float = 0.25,
    output_dir: str = "output",
    records_dir: str = "records",
)
```

- Đường dẫn tương đối được resolve theo `dirname(abspath(__file__))`, tạo thư mục nếu thiếu.
- Mở camera: `cv2.VideoCapture(index, cv2.CAP_DSHOW)` trước (Windows), nếu không mở được thì `cv2.VideoCapture(index)`. Đọc `CAP_PROP_FRAME_WIDTH/HEIGHT` thực tế; nếu `<= 0` dùng `resolution`. Lưu `self.frame_size = (actual_w, actual_h)`.
- Không mở được camera → in cảnh báo, chuyển sang **luồng giả lập** (`_generate_simulated_frame`): nền xám `35`, lưới 40px màu `(45,45,50)`, chữ `"SIMULATED CAMERA STREAM - NO PHYSICAL WEBCAM ATTACHED"` màu `(0,180,255)`.
- Khởi tạo `YOLOPoseDetector(model_path, device, conf_threshold=min_confidence, fps=20.0)`; lỗi → fallback `PoseSkeletonDetector(min_detection_confidence=..., min_tracking_confidence=..., max_humans=10, model_complexity=1)`.
- `EvidenceClipRecorder(output_dir, fps=20.0, frame_size, pre_roll_seconds=1.5, post_roll_seconds=2.0)`.
- Ghi toàn phiên: `records/SESSION_{YYYYmmdd_HHMMSS}_FULL.mp4`, `mp4v` @ 20 fps, `frame_size`.
- `self.show_skeleton = True`.

**Vòng lặp `record_video()`:** cửa sổ `"Urban Safety AI-SOC: Human Behavior & Pose Monitor"` (`WINDOW_NORMAL`). Mỗi frame:
1. `analysis, display_frame = detector.process_frame(frame, frame_idx)` nếu `show_skeleton`, ngược lại dùng frame gốc và `analysis=None`.
2. `is_human = analysis.has_human`.
3. `analysis.is_recording_evidence = evidence_recorder.is_recording` (trước khi ghi evidence để cờ REC phản ánh frame hiện tại).
4. `saved = evidence_recorder.update(display_frame, is_human, now_str)`; nếu có → in `"[CameraRecorder] Evidence clip finalized: {path}"`.
5. `session_writer.write(display_frame)` nếu đang bật.
6. `cv2.imshow(...)`; `cv2.waitKey(1) & 0xFF`.

**Phím tắt (giữ nguyên):**

| Phím | Hành động | Thông báo terminal |
| :-: | :--- | :--- |
| `q` | Thoát, finalize mọi recording | `"[CameraRecorder] Stopping camera recorder..."` |
| `s` | Lưu snapshot `output/snapshot_{YYYYmmdd_HHMMSS}.jpg` (ảnh đã annotate) | `"[CameraRecorder] Snapshot saved: {path}"` |
| `h` | Bật/tắt toàn bộ overlay (skeleton + HUD) | `"[CameraRecorder] HUD overlay: ON/OFF"` |
| `d` | Bật/tắt Debug Alert Box (gọi `detector.toggle_debug_box()`, có `hasattr` guard) | `"[CameraRecorder] Diagnostic Alert Box Debug: ON/OFF"` |
| `r` | Bật/tắt ghi toàn phiên (release writer hoặc `_start_session_recorder()`) | `"[CameraRecorder] Continuous session recording stopped."` |

Toàn bộ vòng lặp trong `try/finally` → `cleanup()`: release camera, release writer, `evidence_recorder.release()`, đóng detector, `cv2.destroyAllWindows()`.
Banner khởi động in đủ 5 hotkey ra terminal.

### 7.2. `BatchHumanDetector` (offline)

```python
BatchHumanDetector(
    records_dir: str = "records",
    output_dir: str = "output",
    model_weights: str = "yolo11n-pose.pt",
    device: Optional[str] = None,
    annotate_output: bool = True,
)
```

- Quét `records/` lấy file có đuôi `.mp4 .avi .mov .mkv .wmv` (case-insensitive). Không có → in thông báo, trả `[]`.
- `process_single_video(path)`:
  - Đọc `total_frames`, `fps`; **nếu `fps <= 0` hoặc `fps > 120` thì ép về 20.0**; đọc `width`, `height`.
  - Lặp frame, `process_frame(frame, frame_idx)`, lấy `annotated_frame` nếu `annotate_output`.
  - Có người → gom frame vào segment, đồng thời gom nhãn `h.behavior.primary_behavior.value`; log tiến độ mỗi 30 frame: `"  Frame {i}/{total} ({pct:.0f}%) -> {n} human(s) | Threat: {level}"`.
  - Không còn người → chốt segment: nhãn trội = `Counter(...).most_common(1)`, tên file `"{video_basename}_seg{n}_{DOMINANT}.mp4"`, ghi bằng `cv2.VideoWriter` `mp4v` @ fps gốc & `(width, height)`, in `"  -> Extracted incident segment: {name} ({n} frames)"`.
  - Flush segment cuối nếu video kết thúc khi vẫn còn người.
  - Tổng kết: `"[BatchHumanDetector] Done: Extracted {n} incident segment(s) to {output_dir}/"`.

### 7.3. CLI `main.py`

```
python main.py --mode live|batch [--camera N] [--weights W] [--device D]
               [--record-all] [--records-dir DIR] [--output-dir DIR] [--conf-thresh F]
```

| Flag | Mặc định | Ý nghĩa |
| :--- | :--- | :--- |
| `--mode` | `live` | `live` = camera thời gian thực; `batch` = quét video trong `records/` |
| `--camera` | `0` | Chỉ số thiết bị camera |
| `--weights` | `yolo11n-pose.pt` | File trọng số YOLO11-Pose |
| `--device` | `None` | `cpu`, `cuda`, hoặc auto |
| `--record-all` | `False` | Ghi toàn bộ phiên live vào `records/` |
| `--records-dir` | `records` | Thư mục video đầu vào batch |
| `--output-dir` | `output` | Nơi lưu clip + snapshot + log |
| `--conf-thresh` | `0.25` | Ngưỡng tin cậy phát hiện |

Banner in ra trước khi chạy (Mode / Weights / Device / Conf Thresh / Output Dir), dùng `argparse.RawTextHelpFormatter`.

---

## 8. FALLBACK ENGINE — `pose_detector.py` → `src/<pkg>/detection/mediapipe_pose.py`

Chỉ chạy khi YOLO/ByteTrack khởi tạo thất bại. Phải giữ nguyên hành vi vì nó là lưới an toàn.

- **MediaPipe 33 landmark**, tên theo thứ tự chuẩn (`NOSE, LEFT_EYE_INNER, ... RIGHT_FOOT_INDEX`).
- **Bộ xương 33 landmark**: thân `(11,12)(11,23)(12,24)(23,24)`; tay trái `(11,13)(13,15)(15,17)(15,19)`; tay phải `(12,14)(14,16)(16,18)(16,20)`; chân trái `(23,25)(25,27)(27,29)(29,31)`; chân phải `(24,26)(26,28)(28,30)(30,32)`; mặt `(0,1)(1,2)(2,3)(3,7)(0,4)(4,5)(5,6)(6,8)(9,10)`.
- **6 bảng màu người** (BGR), gán theo `(track_id - 1) % 6`:
  `CYAN (0,255,255)/(0,255,0)/(0,255,127)`, `ORANGE (0,140,255)/(0,215,255)/(0,165,255)`, `MAGENTA (255,0,255)/(255,105,180)/(255,0,255)`, `BLUE (255,215,0)/(0,255,255)/(255,191,0)`, `GREEN (50,205,50)/(124,252,0)/(0,255,0)`, `RED (80,80,255)/(0,215,255)/(0,69,255)` (thứ tự: bone / joint / box).
- **URL model** (tự tải về `models/` khi thiếu):
  `.../pose_landmarker_full/float16/1/pose_landmarker_full.task`,
  `.../pose_landmarker_lite/float16/1/pose_landmarker_lite.task` (base `https://storage.googleapis.com/mediapipe-models/pose_landmarker/`).
  Ưu tiên `full` nếu tồn tại và `> 1000` byte; thử tải `full`, lỗi thì tải `lite`.
- `PoseLandmarkerOptions(num_poses=max_humans, min_pose_detection_confidence=..., min_pose_presence_confidence=..., min_tracking_confidence=..., output_segmentation_masks=False)`.
- Lỗi toàn bộ MediaPipe → `use_hog_fallback`, dùng `cv2.HOGDescriptor` + `getDefaultPeopleDetector()`, `detectMultiScale(gray, winStride=(8,8), padding=(4,4), scale=1.05)`.
- **NMS khử bóng ma:** sắp xếp giảm dần theo `confidence * số_keypoint_visible`; loại nếu `IoU > 0.50` với box đã nhận **hoặc** khoảng cách tâm `< 0.25 * min_dim`.
- **Tracker nội bộ `MultiPersonTracker(max_disappeared=12)`:** greedy matching chi phí `0.65*(1 - IoU) + 0.35*min(2.0, dist/diag)`; ngưỡng chấp nhận `0.85`; giữ ID cho track biến mất ≤ 12 frame.
- **Kiểm chứng giải phẫu khi vẽ:** keypoint phải nằm trong bbox mở rộng `margin_x = max(25, 30% bw)`, `margin_y = max(30, 30% bh)`; độ dài xương `< max(40.0, 0.70 * hypot(bw, bh))`.
- `_estimate_posture()`: nếu có hip/knee/ankle → `"Sitting"` khi `|knee_y - hip_y| < 0.45 * |ankle_y - knee_y|`, ngược lại `"Standing"`; thiếu điểm → `"Observed"`.
- HUD riêng: thanh 42px, tiêu đề `"URBAN SAFETY SOC | MULTI-PERSON SKELETON DETECTOR"`, clock `"TIME: {timestamp}"`, badge `"[ ALERT: {n} HUMAN(S) DETECTED ]"` (cam đậm nếu `>1`) hoặc `"[ MONITORING: CLEAR ]"`, metrics `"FPS: {fps:.1f} | INFER: {ms:.1f}ms"`, chỉ báo REC.

---

## 9. BỘ TEST — `test_system.py` → `tests/` (pytest)

Hiện tại là script `print` + `assert`, chạy `python test_system.py`, in `"[TEST n/7]"`. **Bảy bài test phải được bảo toàn ngữ nghĩa** và chuyển thành `pytest`:

1. **`test_models`** — khởi tạo `KeypointCOCO`, `BehaviorPrediction`, `HumanPoseTrack`, `SOCFrameAnalysisResult`, kiểm `has_human`, `posture_label == "NORMAL"`; đồng thời kiểm schema legacy (`Keypoint`, `HumanPose`, `FrameAnalysisResult`).
2. **`test_behavior_rules`** — 5 kịch bản với skeleton tổng hợp (helper `_create_synthetic_pose(track_id, bbox, spine_mode ∈ {upright, fallen, crouching}, wrists_mode ∈ {normal, hands_up, fighting}, speed)`); feed 15 frame @ 50ms:
   - upright → `NORMAL` / `LOW`
   - fallen → `FALLEN` / `CRITICAL` / `score >= 0.90`
   - hands_up → `HANDS_UP` / `HIGH`
   - dịch chuyển 45px/frame → `RUNNING` / `HIGH`
   - hai người sát nhau, cổ tay dao động ±40px so le → `FIGHTING` / `CRITICAL`
   - (Luật `CROUCHING` và `LOITERING` hiện **chưa có test** — khi viết lại phải bổ sung.)
3. **`test_anti_flapping_and_stabilization`** — 6 frame `NORMAL`; chèn **2 frame nhiễu** `FALLEN` → **vẫn phải giữ `NORMAL`**; sau đó 10 frame `FALLEN` thật → phải commit `FALLEN`/`CRITICAL`; kiểm `smooth bbox` hợp lệ (`x2 > x1`, `y2 > y1`).
4. **`test_audit_logger`** — `output/behavior_events.jsonl` và `output/behavior_audit.log` tồn tại; parse từng dòng JSON; entry cuối phải có đủ trường `event_id, timestamp, frame_index, track_id, event_type, current_behavior, threat_level, telemetry`.
5. **`test_evidence_clip_recorder`** — pre-roll 25 frame không người → 30 frame có người → 25 frame không người; clip được finalize, file tồn tại, kích thước `> 0`.
6. **`test_yolo_pose_pipeline_and_debug_hud`** — `process_frame` trên frame xám 480×640 trả `SOCFrameAnalysisResult`, shape `(480,640,3)`, có `telemetry_list`/`recent_alerts`; `show_debug_box` mặc định `True`; `toggle_debug_box()` → `False` → `True`.
7. **`test_camera_hardware`** — thử mở camera 0 (DSHOW rồi mặc định), đọc 1 frame, **không bao giờ fail** nếu không có phần cứng (chỉ in thông báo).

**Yêu cầu khi viết lại:** (a) unit test **không được tải model YOLO/MediaPipe** — dùng stub/fake detector; (b) tất cả ghi file vào `tmp_path` của pytest, không ghi vào `output/` thật; (c) test phải tất định, không phụ thuộc mạng; (d) thêm test cho `CROUCHING`, `LOITERING`, cho debounce `exit=12` (quay về NORMAL), và cho việc **FIGHTING cũng đi qua debounce + tạo audit event** (đặc tả mục 11.2).

---

## 10. ARTIFACT VÀ ĐỊNH DẠNG OUTPUT (giữ nguyên)

**Cây thư mục runtime:**
```
records/     # video đầu vào batch + SESSION_*_FULL.mp4 ghi từ live
output/      # EVIDENCE_*_HUMAN.mp4, snapshot_*.jpg, behavior_events.jsonl, behavior_audit.log, detection_events.jsonl
models/      # pose_landmarker_lite.task (5.5 MB, cache sẵn)
```

**Mẫu `output/behavior_events.jsonl` thực tế (giữ nguyên khoá JSON):**
```json
{"event_id": "EVT_20261106_221028_2", "timestamp": "2026-11-06 22:10:28.809", "frame_index": 5, "track_id": 2, "event_type": "CRITICAL_ALERT", "previous_behavior": "NORMAL", "current_behavior": "FALLEN", "threat_level": "CRITICAL", "threat_score": 0.98, "telemetry": {"spine_angle": 90.0, "aspect_ratio": 0.32, "speed": 0.0, "wrist_velocity": 0.0}, "reasoning": "Torso angle 90° (>= 55°) or H/W 0.32 horizontal", "dwell_time_seconds": 0.25}
```

**Mẫu `output/behavior_audit.log`:**
```
[2026-11-06 22:10:28.809] [CRITICAL_ALERT] ID #2: NORMAL -> FALLEN (CRITICAL 98%) | Spine:90° Spd:0.00 | Reason: Torso angle 90° (>= 55°) or H/W 0.32 horizontal
[2026-11-06 22:10:28.812] [THREAT_ESCALATION] ID #3: NORMAL -> HANDS_UP (HIGH 78%) | Spine:0° Spd:0.00 | Reason: Both hands raised above head in distress / surrender gesture
```

Các loại `event_type` được ghi nhận: `TRACK_INITIALIZED`, `STATE_TRANSITION`, `THREAT_ESCALATION`, `CRITICAL_ALERT`, `HEARTBEAT_ALERT`.

**`.gitignore` hiện tại** loại trừ: `__pycache__/`, `*.py[cod]`, `venv/`, `.venv/`, `*.weights`, `*.onnx`, `*.task`, `*.pt`, `*.mp4`, `*.avi`, `*.mov`, `*.mkv`, `*.wmv`, `*.webm`, `*.jpg`, `*.jpeg`, `*.png` (trừ `!*.gitkeep`), `HUMAN DETECT/output/*` (trừ `.gitkeep`), `HUMAN DETECT/records/*` (trừ `.gitkeep`), `*.log`, `detection_events.jsonl`, `.vscode/`, `.idea/`, `Thumbs.db`, `Desktop.ini`, `.DS_Store`, **và cuối cùng là `*.md`**. Vấn đề: `*.md` chặn cả tài liệu dự án; `models/pose_landmarker_lite.task` vẫn bị track vì được add trước khi có ignore rule.

---

## 11. CÁC LỖI / BẤT NHẤT ĐÃ XÁC ĐỊNH — PHẢI SỬA KHI VIẾT LẠI

Mỗi mục dưới đây là lỗi thực tế đọc được từ code, không phải phỏng đoán. Viết lại phải sửa, và ghi rõ trong `PLAN.md` là thay đổi có chủ đích.

**11.1. `output_dir` không được truyền xuống detector.**
`main.py` nhận `--output-dir` và truyền cho `CameraRecorder`/`BatchHumanDetector`, nhưng cả hai đều khởi tạo `YOLOPoseDetector(...)` **không truyền `output_dir`** → audit log luôn rơi vào `output/` tương đối theo CWD, bỏ qua flag. Đây chính là lý do tồn tại `Hackathon-Test-/output/behavior_events.jsonl` (199 KB) **nằm ngoài thư mục dự án**. → Truyền xuyên suốt, resolve về absolute path.

**11.2. FIGHTING ghi đè state machine.**
`_analyze_multi_person_interactions()` chạy sau khi `pose.behavior` đã được debounce và gán, rồi gán đè — nhãn có thể nhấp nháy 1 frame, không qua hysteresis, không sinh audit event. → Đưa FIGHTING vào cùng pipeline quyết định (raw prediction ưu tiên cao nhất) để mọi transition đều qua debounce + log.

**11.3. Bằng chứng clip kích hoạt sai điều kiện.**
`clip_recorder` ghi clip khi **có bất kỳ người nào**, trong khi README/SPEC nói "khi đạt mức đe dọa cao hoặc khẩn cấp". Hệ quả: camera đông người sẽ ghi gần như liên tục, làm đầy `output/`. → Thêm policy cấu hình được: `evidence_trigger ∈ {HUMAN_PRESENCE, THREAT_THRESHOLD}` với ngưỡng mặc định `HIGH`, và cooldown giữa các clip.

**11.4. HUD dùng toạ độ tuyệt đối, vỡ bố cục.**
`_draw_hud_dashboard` đặt badge tại `w - 550` và metrics tại `w - 180`; với khung 640 px badge bắt đầu ở x=90 và metrics bị cắt mép; với 4K thì badge lơ lửng giữa màn hình. Debug box cũng cố định `410×165` và luôn ở góc dưới trái, có thể che chính đối tượng. → Toàn bộ layout tính theo tỉ lệ `w`, `h`, có clamp, có scale font theo độ phân giải.

**11.5. Batch mode nạp toàn bộ segment vào RAM.**
`segment_frames: List[np.ndarray]` giữ mọi frame của một segment cho tới khi người biến mất. Video 1080p, người xuất hiện 2 phút @ 30 fps ≈ 3600 frame × 6 MB ≈ 21 GB → OOM. → Ghi trực tiếp ra file tạm bằng `VideoWriter` khi vào segment, không buffer frame trong RAM.

**11.6. Batch mode bỏ qua `--conf-thresh`.**
`main.py` không truyền `args.conf_thresh`, `BatchHumanDetector` hard-code `conf_threshold=0.25`. → Truyền xuống.

**11.7. `record_full_session` mặc định mâu thuẫn.**
Class mặc định `True`, nhưng `main.py` truyền `record_all=False` mặc định → hành vi phụ thuộc entrypoint. Đồng thời `README.md` nói "Ghi toàn bộ phiên làm việc... khi có `--record-all`", khớp với `main.py`. → Chuẩn hoá mặc định `False` ở mọi nơi và cập nhật docstring.

**11.8. Hai quy ước bounding box.**
`HumanPoseTrack.bbox = (x1,y1,x2,y2)` nhưng `HumanPose.bbox = (x,y,w,h)`. `compute_xyxy_iou` nhận `xyxy`, `compute_box_iou` nhận `xywh`. Bất kỳ nhầm lẫn nào cũng sinh bug im lặng. → Type `BBox` có tên trường + hàm chuyển đổi tường minh.

**11.9. Nuốt lỗi im lặng, trái CD-05.**
`BehaviorAuditLogger.close()` có `except Exception: pass`; `_init_yolo_and_bytetrack` bắt `Exception` rộng rồi chỉ in; import fallback bọc `except Exception` không log nguyên nhân. `AGENTS.md` [CD-05] cấm `silent catch/pass` che giấu sự cố mô hình. → Dùng module `logging` chuẩn, log kèm `exc_info=True`, và phơi trạng thái degraded (`use_fallback`) lên HUD/health check.

**11.10. `requirements.txt` thiếu `mediapipe`.**
Nhánh fallback `pose_detector.py` sẽ luôn hỏng trên máy cài mới. → Bổ sung.

**11.11. Test suite là script, không phải test.**
Không có `pytest`, không có fixture, chạy tuần tự bằng `print`, ghi rác vào `output/` thật (bằng chứng: 2 file `EVIDENCE_*.mp4` 30.4 KB sinh ra bởi test 5), thời gian chạy phụ thuộc tải model từ mạng. → pytest + fixture + `tmp_path` + stub detector.

**11.12. `HumanIncidentClip` là code chết.**
Được định nghĩa nhưng không được khởi tạo ở đâu. Trong khi đó batch mode sinh clip mà không ghi metadata sự cố nào (không dùng `detection_events.jsonl`). → Dùng nó cho batch (ghi metadata mỗi segment) hoặc xoá.

**11.13. Đồng hồ HUD là wall-clock.**
`now_str = datetime.now()` dùng cho cả live và batch → clip batch mang timestamp thời điểm render, không phải thời điểm trong video. Vi phạm mục đích kiểm toán. → Live dùng wall-clock (đúng), batch dùng `frame_idx / fps` + thời điểm bắt đầu video, và ghi rõ nguồn thời gian trong `SOCFrameAnalysisResult`.

**11.14. Cấu trúc repo bẩn.**
File rác ở root (`hello.md`, `te`, `test`, `tett`), weights `yolo11n-pose.pt` 6 MB ở root (đúng ra phải ở `models/`), `output/` rò rỉ ra root, `AGENTS.md` bị xoá khỏi working tree nhưng còn trong HEAD. Tên thư mục có dấu cách.

**11.15. Import dư và state không dùng.**
`pose_detector.py` gán `self.mp = mp` rồi dùng `self.mp.Image`; `human_detection.py` import `datetime`, `argparse` chỉ dùng trong `__main__`; `yolo_pose_detector.py` import `os`, `sys` không dùng; `camera_recorder.py` `argparse` chỉ cho `__main__`. → Dọn theo linter.

---

## 12. CẤU TRÚC ĐÍCH BẮT BUỘC

Tên package lấy là `urbansoc` (không dấu, không khoảng trắng).

```
human-detect/
├── pyproject.toml               # metadata, deps, extras [dev], entry-point "urbansoc", config [tool.pytest.ini_options]
├── requirements.txt             # giữ cho tương thích; đồng bộ với pyproject
├── README.md
├── AGENTS.md                    # khôi phục từ git HEAD (đang bị xoá ở working tree)
├── docs/
│   ├── SPEC.md                  # SPEC-BEHAVIOR-STABILIZATION-02
│   └── PLAN.md                  # PLAN-BEHAVIOR-STABILIZATION-02
├── configs/
│   └── default.yaml             # nạp vào EngineConfig / DetectorConfig / RenderConfig / RecorderConfig
├── src/urbansoc/
│   ├── __init__.py
│   ├── __main__.py              # python -m urbansoc
│   ├── cli.py                   # argparse, banner, dispatch — tương đương main.py
│   ├── config.py                # dataclass cấu hình + load từ YAML/CLI, thay thế các magic number rải rác
│   ├── domain/
│   │   ├── enums.py             # ThreatLevel, BehaviorType
│   │   ├── geometry.py          # BBox (named fields), iou_xyxy, bbox_from_xywh, bbox_to_xywh, corner-box helper
│   │   ├── keypoints.py         # hằng số COCO-17, tên, cặp xương; hằng số MediaPipe-33, tên, cặp xương
│   │   └── schemas.py           # toàn bộ dataclass ở mục 3
│   ├── detection/
│   │   ├── base.py              # Protocol PoseDetector: process_frame(frame, idx) -> (Analysis, ndarray); close()
│   │   ├── yolo_pose.py         # YOLOPoseDetector (mục 5)
│   │   └── mediapipe_pose.py    # PoseSkeletonDetector + MultiPersonTracker (mục 8)
│   ├── behavior/
│   │   ├── kinematics.py        # _extract_state: spine angle, body/wrist velocity, EMA
│   │   ├── rules.py             # 6 luật thuần tuý (pure function) — dễ test riêng từng luật
│   │   ├── interactions.py      # phân tích cặp đôi FIGHTING (đưa vào làm raw prediction, xem 11.2)
│   │   ├── state_machine.py     # HysteresisDebouncer: candidate streak, enter/exit, fast-track
│   │   └── engine.py            # BehaviorEngine điều phối + trả telemetry + recent_alerts
│   ├── telemetry/
│   │   └── audit_logger.py      # BehaviorAuditLogger (JSONL + text, flush)
│   ├── io/
│   │   ├── sources.py           # CameraSource | VideoFileSource | SimulatedSource — cùng interface read()
│   │   └── evidence.py          # EvidenceClipRecorder
│   ├── render/
│   │   ├── theme.py             # THREAT_COLORS, PERSON_PALETTES, hằng số font/scale
│   │   ├── skeleton.py          # vẽ xương + khớp + corner box, có gate độ dài xương
│   │   └── hud.py               # top HUD dashboard + Debug Alert Box (layout theo tỉ lệ)
│   └── apps/
│       ├── live.py              # CameraRecorder — vòng lặp, hotkey, session writer
│       └── batch.py             # BatchHumanDetector — streaming writer, không buffer RAM
├── tests/
│   ├── conftest.py              # fixture: synthetic_pose factory, fake detector, tmp output dir
│   ├── test_schemas.py
│   ├── test_rules.py            # 7 hành vi, gồm CROUCHING + LOITERING
│   ├── test_state_machine.py    # debounce enter/exit, fast-track FALLEN/FIGHTING, noise rejection
│   ├── test_interactions.py     # FIGHTING qua debounce + audit event (đặc tả 11.2)
│   ├── test_audit_logger.py     # JSONL + text format, flush
│   ├── test_evidence.py         # rolling buffer, pre/post roll, cooldown
│   ├── test_render.py           # HUD + debug box render không lỗi ở 640×480, 1280×720, 1920×1080
│   └── test_pipeline_smoke.py   # pipeline với fake detector, không cần model
├── models/                      # .task cache; *.pt tự tải vào đây; gitignored
├── records/.gitkeep
└── output/.gitkeep
```

**Nguyên tắc phân lớp bắt buộc:**
- `domain/` **không import** bất kỳ module nào khác trong package, không import cv2/torch/ultralytics.
- `behavior/` chỉ phụ thuộc `domain/` + `telemetry/`.
- `render/` chỉ phụ thuộc `domain/`, nhận dữ liệu đã tính, **không gọi model**.
- `detection/` phụ thuộc `domain/` + `behavior/`.
- `apps/` là lớp duy nhất được phép biết về camera, GUI, đĩa.
- Không có vòng import. Không có global mutable state ngoài hằng số.

---

## 13. YÊU CẦU CHẤT LƯỢNG VÀ RÀNG BUỘC KỸ THUẬT

1. **Hiệu năng:** I/O log ≤ 0.5 ms/lần ghi (line-buffered, flush mỗi entry). Vòng lặp live phải giữ ≥ 20 FPS trên CPU với `yolo11n-pose` ở 640×480.
2. **Non-blocking ingestion (bắt buộc theo `AGENTS.md` §3.1):** tách luồng đọc frame khỏi luồng inference bằng hàng đợi hoặc ring buffer. Code hiện tại đọc và infer tuần tự trong cùng vòng lặp — **đây là khoảng trống phải lấp** khi viết lại. Tối thiểu: `threading.Thread` cho frame grabber + `queue.Queue(maxsize=2)` drop-oldest, để camera không bị block khi model chậm.
3. **Không silent catch.** Mọi `except` phải log kèm ngữ cảnh; không `pass` trần.
4. **Type hints** đầy đủ trên toàn bộ API công khai. Chạy được `mypy --ignore-missing-imports` không lỗi nghiêm trọng.
5. **Docstring** tiếng Anh cho module/class/hàm công khai; comment nghiệp vụ có thể tiếng Việt (giữ phong cách hiện tại).
6. **Logging** qua `logging` module với logger theo namespace `urbansoc.*`, không dùng `print` trong thư viện (chỉ CLI/UI được `print`).
7. **Không đổi tên khoá JSON, tên hành vi, tên mức đe dọa, mã event_type** — đây là contract kiểm toán.
8. **Không thêm dependency ngoài danh sách mục 2** trừ khi có lý do ghi trong `PLAN.md`. Không dùng `ffmpeg` binary.
9. **Đường dẫn** luôn resolve tuyệt đối từ vị trí package, không phụ thuộc CWD.
10. **Tài liệu phải khớp code.** Mọi tuyên bố trong `README.md` phải kiểm chứng được bằng code (đặc biệt: điều kiện trigger clip bằng chứng, mặc định `--record-all`, sự tồn tại của `--conf-thresh` trong batch).

---

## 14. TIÊU CHÍ NGHIỆM THU (DEFINITION OF DONE)

Việc viết lại chỉ được coi là hoàn thành khi **tất cả** điều sau đúng:

- [ ] `pip install -e ".[dev]"` chạy sạch trên Python 3.10+.
- [ ] `pytest -q` xanh toàn bộ, **không tải model**, **không cần camera**, chạy < 30 giây.
- [ ] `python -m urbansoc --help` liệt kê đủ 8 flag ở mục 7.3 với mặc định đúng.
- [ ] `python -m urbansoc --mode live --camera 0` chạy được; 5 hotkey `q s h d r` hoạt động đúng mô tả; không có camera thì vào luồng giả lập thay vì crash.
- [ ] `python -m urbansoc --mode batch` quét `records/`, sinh tên file `{video}_seg{n}_{BEHAVIOR}.mp4`, chạy hết video *không tăng RAM tuyến tính theo độ dài video*.
- [ ] `output/behavior_events.jsonl` mỗi dòng là JSON hợp lệ, có đủ 12 khoá ở mục 3.2, đúng định dạng `event_id`/`timestamp`.
- [ ] `output/behavior_audit.log` đúng định dạng dòng ở mục 4.2.
- [ ] `output/detection_events.jsonl` ghi đủ 7 khoá ở mục 6.
- [ ] 7 hành vi đều phân loại được trên skeleton tổng hợp, đúng threat level/score như bảng mục 4.7.
- [ ] Nhiễu 2 frame không làm nhảy nhãn; 10 frame liên tục làm commit đúng; `FALLEN`/`FIGHTING` fast-track ở 6 frame; trở về `NORMAL` cần 12 frame.
- [ ] FIGHTING sinh audit event và không nhấp nháy 1 frame.
- [ ] `--output-dir` tác động **thực sự** tới vị trí audit log (không còn rò rỉ ra CWD).
- [ ] HUD không tràn/không chồng ở 640×480, 1280×720, 1920×1080.
- [ ] Không còn `except: pass`; module `logging` được dùng; trạng thái degraded được báo ra ngoài.
- [ ] `grep -rn "print(" src/urbansoc` không trả về gì ngoài `cli.py` và `apps/`.
- [ ] `docs/SPEC.md`, `docs/PLAN.md` được cập nhật phản ánh cấu trúc mới, `AGENTS.md` được khôi phục.
- [ ] Root repo sạch: xoá `hello.md`, `te`, `test`, `tett`, `output/` rò rỉ, chuyển `yolo11n-pose.pt` vào `models/`; `.gitignore` sửa để không chặn `*.md` tài liệu và để `models/*.task` được ignore đúng.
- [ ] Git status sạch sau commit, `promt.md` này được giữ lại ở `docs/REBUILD_PROMPT.md` để truy vết.

---

## 15. DANH SÁCH CHỐNG BỎ SÓT (CHECKLIST ĐỐI CHIẾU)

Trước khi kết thúc, đối chiếu từng dòng — mỗi mục phải có chỗ đứng trong code mới:

**Schema:** `ThreatLevel` (4) · `BehaviorType` (7) · `KeypointCOCO` · `BehaviorPrediction` · `TrackHistoryState` · `TrackKinematicsTelemetry` · `BehaviorAuditLogEntry` · `HumanPoseTrack` (+2 property) · `SOCFrameAnalysisResult` (+2 property) · `Keypoint` · `HumanPose` · `FrameAnalysisResult` · `HumanIncidentClip`.

**Hằng số:** COCO-17 (17 chỉ số + 17 tên + 16 cặp xương) · MediaPipe-33 (33 tên + 29 cặp xương) · `THREAT_COLORS` (4 mức × 4 khoá) · `PERSON_PALETTES` (6 bộ × 3 màu + tên) · 2 URL model · ngưỡng keypoint 0.25 · thread phase constants.

**Behavior:** `BehaviorAuditLogger` (2 file, 2 method) · `BehaviorEngine` (12 tham số) · meta 12 trường mỗi track · `update` · `_extract_state` (3 đại lượng) · `_analyze_single_track` (6 luật) · hysteresis (3 nhánh `req_streak`) · heartbeat · `_analyze_multi_person_interactions` (2 điều kiện) · dọn track 5.0 s · `recent_alerts` maxlen 5.

**Detection:** `YOLOPoseDetector` (9 tham số) · `_init_yolo_and_bytetrack` · `toggle_debug_box` · `process_frame` (9 bước) · `draw_soc_hud_and_indicators` (6 lớp vẽ) · `_draw_corner_box` · `_draw_hud_dashboard` (6 thành phần) · `_draw_debug_alert_box` (4 khối) · FPS moving average 15 · `close`.

**Fallback:** `LANDMARK_NAMES` · `SKELETON_PAIRS` · `PERSON_PALETTES` · `MODEL_URL_FULL/LITE` · `compute_box_iou` · `MultiPersonTracker` (ngưỡng 0.85, max_disappeared 12) · `PoseSkeletonDetector` (4 tham số) · `_init_mediapipe_landmarker` (download logic) · HOG fallback · `_filter_duplicate_poses` (2 điều kiện) · `_is_point_near_box` · `_is_valid_bone_segment` · `_draw_sleek_bounding_box` · `_draw_hud_dashboard` · `_estimate_posture` · `close`.

**IO:** `EvidenceClipRecorder` (5 tham số) · pre/post roll · `update` (3 nhánh) · `_start_recording` (flush pre-roll) · `_finalize_clip` (JSON event) · `release`.

**Apps:** `CameraRecorder` (9 tham số) · camera open DSHOW→default · frame_size thực tế · simulated frame · session writer · `record_video` (6 bước) · 5 hotkey · `cleanup` · `BatchHumanDetector` (5 tham số) · `process_all_videos` (5 đuôi file) · `process_single_video` (fps guard, segment, Counter, progress) · `_save_frames_to_video` · `main.py` (8 flag, banner, dispatch).

**Test:** 7 bài (mục 9) + `_create_synthetic_pose` (3 chế độ spine × 3 chế độ wrist).

**Docs & quy trình:** `README.md` (5 nhóm tính năng, bảng hotkey, 3 chế độ chạy, cây thư mục) · `SPEC.md` (SPEC-BEHAVIOR-STABILIZATION-02, schema, 2 sơ đồ Mermaid, đặc tả Debug HUD, 3 test bổ sung) · `PLAN.md` (PLAN-BEHAVIOR-STABILIZATION-02, file manifest, function signatures, 5 test) · `AGENTS.md` (CD-01..CD-05, 4 bước SDD với gate labels `[WAITING FOR SPEC APPROVAL]` / `[WAITING FOR PLAN APPROVAL]`, 4 tầng kiến trúc, RFC protocol).

---

## 16. QUY TRÌNH THỰC HIỆN (theo `AGENTS.md`)

1. **Stage 1 — SPEC:** cập nhật `docs/SPEC.md` mô tả kiến trúc module mới + mapping cũ→mới + các sửa lỗi mục 11. Kết thúc bằng `[WAITING FOR SPEC APPROVAL]` và dừng.
2. **Stage 2 — PLAN:** sau khi con người duyệt, cập nhật `docs/PLAN.md`: file manifest (tạo/sửa/xoá), chữ ký hàm, dependency, kế hoạch test từng bước. Kết thúc bằng `[WAITING FOR PLAN APPROVAL]` và dừng.
3. **Stage 3 — REVIEW:** đóng băng sinh code, chờ từ khoá duyệt (`Approved` / `Duyệt` / `Proceed to code` / `Triển khai theo plan`).
4. **Stage 4 — CODE & VERIFY:** viết code đúng plan, chạy `pytest`, chạy thử live + batch, đối chiếu checklist mục 15, báo cáo kết quả. Không tiện tay refactor file ngoài manifest. Gặp rào cản → dừng và gửi RFC theo mẫu trong `AGENTS.md` §4.2.

**Ràng buộc nghiệp vụ không được vi phạm:** không thêm bất kỳ nhánh nào cho phép hệ thống tự động gửi cảnh báo tới cơ quan chức năng mà bỏ qua bước `OPERATOR_CONFIRMED` (CD-04). Tầng 4 vẫn nằm ngoài phạm vi lần viết lại này.
