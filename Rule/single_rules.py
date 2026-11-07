"""
Single-Subject Behavior Rules for Urban Safety AI-SOC.
Implements 6 core rules: FallenCollapse, HandsUpDistress, SuddenFleeing,
CrouchingProwling, Loitering, and ConcealedReach.
Adheres strictly to SPEC-URBAN-RULE-ENGINE-01.
"""

import math
from typing import List, Dict, Optional, Any
from Rule.base_rule import BaseBehaviorRule
from Engine.threat_models import (
    BehaviorType,
    BehaviorCategory,
    SubjectKinematicsSnapshot,
    RuleEvaluationResult
)

# Standard COCO-17 Keypoint Constants
NOSE = 0
LEFT_EYE = 1
RIGHT_EYE = 2
LEFT_EAR = 3
RIGHT_EAR = 4
LEFT_SHOULDER = 5
RIGHT_SHOULDER = 6
LEFT_ELBOW = 7
RIGHT_ELBOW = 8
LEFT_WRIST = 9
RIGHT_WRIST = 10
LEFT_HIP = 11
RIGHT_HIP = 12
LEFT_KNEE = 13
RIGHT_KNEE = 14
LEFT_ANKLE = 15
RIGHT_ANKLE = 16


class FallenCollapseRule(BaseBehaviorRule):
    """
    Detects person falling, collapsing, or lying unresponsive on the ground.
    High priority medical emergency or assault victim indicator.
    """

    def __init__(
        self,
        angle_threshold_deg: float = 55.0,
        aspect_ratio_threshold: float = 0.90,
        max_speed_norm: float = 0.40
    ) -> None:
        super().__init__(
            name="FallenCollapseRule",
            behavior_type=BehaviorType.FALLEN_COLLAPSE,
            category=BehaviorCategory.MEDICAL_DISTRESS
        )
        self.angle_threshold = angle_threshold_deg
        self.aspect_ratio_threshold = aspect_ratio_threshold
        self.max_speed_norm = max_speed_norm

    def evaluate(
        self,
        subject: SubjectKinematicsSnapshot,
        history: List[SubjectKinematicsSnapshot],
        all_subjects: Dict[int, SubjectKinematicsSnapshot]
    ) -> RuleEvaluationResult:
        if not self.enabled:
            return self._not_matched("Rule disabled")

        # Condition 1: Horizontal torso or compressed horizontal bounding box
        is_torso_horizontal = subject.spine_angle_deg >= self.angle_threshold
        is_box_horizontal = subject.aspect_ratio <= self.aspect_ratio_threshold

        # Condition 2: Not in high-speed sports motion (e.g. baseball slide)
        is_stationary_or_low_speed = subject.velocity_norm <= self.max_speed_norm

        if (is_torso_horizontal or is_box_horizontal) and is_stationary_or_low_speed:
            confidence = 0.95 if (is_torso_horizontal and is_box_horizontal) else 0.88
            reason = (
                f"Torso horizontal (Spine={subject.spine_angle_deg:.1f}° >= {self.angle_threshold}° "
                f"or H/W={subject.aspect_ratio:.2f} <= {self.aspect_ratio_threshold}) with low velocity ({subject.velocity_norm:.2f})"
            )
            return RuleEvaluationResult(
                rule_name=self.name,
                behavior_type=self.behavior_type,
                category=self.category,
                matched=True,
                confidence=confidence,
                base_threat_score=0.95,
                reasoning=reason,
                metadata={
                    "spine_angle": subject.spine_angle_deg,
                    "aspect_ratio": subject.aspect_ratio,
                    "velocity_norm": subject.velocity_norm
                }
            )

        return self._not_matched("Upright or active motion")

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


class HandsUpDistressRule(BaseBehaviorRule):
    """
    Detects hands raised above head in distress, surrender, or robbery situation.
    """

    def __init__(self) -> None:
        super().__init__(
            name="HandsUpDistressRule",
            behavior_type=BehaviorType.HANDS_UP_DISTRESS,
            category=BehaviorCategory.MEDICAL_DISTRESS
        )

    def evaluate(
        self,
        subject: SubjectKinematicsSnapshot,
        history: List[SubjectKinematicsSnapshot],
        all_subjects: Dict[int, SubjectKinematicsSnapshot]
    ) -> RuleEvaluationResult:
        if not self.enabled:
            return self._not_matched("Rule disabled")

        kps = subject.keypoints
        # Need head reference (nose or eyes)
        head_y = None
        for hid in (NOSE, LEFT_EYE, RIGHT_EYE):
            if hid in kps and kps[hid].confidence > 0.25:
                head_y = kps[hid].y if head_y is None else min(head_y, kps[hid].y)

        if head_y is None:
            return self._not_matched("Head keypoints not visible")

        # Check wrists above head
        lw_up = LEFT_WRIST in kps and kps[LEFT_WRIST].confidence > 0.25 and kps[LEFT_WRIST].y < head_y
        rw_up = RIGHT_WRIST in kps and kps[RIGHT_WRIST].confidence > 0.25 and kps[RIGHT_WRIST].y < head_y

        if lw_up and rw_up:
            # Check separation between wrists to avoid simple hair grooming
            w_dist = abs(kps[LEFT_WRIST].x - kps[RIGHT_WRIST].x)
            sh_width = 30.0
            if LEFT_SHOULDER in kps and RIGHT_SHOULDER in kps:
                sh_width = max(20.0, abs(kps[LEFT_SHOULDER].x - kps[RIGHT_SHOULDER].x))

            if w_dist >= sh_width * 0.40:
                return RuleEvaluationResult(
                    rule_name=self.name,
                    behavior_type=self.behavior_type,
                    category=self.category,
                    matched=True,
                    confidence=0.90,
                    base_threat_score=0.78,
                    reasoning=f"Both wrists raised above head level (Head Y: {head_y:.1f}) in distress gesture",
                    metadata={"wrist_separation": w_dist, "shoulder_width": sh_width}
                )

        return self._not_matched("Wrists below head level")

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


