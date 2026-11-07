"""
Multi-Subject Interaction Behavior Rules for Urban Safety AI-SOC.
Implements 4 core interaction rules:
1. FightingStrikeRule (Violent striking / punching)
2. GrapplingStruggleRule (Body wrestling / close physical struggle)
3. ChasingPursuitRule (High-speed pursuit)
4. SurroundedVictimRule (Gang harassment / surrounding victim)
Adheres strictly to SPEC-URBAN-RULE-ENGINE-01.
"""

import math
import numpy as np
from typing import List, Dict, Optional, Any, Tuple
from Rule.base_rule import BaseBehaviorRule
from Engine.threat_models import (
    BehaviorType,
    BehaviorCategory,
    SubjectKinematicsSnapshot,
    RuleEvaluationResult
)


def compute_iou(box1: Tuple[int, int, int, int], box2: Tuple[int, int, int, int]) -> float:
    """Computes Intersection over Union between two (x1, y1, x2, y2) boxes."""
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area1 = max(1.0, (box1[2] - box1[0]) * (box1[3] - box1[1]))
    area2 = max(1.0, (box2[2] - box2[0]) * (box2[3] - box2[1]))
    union = area1 + area2 - inter
    return inter / union if union > 0 else 0.0


class FightingStrikeRule(BaseBehaviorRule):
    """
    Detects violent physical confrontation, fist strikes, and active arm violence.
    Checks spatial proximity and collective wrist kinetic energy.
    """

    def __init__(
        self,
        proximity_ratio: float = 1.35,
        wrist_energy_thresh: float = 1200.0,
        individual_wrist_thresh: float = 800.0
    ) -> None:
        super().__init__(
            name="FightingStrikeRule",
            behavior_type=BehaviorType.FIGHTING_STRIKE,
            category=BehaviorCategory.IN_PROGRESS_CRIME
        )
        self.proximity_ratio = proximity_ratio
        self.wrist_energy_thresh = wrist_energy_thresh
        self.individual_wrist_thresh = individual_wrist_thresh

    def evaluate(
        self,
        subject: SubjectKinematicsSnapshot,
        history: List[SubjectKinematicsSnapshot],
        all_subjects: Dict[int, SubjectKinematicsSnapshot]
    ) -> RuleEvaluationResult:
        if not self.enabled:
            return self._not_matched("Rule disabled")

        tid = subject.track_id
        bw = max(1, subject.bbox[2] - subject.bbox[0])

        opponents_found: List[int] = []
        highest_combined_energy = 0.0

        for other_id, other_sub in all_subjects.items():
            if other_id == tid:
                continue

            # Skip if other subject is horizontal/fallen
            if other_sub.spine_angle_deg >= 55.0 or other_sub.aspect_ratio <= 0.90:
                continue

            # Coarse distance filter
            other_bw = max(1, other_sub.bbox[2] - other_sub.bbox[0])
            avg_width = (bw + other_bw) / 2.0
            dist = math.hypot(
                subject.centroid[0] - other_sub.centroid[0],
                subject.centroid[1] - other_sub.centroid[1]
            )

            if dist < avg_width * self.proximity_ratio:
                # Close physical proximity verified
                combined_energy = subject.wrist_kinetic_energy + other_sub.wrist_kinetic_energy
                individual_high = (
                    subject.wrist_kinetic_energy >= self.individual_wrist_thresh and
                    other_sub.wrist_kinetic_energy >= self.individual_wrist_thresh
                )

                if combined_energy >= self.wrist_energy_thresh or individual_high:
                    opponents_found.append(other_id)
                    highest_combined_energy = max(highest_combined_energy, combined_energy)

        if opponents_found:
            partner_str = ", ".join(f"#{oid}" for oid in opponents_found)
            return RuleEvaluationResult(
                rule_name=self.name,
                behavior_type=self.behavior_type,
                category=self.category,
                matched=True,
                confidence=0.94,
                base_threat_score=0.95,
                reasoning=(
                    f"Violent physical strike confrontation with ID {partner_str} "
                    f"(Energy: {highest_combined_energy:.0f} >= {self.wrist_energy_thresh:.0f})"
                ),
                interacting_with_track_ids=opponents_found,
                metadata={"combined_energy": highest_combined_energy}
            )

        return self._not_matched("No close hostile physical interaction")

    def _not_matched(self, reason: str) -> RuleEvaluationResult:
        return RuleEvaluationResult(
            rule_name=self.name,
            behavior_type=self.behavior_type,
            category=self.category,
            matched=False,
            confidence=0.0,
            base_threat_score=0.0,
            reasoning=reason
        )


