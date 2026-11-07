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
    hand_crop_image_base64: str = ""
    hand_crop_image_sha256: str = ""
    audio: Dict[str, Any] = field(default_factory=dict)
    audit: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        full_b64 = self.full_image.get("image_base64", "")
        hand_b64 = self.hand_crop_image_base64
        first_subject = self.subjects[0] if self.subjects else None
        subject_b64 = first_subject.crop_image_base64 if first_subject else ""

        # Construct DeepSeek VLM prompt and OpenAI-compatible message structure
        ai_prompt = (
            f"URBAN SAFETY AI-SOC SURVEILLANCE EVENT [{self.event_id} | CAMERA: {self.camera.camera_id}]:\n"
            f"Detected action: {self.primary_action} (Threat: {self.threat_level}, Score: {self.threat_score:.2f}).\n"
            f"Reasoning: {self.reasoning}.\n"
            f"Task for DeepSeek VLM: Please inspect the attached surveillance frame and zoomed hand/object crop:\n"
            f"1. Is the subject wielding or holding a weapon, sharp object, knife, firearm, or harmless object?\n"
            f"2. Confirm specific weapon classification (knife, blade, box cutter, firearm, tool, phone).\n"
            f"3. Provide situational assessment and emergency dispatch advisory."
        )

        deepseek_content = [
            {"type": "text", "text": ai_prompt},
        ]
        if full_b64:
            deepseek_content.append({"type": "image_url", "image_url": {"url": full_b64}})
        if hand_b64:
            deepseek_content.append({"type": "image_url", "image_url": {"url": hand_b64}})
        elif subject_b64:
            deepseek_content.append({"type": "image_url", "image_url": {"url": subject_b64}})

        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "timestamp_ms": self.timestamp_ms,
            "camera_id": self.camera.camera_id,
            "camera_name": self.camera.name,
            "cameraId": self.camera.camera_id,
            "title": f"Cảnh báo: {self.primary_action} ({self.threat_level})",
            "severity": self.threat_level,
            "vlmAnalysis": self.reasoning,
            "primary_action": self.primary_action,
            "threat_level": self.threat_level,
            "threat_score": round(self.threat_score, 4),
            "is_urgent": self.is_urgent,
            "reasoning": self.reasoning,
            "weapon_info": self.weapon,

            # Direct top-level image fields for DeepSeek & VLM consumers
            "image": full_b64,
            "image_base64": full_b64,
            "hand_crop_base64": hand_b64,
            "subject_crop_base64": subject_b64,
            "image_url": f"/api/v1/incidents/{self.event_id}/image.jpg",
            "hand_crop_url": f"/api/v1/incidents/{self.event_id}/hand_crop.jpg" if hand_b64 else None,
            "ai_prompt": ai_prompt,
            "deepseek_message": {
                "role": "user",
                "content": deepseek_content,
            },
            "forensic_hash": self.full_image.get("sha256_hash", ""),

            # Backward-compatible nested structure
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
                "hand_crop_image_base64": hand_b64,
                "audio": self.audio,
            },
            "audit": self.audit,
        }
