"""Behavior recognition, kinematics, and state machine package."""

from urbansoc.behavior.engine import BehaviorEngine
from urbansoc.behavior.interactions import analyze_multi_person_interactions
from urbansoc.behavior.kinematics import extract_kinematics_state
from urbansoc.behavior.rules import (
    compute_normalized_speed,
    evaluate_single_track_behavior,
)
from urbansoc.behavior.state_machine import HysteresisDebouncer, TrackDebounceState

__all__ = [
    "BehaviorEngine",
    "extract_kinematics_state",
    "compute_normalized_speed",
    "evaluate_single_track_behavior",
    "analyze_multi_person_interactions",
    "HysteresisDebouncer",
    "TrackDebounceState",
]