class GrapplingStruggleRule(BaseBehaviorRule):
    """
    Detects grappling, wrestling, and close physical struggle.
    Characterized by significant bounding box overlap and volatile torso rotation without high wrist speeds.
    """

    def __init__(
        self,
        iou_threshold: float = 0.30,
        distance_ratio: float = 0.75,
        min_spine_angular_velocity: float = 30.0
    ) -> None:
        super().__init__(
            name="GrapplingStruggleRule",
            behavior_type=BehaviorType.GRAPPLING_STRUGGLE,
            category=BehaviorCategory.IN_PROGRESS_CRIME
        )
        self.iou_threshold = iou_threshold
        self.distance_ratio = distance_ratio
        self.min_spine_vel = min_spine_angular_velocity

    def evaluate(
        self,
        subject: SubjectKinematicsSnapshot,
        history: List[SubjectKinematicsSnapshot],
        all_subjects: Dict[int, SubjectKinematicsSnapshot]
    ) -> RuleEvaluationResult:
        if not self.enabled:
            return self._not_matched("Rule disabled")

        tid = subject.track_id
        bw = max(1, subject.bbox[2] - subject.bbox[0])

        # Compute spine angular rate of change for subject
        subject_spine_rate = 0.0
        if len(history) >= 1:
            prev = history[-1]
            dt = max(1e-4, subject.timestamp - prev.timestamp)
            subject_spine_rate = abs(subject.spine_angle_deg - prev.spine_angle_deg) / dt

        partners = []
        for other_id, other_sub in all_subjects.items():
            if other_id == tid:
                continue

            iou = compute_iou(subject.bbox, other_sub.bbox)
            other_bw = max(1, other_sub.bbox[2] - other_sub.bbox[0])
            avg_w = (bw + other_bw) / 2.0
            dist = math.hypot(
                subject.centroid[0] - other_sub.centroid[0],
                subject.centroid[1] - other_sub.centroid[1]
            )

            is_tangled = (iou >= self.iou_threshold) or (dist <= avg_w * self.distance_ratio)
            if is_tangled:
                # If subject is struggling or both are moving rapidly in close quarters
                if subject_spine_rate >= self.min_spine_vel or (subject.velocity_norm > 0.6 and other_sub.velocity_norm > 0.6):
                    partners.append(other_id)

        if partners:
            return RuleEvaluationResult(
                rule_name=self.name,
                behavior_type=self.behavior_type,
                category=self.category,
                matched=True,
                confidence=0.91,
                base_threat_score=0.92,
                reasoning=f"Close physical wrestling/grappling with subject(s) #{partners}",
                interacting_with_track_ids=partners,
                metadata={"spine_angular_rate": subject_spine_rate}
            )

        return self._not_matched("No body-entanglement detected")

    def _not_matched(self, reason: str) -> RuleEvaluationResult:
        return RuleEvaluationResult(
            rule_name=self.name,
            behavior_type=self.behavior_type,
            category=self.category,
            matched=False,
            confidence=0.0,
            base_threat_score=0.0,
            reasoning=reason
        )


class ChasingPursuitRule(BaseBehaviorRule):
    """
    Detects high-speed pursuit or chase between two subjects.
    Validates collinear motion vectors and persistent proximity gap.
    """

    def __init__(
        self,
        speed_threshold: float = 1.50,
        cosine_similarity_threshold: float = 0.80,
        min_body_height_dist: float = 0.8,
        max_body_height_dist: float = 4.5
    ) -> None:
        super().__init__(
            name="ChasingPursuitRule",
            behavior_type=BehaviorType.CHASING_PURSUIT,
            category=BehaviorCategory.IN_PROGRESS_CRIME
        )
        self.speed_threshold = speed_threshold
        self.cos_thresh = cosine_similarity_threshold
        self.min_dist_h = min_body_height_dist
        self.max_dist_h = max_body_height_dist

    def evaluate(
        self,
        subject: SubjectKinematicsSnapshot,
        history: List[SubjectKinematicsSnapshot],
        all_subjects: Dict[int, SubjectKinematicsSnapshot]
    ) -> RuleEvaluationResult:
        if not self.enabled:
            return self._not_matched("Rule disabled")

        if subject.velocity_norm < self.speed_threshold or len(history) < 1:
            return self._not_matched("Subject not in high-speed motion")

        # Subject motion vector
        prev = history[-1]
        v_sub = np.array([
            subject.centroid[0] - prev.centroid[0],
            subject.centroid[1] - prev.centroid[1]
        ])
        norm_v_sub = np.linalg.norm(v_sub)
        if norm_v_sub < 1e-4:
            return self._not_matched("Negligible displacement")

        bh = max(1, subject.bbox[3] - subject.bbox[1])
        chase_targets = []

        for other_id, other_sub in all_subjects.items():
            if other_id == subject.track_id:
                continue

            if other_sub.velocity_norm < self.speed_threshold:
                continue

            # Distance check
            dist = math.hypot(
                subject.centroid[0] - other_sub.centroid[0],
                subject.centroid[1] - other_sub.centroid[1]
            )
            if not (self.min_dist_h * bh <= dist <= self.max_dist_h * bh):
                continue

            # Check vector direction alignment
            # Direction vector from subject to other
            rel_dir = np.array([
                other_sub.centroid[0] - subject.centroid[0],
                other_sub.centroid[1] - subject.centroid[1]
            ])
            norm_rel = np.linalg.norm(rel_dir)
            if norm_rel > 1e-4:
                cos_sim = np.dot(v_sub, rel_dir) / (norm_v_sub * norm_rel)
                if cos_sim >= self.cos_thresh:
                    chase_targets.append(other_id)

        if chase_targets:
            return RuleEvaluationResult(
                rule_name=self.name,
                behavior_type=self.behavior_type,
                category=self.category,
                matched=True,
                confidence=0.87,
                base_threat_score=0.86,
                reasoning=f"High-speed pursuit vector chasing subject(s) #{chase_targets}",
                interacting_with_track_ids=chase_targets
            )

        return self._not_matched("No collinear pursuit target")

    def _not_matched(self, reason: str) -> RuleEvaluationResult:
        return RuleEvaluationResult(
            rule_name=self.name,
            behavior_type=self.behavior_type,
            category=self.category,
            matched=False,
            confidence=0.0,
            base_threat_score=0.0,
            reasoning=reason
        )


