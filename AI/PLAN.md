# KẾ HOẠCH TRIỂN KHAI: PHÂN HỆ THU NHẬN VIDEO, YOLO11-POSE & BỘ ĐỆM BẰNG CHỨNG (AI/)
**Mã tài liệu:** `PLAN-URBAN-AI-PIPELINE-01`  
**Dự án:** Hệ thống Giám sát An ninh & An toàn Đô thị Thông minh (Urban Safety AI-SOC)  
**Phân hệ:** Tầng 1 (Input/Ingestion) & Tầng 2 (AI/Pose Analytics & SOC Visual Composer)  
**Căn cứ kỹ thuật:** Tuân thủ `AGENTS.md` (Stage 2 SDD) và `SPEC-URBAN-AI-PIPELINE-01`.  
**Trạng thái:** Chờ phê duyệt từ Lead Architect (`[WAITING FOR PLAN APPROVAL]`)

---

## 1. DANH MỤC TỆP TIN TRIỂN KHAI (FILE MANIFEST)

| Thao tác | Đường dẫn tệp | Trách nhiệm chính / Nội dung thực hiện |
| :--- | :--- | :--- |
| **Tạo mới** | `AI/stream_reader.py` | Lớp `AsyncVideoStreamReader`: Thu nhận luồng video đa nguồn (Webcam/RTSP/File) bằng luồng phụ bất đồng bộ, kèm bộ sinh khung hình giả lập `SimulatedFrameGenerator` làm dự phòng lỗi. |
| **Tạo mới** | `AI/pose_extractor.py` | Lớp `YOLOPoseExtractor`: Tích hợp mô hình `YOLO11n-Pose` và `Supervision ByteTrack` để trích xuất 17 khớp giải phẫu COCO, bảo toàn `track_id`, và làm mượt hộp bao qua bộ lọc EMA ($\alpha = 0.65$). |
| **Tạo mới** | `AI/kinematics_builder.py` | Lớp `KinematicsBuilder`: Tính toán góc nghiêng cột sống ($\theta_{\text{spine}}$), tỷ lệ $H/W$, vận tốc chuẩn hóa ($V_{\text{norm}}$), động năng cổ tay ($E_{\text{wrist}}$), đóng gói thành `SubjectKinematicsSnapshot`. |
| **Tạo mới** | `AI/evidence_buffer.py` | Lớp `EvidenceRollingBuffer`: Bộ đệm vòng 1.5s trước sự cố; tự động kích hoạt ghi hình và đóng gói video clip MP4 (kèm 2.0s hậu sự cố) ra `output/` bằng OpenCV native `VideoWriter`. |
| **Tạo mới** | `AI/visual_composer.py` | Lớp `SOCVisualComposer`: Soạn thảo và vẽ HUD lên từng khung hình (khung xương phân màu theo Threat Mark, hộp bao viền góc, thanh Dashboard SOC, đồng hồ kiểm toán, và bảng Alert Box Debug). |
| **Tạo mới** | `AI/pipeline.py` | Lớp điều phối trung tâm `UrbanSafetyAIPipeline`: Kết nối Stream Reader $\to$ Pose Extractor $\to$ Kinematics $\to$ `ThreatMarkingEngine` $\to$ Rolling Buffer $\to$ Visual Composer $\to$ `CloudflareSOCClient`. |
| **Tạo mới** | `AI/__init__.py` | Export module công khai cho phân hệ `AI/`. |
| **Tạo mới** | `test_ai_pipeline.py` | Kịch bản kiểm thử tự động toàn diện kiểm chứng thu nhận luồng, trích xuất đặc trưng động học, kích hoạt bộ đệm bằng chứng, và vẽ giao diện HUD. |

---

## 2. CHỮ KÝ HÀM & THIẾT KẾ CHI TIẾT (FUNCTION SIGNATURES)

### 2.1. Module `AI/stream_reader.py`
```python
from typing import Tuple, Optional
import numpy as np

class SimulatedFrameGenerator:
    def __init__(self, width: int = 640, height: int = 480) -> None: ...
    def generate(self, frame_index: int) -> np.ndarray: ...

class AsyncVideoStreamReader:
    def __init__(
        self,
        source: str = "0",               # "0" (Webcam), "rtsp://...", hoặc "video.mp4"
        target_resolution: Tuple[int, int] = (640, 480),
        target_fps: float = 20.0,
        use_simulated_fallback: bool = True
    ) -> None: ...

    def start(self) -> "AsyncVideoStreamReader": ...
    def read(self) -> Tuple[bool, np.ndarray, float]:
        """Trả về (ret, frame_bgr, timestamp) không gây nghẽn (non-blocking)."""
        ...
    def stop(self) -> None: ...
```

