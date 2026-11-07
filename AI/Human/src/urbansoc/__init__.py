"""Urban Safety AI-SOC Package.

Human Detection, 2D Pose Estimation, Dynamic Threat Scoring, and Audit Observability.
"""

from urbansoc.apps.batch import BatchHumanDetector
from urbansoc.apps.live import CameraRecorder
from urbansoc.behavior.engine import BehaviorEngine
from urbansoc.detection.yolo_pose import YOLOPoseDetector
from urbansoc.domain.enums import AuditEventType, BehaviorType, ThreatLevel
from urbansoc.domain.geometry import BBox
from urbansoc.domain.schemas import (
    BehaviorAuditLogEntry,
    BehaviorPrediction,
    HumanPoseTrack,
    KeypointCOCO,
    SOCFrameAnalysisResult,
    TrackKinematicsTelemetry,
)

__version__ = "0.2.0"

__all__ = [
    "ThreatLevel",
    "BehaviorType",
    "AuditEventType",
    "BBox",
    "KeypointCOCO",
    "BehaviorPrediction",
    "HumanPoseTrack",
    "SOCFrameAnalysisResult",
    "TrackKinematicsTelemetry",
    "BehaviorAuditLogEntry",
    "BehaviorEngine",
    "YOLOPoseDetector",
    "CameraRecorder",
    "BatchHumanDetector",
]
