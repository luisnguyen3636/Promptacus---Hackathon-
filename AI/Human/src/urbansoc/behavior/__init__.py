"""Behavior recognition, kinematics, and state machine package."""

from urbansoc.behavior.engine import BehaviorEngine
from urbansoc.behavior.interactions import analyze_multi_person_interactions
from urbansoc.behavior.kinematics import extract_kinematics_state
from urbansoc.behavior.rules import (
    compute_normalized_speed,
    evaluate_single_track_behavior,
)
from urbansoc.behavior.falsification import (
    AdversarialFalsificationResult,
    AntiFalsePositiveAudit,
    FiveGateFalsificationEngine,
)
from urbansoc.behavior.state_machine import HysteresisDebouncer, TrackDebounceState
from urbansoc.behavior.twelve_actions import (
    ACTION_WEIGHTS,
    ALL_TWELVE_ACTIONS,
    TwelveBehaviorAndThreatEngine,
)

__all__ = [
    "BehaviorEngine",
    "extract_kinematics_state",
    "compute_normalized_speed",
    "evaluate_single_track_behavior",
    "analyze_multi_person_interactions",
    "HysteresisDebouncer",
    "TrackDebounceState",
    "TwelveBehaviorAndThreatEngine",
    "ACTION_WEIGHTS",
    "ALL_TWELVE_ACTIONS",
    "FiveGateFalsificationEngine",
    "AntiFalsePositiveAudit",
    "AdversarialFalsificationResult",
]
