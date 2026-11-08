"""MMAction2 Data Models and Action Classification Standards.

Implements OpenMMLab MMAction2 Spatio-Temporal Action Detection & Recognition schemas,
action label definitions, and criminal behavior taxonomy for Urban Safety AI-SOC.
Reference: https://github.com/open-mmlab/mmaction2
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class CriminalActionCategory(str, Enum):
    """10 Common Criminal Behaviors targeted for AI-SOC Law Enforcement."""
    WEAPON_BRANDISHING = "WEAPON_BRANDISHING"    # Rút/cầm hung khí (dao, súng, gậy)
    VIOLENT_ASSAULT = "VIOLENT_ASSAULT"          # Ẩu đả, đánh nhau, bạo lực thể xác
    ROBBERY_SNATCHING = "ROBBERY_SNATCHING"      # Cướp giật tài sản rồi tháo chạy
    FLEEING_HIGH_SPEED = "FLEEING_HIGH_SPEED"    # Bỏ chạy tốc độ cao khỏi hiện trường
    LOITERING_SUSPICIOUS = "LOITERING_SUSPICIOUS"# Lảng vảng nghi vấn tại điểm nhạy cảm
    PERIMETER_INTRUSION = "PERIMETER_INTRUSION"  # Đột nhập trái phép vùng cấm, trèo rào
    VANDALISM_TAMPERING = "VANDALISM_TAMPERING"  # Phá hoại tài sản, phá hỏng camera
    VICTIM_COLLAPSED = "VICTIM_COLLAPSED"        # Nạn nhân ngã quỵ bất động sau va chạm
    HOSTAGE_CHOKEHOLD = "HOSTAGE_CHOKEHOLD"      # Bắt giữ, khống chế, siết cổ con tin
    STALKING_PURSUIT = "STALKING_PURSUIT"        # Bám đuôi, theo dõi mục tiêu cự ly gần


class NormalActionCategory(str, Enum):
    """Benign Everyday Actions for False Positive Filtering."""
    WALKING_NORMAL = "WALKING_NORMAL"
    STANDING_STILL = "STANDING_STILL"
    SITTING_BENIGN = "SITTING_BENIGN"
    PHONE_CONVERSATION = "PHONE_CONVERSATION"
    FITNESS_JOGGING = "FITNESS_JOGGING"
    CASUAL_GESTURING = "CASUAL_GESTURING"


@dataclass
class MMActionDetection:
    """Individual human bounding box and action recognition result."""
    track_id: str
    camera_id: str
    bbox_xyxy: Tuple[float, float, float, float]  # [x1, y1, x2, y2]
    bbox_norm: Tuple[float, float, float, float]  # [cx, cy, w, h] normalized [0, 1]
    det_confidence: float
    action_label: str
    action_confidence: float
    is_criminal: bool
    criminal_category: Optional[CriminalActionCategory] = None
    threat_score: float = 0.0
    threat_level: str = "LOW"
    keypoints: Optional[List[Dict[str, float]]] = None
    velocity_vector: Tuple[float, float] = (0.0, 0.0)
    extra_meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "track_id": self.track_id,
            "camera_id": self.camera_id,
            "bbox_xyxy": list(self.bbox_xyxy),
            "bbox_norm": list(self.bbox_norm),
            "det_confidence": round(self.det_confidence, 4),
            "action_label": self.action_label,
            "action_confidence": round(self.action_confidence, 4),
            "is_criminal": self.is_criminal,
            "criminal_category": self.criminal_category.value if self.criminal_category else None,
            "threat_score": round(self.threat_score, 1),
            "threat_level": self.threat_level,
            "velocity_vector": list(self.velocity_vector),
            "extra_meta": self.extra_meta,
        }


@dataclass
class MMAction2Config:
    """Configuration specification mimicking OpenMMLab MMAction2 configs."""
    model_name: str = "mmaction2_spatiotemporal_urban_safety"
    backbone: str = "ResNet3D_SlowFast_STGCN"
    temporal_window_size: int = 16
    fps: float = 25.0
    spatial_input_size: Tuple[int, int] = (224, 224)
    det_threshold: float = 0.40
    action_threshold: float = 0.55
    criminal_threshold: float = 0.65
    device: str = "cpu"
