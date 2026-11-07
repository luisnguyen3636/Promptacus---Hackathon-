"""Twelve standard SOC behaviors, temporal exponential decay threat scoring, and state machine."""

import math
import time
from typing import Any, Dict, List, Optional, Set, Tuple

# 12 Standard Behaviors
PRE_CRIME_ACTIONS = {
    "LOITERING",
    "STALKING",
    "INTRUSION",
    "AGGRESSIVE_GATHERING",
    "WEAPON_CONCEALMENT",
}

ACTIVE_CRIME_ACTIONS = {
    "FIGHTING",
    "WEAPON_THREAT",
    "SNATCHING",
    "RESTRAINING",
    "FALLEN",
}

POST_CRIME_ACTIONS = {
    "FLEEING",
    "EVIDENCE_DUMPING",
}

ALL_TWELVE_ACTIONS = PRE_CRIME_ACTIONS | ACTIVE_CRIME_ACTIONS | POST_CRIME_ACTIONS

ACTION_WEIGHTS = {
    "LOITERING": 25.0,
    "STALKING": 30.0,
    "AGGRESSIVE_GATHERING": 35.0,
    "INTRUSION": 50.0,
    "WEAPON_CONCEALMENT": 55.0,
    "FLEEING": 45.0,
    "EVIDENCE_DUMPING": 40.0,
    "FIGHTING": 88.0,
    "WEAPON_THREAT": 95.0,
    "SNATCHING": 90.0,
    "RESTRAINING": 86.0,
    "FALLEN": 85.0,
    "NORMAL": 0.0,
}


class TwelveBehaviorAndThreatEngine:
    """Manages 12-action behavioral categorization, anti-flapping, and temporal exponential decay threat scoring."""

    def __init__(self) -> None:
        # Subject tracking history: track_id -> {last_score, last_time, level, history_list}
        self.subjects: Dict[str, Dict[str, Any]] = {}

    def update_threat(
        self,
        track_id: str,
        detected_actions: List[str],
        timestamp_sec: Optional[float] = None,
        false_positive_suppressed: bool = False,
    ) -> Tuple[float, str, str, str, float]:
        """Compute new temporal threat score with exponential decay and anti-flapping guardrails.

        Returns:
            (temporal_threat_score, previous_level, current_level, escalation_history, recommended_vlm_sampling_sec)
        """
        now = time.time() if timestamp_sec is None else float(timestamp_sec)

        if track_id not in self.subjects:
            self.subjects[track_id] = {
                "score": 0.0,
                "last_time": now,
                "level": "Low",
                "history": ["Low"],
            }

        rec = self.subjects[track_id]
        dt = max(0.0, now - rec["last_time"])
        rec["last_time"] = now
        prev_level = rec["level"]

        # Rule-Memory check: if false positive is suppressed, force Low threat immediately
        if false_positive_suppressed:
            rec["score"] = 0.0
            curr_level = "Low"
            rec["level"] = curr_level
            if rec["history"][-1] != curr_level:
                rec["history"].append(curr_level)
            escalation_history = " -> ".join(rec["history"][-4:])
            return round(rec["score"], 1), prev_level, curr_level, escalation_history, 5.0

        # Calculate decay: S_t = S_{t-1} * exp(-0.08 * dt)
        decayed_score = rec["score"] * math.exp(-0.08 * dt)

        # Calculate incremental weight for active behaviors
        max_action_weight = 0.0
        for act in detected_actions:
            clean_act = act.strip().upper()
            w = ACTION_WEIGHTS.get(clean_act, 0.0)
            if w > max_action_weight:
                max_action_weight = w

        if max_action_weight >= 85.0:
            # Active violent crime leaps directly into Critical/High zone
            new_score = max(max_action_weight, decayed_score)
        elif max_action_weight > 0.0:
            new_score = min(100.0, decayed_score + max_action_weight)
        else:
            new_score = decayed_score

        rec["score"] = max(0.0, min(100.0, new_score))

        # Categorize threat level
        if rec["score"] >= 85.0:
            curr_level = "Critical"
            vlm_sampling = 1.0
        elif rec["score"] >= 65.0:
            curr_level = "High"
            vlm_sampling = 1.5
        elif rec["score"] >= 30.0:
            curr_level = "Medium"
            vlm_sampling = 3.0
        else:
            curr_level = "Low"
            vlm_sampling = 5.0

        # Anti-flapping: require sustained lower score before dropping from Critical/High
        if prev_level in ("Critical", "High") and curr_level == "Low" and dt < 3.0:
            curr_level = "Medium"

        rec["level"] = curr_level
        if rec["history"][-1] != curr_level:
            rec["history"].append(curr_level)

        escalation_history = " -> ".join(rec["history"][-4:])
        return round(rec["score"], 1), prev_level, curr_level, escalation_history, vlm_sampling

    @staticmethod
    def get_soc_action_state(threat_level: str) -> str:
        """Rule-HITL: Enforce strict operational state limits."""
        if threat_level in ("Critical", "High"):
            return "AWAITING_OPERATOR_VERIFICATION"
        if threat_level == "Medium":
            return "ENHANCED_TRACKING"
        return "MONITORING_ONLY"
