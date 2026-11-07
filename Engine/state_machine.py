"""
Hysteresis Debounce State Machine for Urban Safety AI-SOC Threat Engine.
Prevents high-frequency state flapping, glitch triggers, and label flickering.
Implements asymmetric transition gates:
- Enter threshold: 8 frames
- Critical fast-track: 5 frames
- Exit threshold: 12 frames
Adheres strictly to SPEC-URBAN-RULE-ENGINE-01.
"""

from typing import Dict, Tuple, Any, Optional
from Engine.threat_models import (
    ThreatLevel,
    BehaviorType,
    BehaviorCategory
)


class HysteresisDebounceStateMachine:
    """
    Maintains debounced state for each tracked subject across consecutive frames.
    Filters out 1-2 frame classification anomalies while ensuring rapid emergency response.
    """

    def __init__(
        self,
        enter_debounce_frames: int = 8,
        exit_debounce_frames: int = 12,
        fast_track_critical_frames: int = 5
    ) -> None:
        self.enter_thresh = enter_debounce_frames
        self.exit_thresh = exit_debounce_frames
        self.fast_track_thresh = fast_track_critical_frames

        # track_id -> State Dict
        self._tracks_state: Dict[int, Dict[str, Any]] = {}

    def update_track_state(
        self,
        track_id: int,
        raw_threat_level: ThreatLevel,
        raw_score: float,
        raw_behavior: BehaviorType,
        raw_category: BehaviorCategory,
        timestamp: float
    ) -> Tuple[ThreatLevel, float, BehaviorType, BehaviorCategory, float, bool]:
        """
        Updates debounced state for one track.

        Returns:
            Tuple of:
            - confirmed_threat_level: Current debounced ThreatLevel mark
            - confirmed_score: Blended threat score
            - confirmed_behavior: Current debounced BehaviorType
            - confirmed_category: Current BehaviorCategory
            - state_dwell_seconds: Continuous duration in current confirmed mark
            - is_escalated: True if confirmed_threat_level transitioned to a higher rank this frame
        """
        # Rank ordering for escalation comparison
        rank_order = {
            ThreatLevel.LOW: 0,
            ThreatLevel.MEDIUM: 1,
            ThreatLevel.HIGH: 2,
            ThreatLevel.CRITICAL: 3
        }

        if track_id not in self._tracks_state:
            # Initialize track state safely at LOW / NORMAL to prevent 1st-frame glitches
            is_initial_abnormal = (raw_threat_level != ThreatLevel.LOW) or (raw_behavior != BehaviorType.NORMAL)
            self._tracks_state[track_id] = {
                "confirmed_level": ThreatLevel.LOW,
                "confirmed_score": min(raw_score, 0.25),
                "confirmed_behavior": BehaviorType.NORMAL,
                "confirmed_category": BehaviorCategory.BENIGN,
                "confirmed_since": timestamp,
                "candidate_behavior": raw_behavior if is_initial_abnormal else None,
                "candidate_level": raw_threat_level if is_initial_abnormal else None,
                "candidate_streak": 1 if is_initial_abnormal else 0,
                "last_seen": timestamp
            }
            return (
                ThreatLevel.LOW,
                min(raw_score, 0.25),
                BehaviorType.NORMAL,
                BehaviorCategory.BENIGN,
                0.0,
                False
            )

        state = self._tracks_state[track_id]
        state["last_seen"] = timestamp
        confirmed_level = state["confirmed_level"]
        confirmed_behavior = state["confirmed_behavior"]

        is_escalated = False

        is_same_state = (raw_behavior == confirmed_behavior and raw_threat_level == confirmed_level)

        if is_same_state:
            # Consistent observation: clear pending transition
            state["candidate_behavior"] = None
            state["candidate_level"] = None
            state["candidate_streak"] = 0
            state["confirmed_score"] = 0.85 * state["confirmed_score"] + 0.15 * raw_score
        else:
            # Novel or alternate candidate behavior/level observed
            if (raw_behavior == state["candidate_behavior"]) and (raw_threat_level == state["candidate_level"]):
                state["candidate_streak"] += 1
            else:
                state["candidate_behavior"] = raw_behavior
                state["candidate_level"] = raw_threat_level
                state["candidate_streak"] = 1

            # Determine required debounced streak threshold
            if raw_threat_level == ThreatLevel.CRITICAL:
                required_streak = self.fast_track_thresh
            elif rank_order[raw_threat_level] < rank_order[confirmed_level]:
                # Downgrading to lower threat level requires solid proof
                required_streak = self.exit_thresh
            else:
                # Escalating to Medium or High
                required_streak = self.enter_thresh

            # Check if threshold reached for state transition
            if state["candidate_streak"] >= required_streak:
                prev_rank = rank_order[state["confirmed_level"]]
                new_rank = rank_order[raw_threat_level]

                state["confirmed_level"] = raw_threat_level
                state["confirmed_score"] = raw_score
                state["confirmed_behavior"] = raw_behavior
                state["confirmed_category"] = raw_category
                state["confirmed_since"] = timestamp

                state["candidate_behavior"] = None
                state["candidate_level"] = None
                state["candidate_streak"] = 0

                if new_rank > prev_rank:
                    is_escalated = True

        state_dwell = max(0.0, timestamp - state["confirmed_since"])

        return (
            state["confirmed_level"],
            state["confirmed_score"],
            state["confirmed_behavior"],
            state["confirmed_category"],
            state_dwell,
            is_escalated
        )

    def prune_stale_tracks(self, current_time: float, max_idle_seconds: float = 6.0) -> None:
        """Removes tracks that have been inactive / out of frame."""
        stale_ids = [
            tid for tid, s in self._tracks_state.items()
            if (current_time - s.get("last_seen", current_time)) > max_idle_seconds
        ]
        for tid in stale_ids:
            del self._tracks_state[tid]