class SuddenFleeingRule(BaseBehaviorRule):
    """
    Detects sudden acceleration and rapid fleeing or running from a scene.
    High priority post-crime indicator.
    """

    def __init__(
        self,
        speed_multiplier: float = 1.85,
        accel_threshold: float = 1.2
    ) -> None:
        super().__init__(
            name="SuddenFleeingRule",
            behavior_type=BehaviorType.SUDDEN_FLEEING,
            category=BehaviorCategory.POST_CRIME
        )
        self.speed_multiplier = speed_multiplier
        self.accel_threshold = accel_threshold

    def evaluate(
        self,
        subject: SubjectKinematicsSnapshot,
        history: List[SubjectKinematicsSnapshot],
        all_subjects: Dict[int, SubjectKinematicsSnapshot]
    ) -> RuleEvaluationResult:
        if not self.enabled:
            return self._not_matched("Rule disabled")

        if subject.velocity_norm >= self.speed_multiplier:
            # High normalized speed reached
            accel = 0.0
            if len(history) >= 2:
                prev = history[-1]
                dt = max(1e-4, subject.timestamp - prev.timestamp)
                accel = (subject.velocity_norm - prev.velocity_norm) / dt

            reason = (
                f"High movement speed: {subject.velocity_norm:.2f} body-heights/sec "
                f"(>= {self.speed_multiplier:.2f})"
            )
            if accel >= self.accel_threshold:
                reason += f" with sudden surge acceleration: {accel:.2f}"

            return RuleEvaluationResult(
                rule_name=self.name,
                behavior_type=self.behavior_type,
                category=self.category,
                matched=True,
                confidence=0.88,
                base_threat_score=0.82,
                reasoning=reason,
                metadata={"velocity_norm": subject.velocity_norm, "acceleration": accel}
            )

        return self._not_matched("Normal gait speed")

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


class CrouchingProwlingRule(BaseBehaviorRule):
    """
    Detects sneaking, crouched posture, prowling, or stealth break-in behavior.
    """

    def __init__(
        self,
        aspect_ratio_threshold: float = 1.30,
        spine_angle_min: float = 20.0,
        spine_angle_max: float = 50.0
    ) -> None:
        super().__init__(
            name="CrouchingProwlingRule",
            behavior_type=BehaviorType.CROUCHING_PROWLING,
            category=BehaviorCategory.PRE_CRIME
        )
        self.aspect_ratio_thresh = aspect_ratio_threshold
        self.spine_angle_min = spine_angle_min
        self.spine_angle_max = spine_angle_max

    def evaluate(
        self,
        subject: SubjectKinematicsSnapshot,
        history: List[SubjectKinematicsSnapshot],
        all_subjects: Dict[int, SubjectKinematicsSnapshot]
    ) -> RuleEvaluationResult:
        if not self.enabled:
            return self._not_matched("Rule disabled")

        kps = subject.keypoints
        is_compressed = subject.aspect_ratio < self.aspect_ratio_thresh
        is_bent_spine = self.spine_angle_min <= subject.spine_angle_deg <= self.spine_angle_max

        # Check knee bend if keypoints available
        has_knee_bend = False
        if (LEFT_KNEE in kps or RIGHT_KNEE in kps) and (LEFT_HIP in kps or RIGHT_HIP in kps):
            has_knee_bend = True

        if is_compressed and (is_bent_spine or has_knee_bend):
            return RuleEvaluationResult(
                rule_name=self.name,
                behavior_type=self.behavior_type,
                category=self.category,
                matched=True,
                confidence=0.80,
                base_threat_score=0.58,
                reasoning=(
                    f"Low center of gravity posture (H/W={subject.aspect_ratio:.2f} < {self.aspect_ratio_thresh}) "
                    f"with forward bent torso ({subject.spine_angle_deg:.1f}°)"
                ),
                metadata={"aspect_ratio": subject.aspect_ratio, "spine_angle": subject.spine_angle_deg}
            )

        return self._not_matched("Upright stance")

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