class SurroundedVictimRule(BaseBehaviorRule):
    """
    Detects a low-mobility victim surrounded by 2 or more individuals in close perimeter.
    Key pre-crime / mob harassment indicator.
    """

    def __init__(
        self,
        min_surrounders: int = 2,
        proximity_radius_ratio: float = 2.0,
        max_victim_speed: float = 0.60
    ) -> None:
        super().__init__(
            name="SurroundedVictimRule",
            behavior_type=BehaviorType.SURROUNDED_VICTIM,
            category=BehaviorCategory.PRE_CRIME
        )
        self.min_surrounders = min_surrounders
        self.radius_ratio = proximity_radius_ratio
        self.max_victim_speed = max_victim_speed

    def evaluate(
        self,
        subject: SubjectKinematicsSnapshot,
        history: List[SubjectKinematicsSnapshot],
        all_subjects: Dict[int, SubjectKinematicsSnapshot]
    ) -> RuleEvaluationResult:
        if not self.enabled:
            return self._not_matched("Rule disabled")

        if subject.velocity_norm > self.max_victim_speed:
            return self._not_matched("Subject is moving actively")

        bh = max(1, subject.bbox[3] - subject.bbox[1])
        radius = bh * self.radius_ratio

        surrounders: List[int] = []
        angles: List[float] = []

        for other_id, other_sub in all_subjects.items():
            if other_id == subject.track_id:
                continue

            dx = other_sub.centroid[0] - subject.centroid[0]
            dy = other_sub.centroid[1] - subject.centroid[1]
            dist = math.hypot(dx, dy)

            if dist <= radius:
                surrounders.append(other_id)
                angles.append(math.atan2(dy, dx))

        if len(surrounders) >= self.min_surrounders:
            # Check angular spread
            angles.sort()
            max_gap = 0.0
            for i in range(len(angles)):
                gap = (angles[(i + 1) % len(angles)] - angles[i]) % (2 * math.pi)
                max_gap = max(max_gap, gap)

            angular_spread_deg = math.degrees(2 * math.pi - max_gap)
            if angular_spread_deg >= 140.0:
                return RuleEvaluationResult(
                    rule_name=self.name,
                    behavior_type=self.behavior_type,
                    category=self.category,
                    matched=True,
                    confidence=0.85,
                    base_threat_score=0.80,
                    reasoning=(
                        f"Target hemmed in by {len(surrounders)} individuals #{surrounders} "
                        f"with angular perimeter spread of {angular_spread_deg:.0f}°"
                    ),
                    interacting_with_track_ids=surrounders,
                    metadata={"surrounders_count": len(surrounders), "angular_spread": angular_spread_deg}
                )

        return self._not_matched("Not surrounded by perimeter group")

    def _not_matched(self, reason: str) -> RuleEvaluationResult:
        return RuleEvaluationResult(
            rule_name=self.name,
            behavior_type=self.behavior_type,
            category=self.category,
            matched=False,
            confidence=0.0,
            base_threat_score=0.0,
            reasoning=reason
        )
