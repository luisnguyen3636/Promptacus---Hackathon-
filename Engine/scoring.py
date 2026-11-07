"""
Dynamic Temporal Threat Scoring Module for Urban Safety AI-SOC Threat Engine.
Computes smooth, temporal risk score S_t incorporating rule confidence,
dwell time escalation, and multi-person interaction bonuses.
Adheres strictly to SPEC-URBAN-RULE-ENGINE-01.
"""

import math
from typing import List, Optional
from Engine.threat_models import (
    RuleEvaluationResult,
    ThreatLevel
)


class DynamicThreatScorer:
    """
    Computes time-decayed, smooth threat scores for tracked subjects.
    Formula:
        S_t = lambda * S_{t-1} + (1 - lambda) * S_max + delta_S_dwell + delta_S_interaction
    """

    def __init__(
        self,
        inertia_lambda: float = 0.70,
        dwell_penalty_beta: float = 0.05,
        max_dwell_penalty: float = 0.15,
        interaction_bonus: float = 0.10,
        baseline_score: float = 0.10
    ) -> None:
        self.inertia_lambda = inertia_lambda
        self.dwell_beta = dwell_penalty_beta
        self.max_dwell_penalty = max_dwell_penalty
        self.interaction_bonus = interaction_bonus
        self.baseline_score = baseline_score

    def compute_score(
        self,
        prev_score: float,
        matched_evaluations: List[RuleEvaluationResult],
        state_dwell_seconds: float,
        has_hostile_interaction: bool
    ) -> float:
        """
        Computes instantaneous dynamic threat score clamped to [0.0, 1.0].

        Args:
            prev_score: Threat score S_{t-1} from previous frame.
            matched_evaluations: All rules that matched in the current frame.
            state_dwell_seconds: Duration subject has remained in elevated/suspicious state.
            has_hostile_interaction: True if interacting with another subject with elevated risk.

        Returns:
            Computed S_t score in range [0.0, 1.0].
        """
        # 1. Determine instantaneous peak score from matched rules
        if matched_evaluations:
            s_rule_max = max(r.base_threat_score * r.confidence for r in matched_evaluations)
        else:
            s_rule_max = self.baseline_score

        # 2. Dwell time penalty (logarithmic progression)
        if state_dwell_seconds > 0:
            delta_dwell = min(self.max_dwell_penalty, self.dwell_beta * math.log(1.0 + state_dwell_seconds))
        else:
            delta_dwell = 0.0

        # 3. Hostile multi-person interaction bonus
        delta_interaction = self.interaction_bonus if has_hostile_interaction else 0.0

        # 4. Temporal blending with inertia
        raw_st = (
            self.inertia_lambda * prev_score +
            (1.0 - self.inertia_lambda) * s_rule_max +
            delta_dwell +
            delta_interaction
        )

        # 5. Fast-track override: If any rule is CRITICAL (>= 0.90), don't drag down with inertia
        if matched_evaluations and any(r.base_threat_score >= 0.90 for r in matched_evaluations):
            crit_target = max(r.base_threat_score for r in matched_evaluations if r.base_threat_score >= 0.90)
            # Quicker convergence to critical threshold
            raw_st = max(raw_st, 0.40 * prev_score + 0.60 * crit_target)

        # Clamp between 0.0 and 1.0
        return float(min(1.0, max(0.0, raw_st)))

    @staticmethod
    def map_score_to_threat_level(score: float) -> ThreatLevel:
        """
        Maps continuous score S_t to discrete ThreatLevel:
        [0.00, 0.29] -> LOW
        [0.30, 0.59] -> MEDIUM
        [0.60, 0.84] -> HIGH
        [0.85, 1.00] -> CRITICAL
        """
        if score >= 0.85:
            return ThreatLevel.CRITICAL
        elif score >= 0.60:
            return ThreatLevel.HIGH
        elif score >= 0.30:
            return ThreatLevel.MEDIUM
        else:
            return ThreatLevel.LOW

    @staticmethod
    def get_threat_color(level: ThreatLevel) -> str:
        """Returns standard UI hex color code for given ThreatLevel mark."""
        colors = {
            ThreatLevel.LOW: "#00E676",       # Vibrant Green
            ThreatLevel.MEDIUM: "#FFD600",    # Warning Yellow
            ThreatLevel.HIGH: "#FF9100",      # Alert Orange
            ThreatLevel.CRITICAL: "#FF1744"   # Emergency Red
        }
        return colors.get(level, "#00E676")
