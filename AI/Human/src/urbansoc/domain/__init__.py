"""Urban Safety AI-SOC Domain package."""

from urbansoc.domain.enums import ThreatLevel, BehaviorType, AuditEventType
from urbansoc.domain.geometry import (
    BBox,
    bbox_from_xywh,
    bbox_to_xywh,
    iou_xyxy,
)
from urbansoc.domain.keypoints import (
    COCO_KEYPOINT_NAMES,
    COCO_SKELETON_PAIRS,
    KEYPOINT_CONFIDENCE_THRESHOLD,
    MEDIAPIPE_LANDMARK_NAMES,
    MEDIAPIPE_SKELETON_PAIRS,
)
from urbansoc.domain.schemas import (
    BehaviorAuditLogEntry,
    BehaviorPrediction,
    FrameAnalysisResult,
    HumanIncidentClip,
    HumanPose,
    HumanPoseTrack,
    Keypoint,
    KeypointCOCO,
    SOCFrameAnalysisResult,
    TrackHistoryState,
    TrackKinematicsTelemetry,
)
from urbansoc.domain.webhook_models import (
    CameraLocationConfig,
    SubjectCropData,
    WebhookIncidentPayload,
)

__all__ = [
    "ThreatLevel",
    "BehaviorType",
    "AuditEventType",
    "BBox",
    "bbox_from_xywh",
    "bbox_to_xywh",
    "iou_xyxy",
    "KEYPOINT_CONFIDENCE_THRESHOLD",
    "COCO_KEYPOINT_NAMES",
    "COCO_SKELETON_PAIRS",
    "MEDIAPIPE_LANDMARK_NAMES",
    "MEDIAPIPE_SKELETON_PAIRS",
    "KeypointCOCO",
    "BehaviorPrediction",
    "TrackHistoryState",
    "TrackKinematicsTelemetry",
    "BehaviorAuditLogEntry",
    "HumanPoseTrack",
    "SOCFrameAnalysisResult",
    "CameraLocationConfig",
    "SubjectCropData",
    "WebhookIncidentPayload",
    "Keypoint",
    "HumanPose",
    "FrameAnalysisResult",
    "HumanIncidentClip",
]