### 2.2. Module `AI/pose_extractor.py`
```python
from typing import List, Tuple, Dict, Optional, Any
import numpy as np

class YOLOPoseExtractor:
    def __init__(
        self,
        model_path: str = "yolo11n-pose.pt",
        device: Optional[str] = None,    # "cuda" hoặc "cpu"
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        bbox_ema_alpha: float = 0.65
    ) -> None: ...

    def extract_poses(
        self,
        frame_bgr: np.ndarray,
        frame_index: int
    ) -> Tuple[List[Dict[str, Any]], float]:
        """
        Trả về:
        1. Danh sách poses thô: track_id, bbox_smooth, keypoints_coco (17 khớp).
        2. Thời gian suy luận inference_time_ms.
        """
        ...
```

### 2.3. Module `AI/kinematics_builder.py`
```python
from Engine.threat_models import SubjectKinematicsSnapshot

class KinematicsBuilder:
    def __init__(self, fps: float = 20.0) -> None: ...

    def build_snapshot(
        self,
        raw_pose: Dict[str, Any],
        prev_snapshot: Optional[SubjectKinematicsSnapshot],
        timestamp: float
    ) -> SubjectKinematicsSnapshot:
        """Tính toán góc cột sống, vận tốc rơi hông, động năng cổ tay và đóng gói SubjectKinematicsSnapshot."""
        ...
```

### 2.4. Module `AI/evidence_buffer.py`
```python
class EvidenceRollingBuffer:
    def __init__(
        self,
        output_dir: str = "output",
        fps: float = 20.0,
        frame_size: Tuple[int, int] = (640, 480),
        pre_roll_seconds: float = 1.5,
        post_roll_seconds: float = 2.0
    ) -> None: ...

    def update(
        self,
        frame_bgr: np.ndarray,
        trigger_recording: bool,
        behavior_label: str = "INCIDENT",
        timestamp_str: Optional[str] = None
    ) -> Optional[str]:
        """
        Cập nhật bộ đệm và ghi file MP4 khi có sự kiện HIGH/CRITICAL.
        Trả về đường dẫn file video clip nếu vừa hoàn tất ghi hình.
        """
        ...
    def release(self) -> None: ...
```

### 2.5. Module `AI/visual_composer.py`
```python
from Engine.threat_models import SOCEngineOutput

class SOCVisualComposer:
    def __init__(self) -> None:
        self.show_debug_box: bool = True

    def toggle_debug_box(self) -> bool: ...

    def compose(
        self,
        frame_bgr: np.ndarray,
        engine_output: SOCEngineOutput,
        fps: float = 20.0,
        inference_time_ms: float = 0.0,
        is_recording: bool = False
    ) -> np.ndarray:
        """Vẽ toàn bộ HUD, khung xương phân màu, hộp bao viền góc, đồng hồ và Alert Box Debug."""
        ...
```

### 2.6. Module `AI/pipeline.py`
```python
class UrbanSafetyAIPipeline:
    def __init__(
        self,
        source: str = "0",
        model_weights: str = "yolo11n-pose.pt",
        enable_cloudflare: bool = True,
        output_dir: str = "output"
    ) -> None: ...

    def step(self, frame_index: int) -> Tuple[np.ndarray, SOCEngineOutput, Optional[str]]:
        """Thực hiện một chu trình hoàn chỉnh của pipeline trên 1 khung hình."""
        ...
    def close(self) -> None: ...
```

---

## 3. KỊCH BẢN KIỂM THỬ XÁC MINH (VERIFICATION & TEST PLAN)

Tệp kiểm thử `test_ai_pipeline.py` sẽ kiểm chứng 5 giai đoạn độc lập:
1. **Kiểm thử Thu nhận Luồng (Stream Reader Test):** Đọc liên tục 20 khung hình từ luồng giả lập/camera, đảm bảo không bị nghẽn, trả về đúng định dạng BGR.
2. **Kiểm thử Biomechanical Kinematics (Kinematics Builder Test):** Đưa dữ liệu 17 khớp giả lập (tư thế ngã, đứng, vung tay) $\to$ tính toán chính xác góc cột sống $\theta_{\text{spine}}$ và động năng cổ tay $E_{\text{wrist}}$.
3. **Kiểm thử Trích xuất Video Bằng chứng (Rolling Buffer Test):** Kích hoạt cờ `trigger_recording = True` $\to$ kiểm tra file MP4 được lưu vào thư mục `output/`, kiểm tra tính toàn vẹn của video (mở đọc bằng OpenCV và kiểm tra số lượng khung hình).
4. **Kiểm thử Soạn thảo Giao diện HUD (Visual Composer Test):** Render toàn bộ lớp overlay lên ảnh $\to$ đảm bảo không bị lỗi mảng màu và phím tắt `toggle_debug_box()` hoạt động chính xác.
5. **Kiểm thử Pipeline Tích hợp Toàn diện (End-to-End Pipeline Test):** Chạy liên tục chu trình qua `ThreatMarkingEngine` và `CloudflareSOCClient`, xác nhận luồng dữ liệu thông suốt từ camera đến kho lưu trữ sự cố.

---

[WAITING FOR PLAN APPROVAL]
