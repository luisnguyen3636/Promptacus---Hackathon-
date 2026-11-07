"""Domain Enums for Urban Safety AI-SOC."""

from enum import Enum


class ThreatLevel(str, Enum):
    """Dynamic threat evaluation levels."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class BehaviorType(str, Enum):
    """Recognized human posture and behavior classifications."""
    NORMAL = "NORMAL"
    CROUCHING = "CROUCHING"
    LOITERING = "LOITERING"
    HANDS_UP = "HANDS_UP"
    RUNNING = "RUNNING"
    FIGHTING = "FIGHTING"
    FALLEN = "FALLEN"
    WEAPON_THREAT = "WEAPON_THREAT"
    SNATCHING = "SNATCHING"
    PURSUIT = "PURSUIT"
    RESTRAINING = "RESTRAINING"
    SURROUNDING = "SURROUNDING"
    INTRUSION = "INTRUSION"


class AuditEventType(str, Enum):
    """Audit logging event type taxonomy."""
    TRACK_INITIALIZED = "TRACK_INITIALIZED"
    STATE_TRANSITION = "STATE_TRANSITION"
    THREAT_ESCALATION = "THREAT_ESCALATION"
    CRITICAL_ALERT = "CRITICAL_ALERT"
    HEARTBEAT_ALERT = "HEARTBEAT_ALERT"
