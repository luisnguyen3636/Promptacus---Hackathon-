"""
Data models and serialization schemas for Suspicious Action Alerts and AI Server.
Urban Safety AI-SOC Edition.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import json


@dataclass
class SuspiciousActionRequest:
    """Payload sent by the detector client to the AI Alert Server when a suspicious action is detected."""
    camera_id: str
    camera_name: str
    timestamp: str                       # ISO-8601 formatted timestamp string
    timestamp_ms: int                    # Milliseconds epoch
    track_id: int                        # Tracked subject identifier
    action: str                          # e.g., "FALLEN", "FIGHTING", "HANDS_UP", "RUNNING", "CROUCHING"
    threat_level: str                    # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    threat_score: float                  # 0.0 to 1.0
    bbox: List[int]                      # [x1, y1, x2, y2]
    kinematics: Dict[str, float]         # e.g. {"speed": 1.8, "spine_angle": 65.0, "wrist_energy": 1400.0}
    image_base64: str                    # Base64 encoded JPEG frame/crop
    location: str = "Zone A"
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SuspiciousActionRequest":
        return cls(
            camera_id=str(data.get("camera_id", "CAM_01")),
            camera_name=str(data.get("camera_name", "Surveillance Sector")),
            timestamp=str(data.get("timestamp", datetime.utcnow().isoformat() + "Z")),
            timestamp_ms=int(data.get("timestamp_ms", int(datetime.utcnow().timestamp() * 1000))),
            track_id=int(data.get("track_id", 1)),
            action=str(data.get("action", "SUSPICIOUS_BEHAVIOR")),
            threat_level=str(data.get("threat_level", "MEDIUM")),
            threat_score=float(data.get("threat_score", 0.5)),
            bbox=list(data.get("bbox", [0, 0, 100, 100])),
            kinematics=dict(data.get("kinematics", {})),
            image_base64=str(data.get("image_base64", "")),
            location=str(data.get("location", "Zone A")),
            notes=data.get("notes")
        )


@dataclass
class EvidencePackage:
    """Forensic evidence package with tamper-evident SHA-256 hashes."""
    frame_hash: str                      # SHA-256 of raw image bytes
    chain_hash: str                      # Cumulative blockchain-style Merkle/HMAC hash
    saved_image_path: str                # File path where evidence snapshot is stored
    image_url: str                       # HTTP URL to access evidence image
    camera_id: str
    track_id: int
    bounding_box: List[int]
    verification_status: str             # "VERIFIED_BY_AI", "PENDING_OPERATOR_VERIFICATION"
    tamper_check: str = "PASSED"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AIAnalysisPrediction:
    """Multimodal situational reasoning, future projections, and intent predictions."""
    description: str                     # Visual description of observed scene
    reasoning: str                       # Why action was classified as suspicious / threat
    intent_prediction: Dict[str, Any]    # "dự kiến": Projected human intent and likely next actions
    escalation_risk: str                 # "LOW", "MEDIUM", "HIGH", "SEVERE"
    recommended_action: str              # e.g., "DISPATCH_SECURITY_PATROL", "CALL_EMS", "LOG_AND_MONITOR"
    confidence: float                    # 0.0 to 1.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AlertRecord:
    """Complete 100% JSON-compliant Alert Object returned by the AI Alert Server."""
    alert_id: str                        # e.g. "ALT_20261108_034500_CAM01_T1"
    severity: str                        # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    threat_score: float                  # 0.0 to 1.0
    timestamp: str                       # ISO-8601 UTC timestamp ("đánh dấu thời gian")
    timestamp_ms: int                    # Unix milliseconds epoch
    action_type: str                     # Verified action name
    hash: str                            # Cryptographic SHA-256 hash ("mã hash")
    evidence: EvidencePackage            # Forensic evidence package ("evidence")
    ai_analysis: AIAnalysisPrediction    # Multimodal analysis & intent projection ("dự kiến")
    metadata: Dict[str, Any]             # Camera, location, and kinematic metadata
    is_alert: bool = True                # Flag indicating valid actionable alert
    status: str = "AWAITING_OPERATOR_VERIFICATION"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "severity": self.severity,
            "threat_score": round(self.threat_score, 2),
            "timestamp": self.timestamp,
            "timestamp_ms": self.timestamp_ms,
            "action_type": self.action_type,
            "hash": self.hash,
            "evidence": self.evidence.to_dict(),
            "ai_analysis": self.ai_analysis.to_dict(),
            "metadata": self.metadata,
            "is_alert": self.is_alert,
            "status": self.status,
        }

    def to_json(self, indent: Optional[int] = None) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)
