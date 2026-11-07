"""
Data Models and Enums for Urban Safety AI-SOC Threat Engine and Rule System.
Adheres strictly to SPEC-URBAN-RULE-ENGINE-01 and API contracts in standard.md.
"""

from enum import Enum
from typing import List, Tuple, Dict, Optional, Any
from pydantic import BaseModel, Field


class ThreatLevel(str, Enum):
    """4 standard SOC threat levels corresponding to visual marks and operational response."""
    LOW = "LOW"          # Safe / Normal activity (Green)
    MEDIUM = "MEDIUM"    # Suspicious / Minor pre-crime indicators (Yellow)
    HIGH = "HIGH"        # High risk / Alert SOC screens (Orange)
    CRITICAL = "CRITICAL"# Emergency / Violent or life-threatening event (Red)


class BehaviorCategory(str, Enum):
    """Categorization of human actions for operational security and forensic auditing."""
    BENIGN = "BENIGN"                      # Normal benign activity
    PRE_CRIME = "PRE_CRIME"                # Pre-crime indicator (loitering, concealing, prowling)
    IN_PROGRESS_CRIME = "IN_PROGRESS_CRIME"# Crime in progress (fighting, grappling, pursuit)
    POST_CRIME = "POST_CRIME"              # Post-crime action (sudden fleeing)
    MEDICAL_DISTRESS = "MEDICAL_DISTRESS"  # Medical emergency / Distress surrender


class BehaviorType(str, Enum):
    """Extended catalog of recognized urban behaviors."""
    NORMAL = "NORMAL"
    CROUCHING_PROWLING = "CROUCHING_PROWLING"
    LOITERING = "LOITERING"
    CONCEALED_REACH = "CONCEALED_REACH"
    HANDS_UP_DISTRESS = "HANDS_UP_DISTRESS"
    SUDDEN_FLEEING = "SUDDEN_FLEEING"
    FIGHTING_STRIKE = "FIGHTING_STRIKE"
    GRAPPLING_STRUGGLE = "GRAPPLING_STRUGGLE"
    CHASING_PURSUIT = "CHASING_PURSUIT"
    SURROUNDED_VICTIM = "SURROUNDED_VICTIM"
    FALLEN_COLLAPSE = "FALLEN_COLLAPSE"


class KeypointData(BaseModel):
    """Coordinate, confidence, and anatomical identity of a detected COCO-17 keypoint."""
    id: int
    name: str
    x: float
    y: float
    confidence: float


class SubjectKinematicsSnapshot(BaseModel):
    """Biomechanical kinematics snapshot of a tracked subject at a specific frame/time."""
    track_id: int
    bbox: Tuple[int, int, int, int]           # (x1, y1, x2, y2)
    centroid: Tuple[float, float]             # (cx, cy)
    keypoints: Dict[int, KeypointData]        # keypoint_id -> KeypointData
    spine_angle_deg: float                    # Deviation from vertical in degrees [0, 90]
    aspect_ratio: float                       # Height / Width (H / W)
    velocity_norm: float                      # Normalized speed (body-heights per second)
    wrist_kinetic_energy: float               # Cumulative kinetic energy of both wrists
    dwell_time_seconds: float                 # Continuous presence duration in scene
    timestamp: float = 0.0                    # Epoch timestamp


class RuleEvaluationResult(BaseModel):
    """Standardized output returned by any behavior rule evaluation."""
    rule_name: str
    behavior_type: BehaviorType
    category: BehaviorCategory
    matched: bool
    confidence: float = Field(ge=0.0, le=1.0)
    base_threat_score: float = Field(ge=0.0, le=1.0)
    reasoning: str
    interacting_with_track_ids: List[int] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SubjectThreatMark(BaseModel):
    """Visual and operational threat mark assigned to a tracked subject by the Threat Engine."""
    track_id: int
    threat_level: ThreatLevel
    threat_score: float = Field(ge=0.0, le=1.0)
    confirmed_behavior: BehaviorType
    behavior_category: BehaviorCategory
    dwell_time_seconds: float
    state_dwell_seconds: float                 # Continuous dwell time in current threat mark
    is_escalated: bool                         # True if threat level just increased
    requires_operator_attention: bool          # Flag triggering Operational HITL gate (Threat >= HIGH)
    interacting_partners: List[int] = Field(default_factory=list)
    diagnostic_summary: str
    color_hex: str                             # Hex code for SOC UI: #00E676, #FFD600, #FF9100, #FF1744


class SOCEngineOutput(BaseModel):
    """Full structured output of ThreatMarkingEngine for a single processed frame."""
    frame_index: int
    timestamp: str                             # ISO-8601: YYYY-MM-DD HH:MM:SS.mmm
    subjects_count: int
    threat_marks: List[SubjectThreatMark]
    highest_threat_level: ThreatLevel
    highest_threat_score: float
    active_alerts: List[str]
    audit_events: List[Dict[str, Any]] = Field(default_factory=list)

    @property
    def has_critical_incident(self) -> bool:
        return self.highest_threat_level == ThreatLevel.CRITICAL

    @property
    def requires_operator_verification(self) -> bool:
        return self.highest_threat_level in (ThreatLevel.HIGH, ThreatLevel.CRITICAL)