class LoiteringRule(BaseBehaviorRule):
    """
    Detects lingering / loitering in restricted or monitored zones over time.
    Features dynamic escalation from MEDIUM to HIGH threat based on dwell duration.
    """

    def __init__(
        self,
        dwell_threshold_medium: float = 10.0,
        dwell_threshold_high: float = 20.0,
        max_net_disp_pixels: float = 120.0
    ) -> None:
        super().__init__(
            name="LoiteringRule",
            behavior_type=BehaviorType.LOITERING,
            category=BehaviorCategory.PRE_CRIME
        )
        self.dwell_med = dwell_threshold_medium
        self.dwell_high = dwell_threshold_high
        self.max_disp = max_net_disp_pixels

    def evaluate(
        self,
        subject: SubjectKinematicsSnapshot,
        history: List[SubjectKinematicsSnapshot],
        all_subjects: Dict[int, SubjectKinematicsSnapshot]
    ) -> RuleEvaluationResult:
        if not self.enabled:
            return self._not_matched("Rule disabled")

        dwell = subject.dwell_time_seconds
        if dwell < self.dwell_med or len(history) < 10:
            return self._not_matched(f"Dwell time {dwell:.1f}s below threshold ({self.dwell_med}s)")

        # Calculate net displacement from initial centroid in history
        initial_c = history[0].centroid
        current_c = subject.centroid
        net_disp = math.hypot(current_c[0] - initial_c[0], current_c[1] - initial_c[1])

        bw = max(1, subject.bbox[2] - subject.bbox[0])
        disp_limit = max(self.max_disp, bw * 2.5)

        if net_disp <= disp_limit:
            is_high = dwell >= self.dwell_high
            threat_score = 0.72 if is_high else 0.52
            conf = 0.90 if is_high else 0.82

            return RuleEvaluationResult(
                rule_name=self.name,
                behavior_type=self.behavior_type,
                category=self.category,
                matched=True,
                confidence=conf,
                base_threat_score=threat_score,
                reasoning=(
                    f"Lingering in restricted vicinity for {dwell:.1f}s "
                    f"(Net displacement: {net_disp:.1f}px <= {disp_limit:.1f}px)"
                ),
                metadata={"dwell_time": dwell, "net_displacement": net_disp}
            )

        return self._not_matched(f"Active transit displacement: {net_disp:.1f}px")

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


class ConcealedReachRule(BaseBehaviorRule):
    """
    Detects hand concealed behind back or reaching inside jacket/waistband.
    Key pre-crime indicator for concealed weapons or suspicious readiness.
    """

    def __init__(self, min_dwell_seconds: float = 3.0) -> None:
        super().__init__(
            name="ConcealedReachRule",
            behavior_type=BehaviorType.CONCEALED_REACH,
            category=BehaviorCategory.PRE_CRIME
        )
        self.min_dwell = min_dwell_seconds

    def evaluate(
        self,
        subject: SubjectKinematicsSnapshot,
        history: List[SubjectKinematicsSnapshot],
        all_subjects: Dict[int, SubjectKinematicsSnapshot]
    ) -> RuleEvaluationResult:
        if not self.enabled:
            return self._not_matched("Rule disabled")

        kps = subject.keypoints
        # Shoulders must be visible
        sh_vis = (LEFT_SHOULDER in kps and kps[LEFT_SHOULDER].confidence > 0.40) and (
            RIGHT_SHOULDER in kps and kps[RIGHT_SHOULDER].confidence > 0.40
        )
        if not sh_vis:
            return self._not_matched("Shoulders not visible")

        # Check if one wrist is completely hidden while elbow is pulled back/bent
        lw_hidden = (LEFT_WRIST not in kps) or (kps[LEFT_WRIST].confidence < 0.20)
        rw_hidden = (RIGHT_WRIST not in kps) or (kps[RIGHT_WRIST].confidence < 0.20)

        elbow_tucked = False
        if lw_hidden and LEFT_ELBOW in kps and LEFT_HIP in kps:
            d_el_hip = math.hypot(kps[LEFT_ELBOW].x - kps[LEFT_HIP].x, kps[LEFT_ELBOW].y - kps[LEFT_HIP].y)
            if d_el_hip < 60.0:
                elbow_tucked = True

        if rw_hidden and RIGHT_ELBOW in kps and RIGHT_HIP in kps:
            d_er_hip = math.hypot(kps[RIGHT_ELBOW].x - kps[RIGHT_HIP].x, kps[RIGHT_ELBOW].y - kps[RIGHT_HIP].y)
            if d_er_hip < 60.0:
                elbow_tucked = True

        if (lw_hidden or rw_hidden) and elbow_tucked and subject.dwell_time_seconds >= self.min_dwell:
            return RuleEvaluationResult(
                rule_name=self.name,
                behavior_type=self.behavior_type,
                category=self.category,
                matched=True,
                confidence=0.76,
                base_threat_score=0.65,
                reasoning="Arm bent and hand concealed behind hip/waistband continuous stance",
                metadata={"lw_hidden": lw_hidden, "rw_hidden": rw_hidden}
            )

        return self._not_matched("Hands normally positioned")

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
