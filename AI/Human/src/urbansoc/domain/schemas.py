"""Data schemas and domain models for Urban Safety AI-SOC."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from urbansoc.domain.enums import BehaviorType, ThreatLevel
from urbansoc.domain.geometry import BBox


@dataclass
class KeypointCOCO:
    """COCO-17 Keypoint representation."""
    id: int            # 0..16
    name: str          # "nose", "left_shoulder", ...
    x: float           # pixel X
    y: float           # pixel Y
    confidence: float  # 0.0..1.0


@dataclass
class BehaviorPrediction:
    """Instantaneous or confirmed behavior prediction."""
    primary_behavior: BehaviorType
    confidence: float
    threat_level: ThreatLevel
    threat_score: float                      # 0.00..1.00
    reasoning: str                           # audit reasoning explanation
    interacting_with_track_id: Optional[int] = None


@dataclass
class TrackHistoryState:
    """Historical state snapshot for a single track at a given timestamp."""
    timestamp: float
    bbox: BBox
    centroid: Tuple[float, float]
    keypoints: List[KeypointCOCO]
    spine_angle: float
    wrist_velocity: float
    body_velocity: float
    left_elbow_angle: float = 0.0
    right_elbow_angle: float = 0.0
    left_arm_extension: float = 0.0
    right_arm_extension: float = 0.0
    wrist_distance: float = 0.0
    velocity_vector: Tuple[float, float] = (0.0, 0.0)


@dataclass
class TrackKinematicsTelemetry:
    """Telemetry data for UI rendering and diagnostic inspection."""
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
    """Audit log entry saved to JSONL and text log for SOC traceability."""
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
    """Tracked human subject with COCO keypoints and behavior prediction."""
    track_id: int
    bbox: BBox
    detection_conf: float
    keypoints: List[KeypointCOCO] = field(default_factory=list)
    behavior: BehaviorPrediction = field(default_factory=lambda: BehaviorPrediction(
        primary_behavior=BehaviorType.NORMAL,
        confidence=1.0,
        threat_level=ThreatLevel.LOW,
        threat_score=0.10,
        reasoning="Normal activity"
    ))
    dwell_time_seconds: float = 0.0

    @property
    def posture_label(self) -> str:
        return self.behavior.primary_behavior.value

    @property
    def confidence(self) -> float:
        return self.detection_conf


@dataclass
class SOCFrameAnalysisResult:
    """Comprehensive frame-level analysis result across all detected subjects."""
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
    def has_human(self) -> bool:
        return self.human_count > 0

    @property
    def requires_operator_attention(self) -> bool:
        return self.highest_threat_level in (ThreatLevel.HIGH, ThreatLevel.CRITICAL)


# Legacy MediaPipe schemas (kept for backward compatibility & resilient fallback)
@dataclass
class Keypoint:
    """MediaPipe 33 Landmark."""
    id: int
    name: str
    x: int
    y: int
    z: float
    visibility: float


@dataclass
class HumanPose:
    """MediaPipe detected human pose."""
    track_id: int
    bbox: BBox
    confidence: float
    keypoints: List[Keypoint] = field(default_factory=list)
    posture_label: str = "Standing"     # "Standing" | "Sitting" | "Observed"


@dataclass
class FrameAnalysisResult:
    """MediaPipe fallback frame analysis result."""
    frame_index: int
    timestamp: str
    human_count: int
    humans: List[HumanPose] = field(default_factory=list)
    inference_time_ms: float = 0.0
    is_recording_evidence: bool = False

    @property
    def has_human(self) -> bool:
        return self.human_count > 0


@dataclass
class HumanIncidentClip:
    """Incident video clip metadata for batch streaming or evidence packaging."""
    event_id: str
    source_video: str
    start_time: str
    end_time: str
    start_frame: int
    end_frame: int
    duration_seconds: float
    output_filepath: str
    max_confidence: float = 0.0
    primary_behavior: str = "NORMAL"
    threat_level: str = "LOW"
