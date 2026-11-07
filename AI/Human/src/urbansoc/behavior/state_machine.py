"""Hysteresis and Debounce State Machine for stable threat categorization and anti-flapping."""

from dataclasses import dataclass
from typing import Optional, Tuple

from urbansoc.domain.enums import AuditEventType, BehaviorType, ThreatLevel
from urbansoc.domain.schemas import BehaviorPrediction

# Fast-track behaviors requiring immediate (~0.3s) activation due to imminent physical danger
FAST_TRACK_BEHAVIORS = {
    BehaviorType.FALLEN,
    BehaviorType.FIGHTING,
    BehaviorType.WEAPON_THREAT,
    BehaviorType.KNIFE_THREAT,
    BehaviorType.SNATCHING,
    BehaviorType.RESTRAINING,
}


@dataclass
class TrackDebounceState:
    """Internal state machine container for a single track."""
    confirmed_behavior: str = BehaviorType.NORMAL.value
    confirmed_threat_level: ThreatLevel = ThreatLevel.LOW
    confirmed_threat_score: float = 0.10
    confirmed_reasoning: str = "Normal activity"
    confirmed_interacting_id: Optional[int] = None
    confirmed_since: float = 0.0

    candidate_behavior: Optional[BehaviorType] = None
    candidate_streak: int = 0
    candidate_prediction: Optional[BehaviorPrediction] = None


class HysteresisDebouncer:
    """State machine enforcing hysteresis, debounce frames, and fast-track rules."""

    def __init__(
        self,
        enter_debounce_frames: int = 8,
        exit_debounce_frames: int = 12,
        fast_track_debounce_frames: int = 6,
    ) -> None:
        self.enter_debounce_frames = enter_debounce_frames
        self.exit_debounce_frames = exit_debounce_frames
        self.fast_track_debounce_frames = fast_track_debounce_frames

    def process_candidate(
        self,
        state: TrackDebounceState,
        raw_pred: BehaviorPrediction,
        curr_time: float,
    ) -> Optional[Tuple[str, Optional[str], str, ThreatLevel, float, str, Optional[int]]]:
        """Update debounce streak and commit state when threshold is reached.

        Returns:
            Tuple of (event_type, prev_behavior, current_behavior, threat_level, threat_score, reasoning, interacting_id)
            if a state transition was committed; otherwise None.
        """
        new_candidate = raw_pred.primary_behavior

        if new_candidate.value == state.confirmed_behavior:
            state.candidate_behavior = None
            state.candidate_streak = 0
            state.candidate_prediction = None
            if raw_pred.interacting_with_track_id is not None:
                state.confirmed_interacting_id = raw_pred.interacting_with_track_id
            return None

        # Candidate differs from confirmed behavior
        if state.candidate_behavior == new_candidate:
            state.candidate_streak += 1
            state.candidate_prediction = raw_pred
        else:
            state.candidate_behavior = new_candidate
            state.candidate_streak = 1
            state.candidate_prediction = raw_pred

        # Determine required streak based on target state
        if new_candidate in FAST_TRACK_BEHAVIORS:
            req_streak = self.fast_track_debounce_frames
        elif new_candidate == BehaviorType.NORMAL:
            req_streak = self.exit_debounce_frames
        else:
            req_streak = self.enter_debounce_frames

        # Check commit threshold
        if state.candidate_streak >= req_streak:
            prev_behavior = state.confirmed_behavior
            state.confirmed_behavior = raw_pred.primary_behavior.value
            state.confirmed_threat_level = raw_pred.threat_level
            state.confirmed_threat_score = raw_pred.threat_score
            state.confirmed_reasoning = raw_pred.reasoning
            state.confirmed_interacting_id = raw_pred.interacting_with_track_id
            state.confirmed_since = curr_time

            # Audit event type taxonomy
            if raw_pred.threat_level == ThreatLevel.CRITICAL:
                event_type = AuditEventType.CRITICAL_ALERT.value
            elif raw_pred.threat_level == ThreatLevel.HIGH:
                event_type = AuditEventType.THREAT_ESCALATION.value
            else:
                event_type = AuditEventType.STATE_TRANSITION.value

            # Reset candidate streak after successful commit
            state.candidate_behavior = None
            state.candidate_streak = 0
            state.candidate_prediction = None

            return (
                event_type,
                prev_behavior,
                state.confirmed_behavior,
                state.confirmed_threat_level,
                state.confirmed_threat_score,
                state.confirmed_reasoning,
                state.confirmed_interacting_id,
            )

        return None
