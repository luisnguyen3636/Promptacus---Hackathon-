"""Domain models and schemas for Webhook Event Dispatching with Forensic Cryptographic Integrity."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CameraLocationConfig:
    """Configuration for camera identification and geolocation."""
    camera_id: str = "CAM_01"
    name: str = "Camera Giám Sát Trung Tâm"
    zone_id: str = "ZONE_DEFAULT"
    address: str = "Đang cập nhật vị trí"
    latitude: float = 10.776889
    longitude: float = 106.700806

    def to_dict(self) -> Dict[str, Any]:
        return {
            "camera_id": self.camera_id,
            "name": self.name,
            "zone_id": self.zone_id,
            "address": self.address,
            "latitude": self.latitude,
            "longitude": self.longitude,
        }


@dataclass
class SubjectCropData:
    """Comprehensive telemetry and forensic snapshot for a single subject involved in an event."""
    track_id: int
    role: str                       # "suspect", "victim", "participant", "bystander"
    behavior: str
    threat_level: str
    threat_score: float
    confidence: float
    bbox: List[int]                 # [x1, y1, x2, y2]
    bbox_width: int
    bbox_height: int
    bbox_aspect_ratio: float
    bbox_area: int
    dwell_time_seconds: float
    speed: float
    velocity_vector: List[float]    # [vx, vy]
    kinematics: Dict[str, float]    # spine_angle, wrist_velocity, elbow angles, arm extension, wrist distance
    keypoints: List[Dict[str, Any]] # List of 17 COCO keypoints: id, name, x, y, confidence
    crop_image_base64: str          # "data:image/jpeg;base64,..."
    crop_image_sha256: str          # Cryptographic SHA-256 (RawJPEGBytes + TimestampMs)
    crop_image_size_bytes: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "track_id": self.track_id,
            "role": self.role,
            "behavior": self.behavior,
            "threat_level": self.threat_level,
            "threat_score": round(self.threat_score, 4),
            "confidence": round(self.confidence, 4),
            "bbox": self.bbox,
            "bbox_geometry": {
                "width": self.bbox_width,
                "height": self.bbox_height,
                "aspect_ratio": round(self.bbox_aspect_ratio, 2),
                "area": self.bbox_area,
            },
            "dwell_time_seconds": round(self.dwell_time_seconds, 2),
            "speed": round(self.speed, 2),
            "velocity_vector": [round(v, 2) for v in self.velocity_vector],
            "kinematics": {k: round(v, 2) for k, v in self.kinematics.items()},
            "keypoints": self.keypoints,
            "crop_image_base64": self.crop_image_base64,
            "crop_image_sha256": self.crop_image_sha256,
            "crop_image_size_bytes": self.crop_image_size_bytes,
        }


@dataclass
class WebhookIncidentPayload:
    """Complete incident event payload sent via HTTP POST to the external webhook endpoint."""
    event_id: str
    timestamp: str                  # ISO 8601 string
    timestamp_ms: int               # Unix Epoch milliseconds
    camera: CameraLocationConfig
    primary_action: str
    threat_level: str               # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    threat_score: float
    is_urgent: bool
    reasoning: str
    weapon: Dict[str, Any]          # {"is_weapon_detected": bool, "weapon_types": list, ...}
    subjects: List[SubjectCropData]
    full_image: Dict[str, Any]      # {"format": "jpeg", "width": int, "height": int, "image_base64": str, "sha256_hash": str, "image_size_bytes": int}
    audio: Dict[str, Any] = field(default_factory=dict)
    audit: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "timestamp_ms": self.timestamp_ms,
            "camera": self.camera.to_dict(),
            "detection": {
                "primary_action": self.primary_action,
                "threat_level": self.threat_level,
                "threat_score": round(self.threat_score, 4),
                "is_urgent": self.is_urgent,
                "reasoning": self.reasoning,
                "weapon": self.weapon,
                "subjects": [s.to_dict() for s in self.subjects],
                "full_image": self.full_image,
                "audio": self.audio,
            },
            "audit": self.audit,
        }
