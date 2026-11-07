"""Pure rule functions for single-subject behavior classification and dangerous posture detection."""

import math
from typing import Optional, Sequence, Tuple

from urbansoc.domain.enums import BehaviorType, ThreatLevel
from urbansoc.domain.keypoints import (
    KEYPOINT_CONFIDENCE_THRESHOLD,
    LEFT_ANKLE,
    LEFT_ELBOW,
    LEFT_EYE,
    LEFT_HIP,
    LEFT_KNEE,
    LEFT_SHOULDER,
    LEFT_WRIST,
    NOSE,
    RIGHT_ANKLE,
    RIGHT_ELBOW,
    RIGHT_EYE,
    RIGHT_HIP,
    RIGHT_KNEE,
    RIGHT_SHOULDER,
    RIGHT_WRIST,
)
from urbansoc.domain.schemas import BehaviorPrediction, HumanPoseTrack, TrackHistoryState


def compute_normalized_speed(
    pose: HumanPoseTrack,
    history: Sequence[TrackHistoryState],
) -> float:
    """Compute movement speed normalized by body height (body-heights / sec)."""
    if len(history) >= 5:
        dt = max(1e-4, history[-1].timestamp - history[-5].timestamp)
        disp = math.hypot(
            history[-1].centroid[0] - history[-5].centroid[0],
            history[-1].centroid[1] - history[-5].centroid[1],
        )
        norm_speed = (disp / dt) / max(10.0, float(pose.bbox.height))
        return norm_speed
    return 0.0


def check_weapon_threat(
    pose: HumanPoseTrack,
    current_state: TrackHistoryState,
    history: Sequence[TrackHistoryState],
    norm_speed: float,
    conf_thresh: float = KEYPOINT_CONFIDENCE_THRESHOLD,
) -> Optional[BehaviorPrediction]:
    """Detect dangerous weapon wielding (two-handed firearm aim, single-arm weapon pointing, overhead strike).

    Includes strict biometric gating to reject false positives (phone calls, clapping, casual pointing).
    """
    kp_map = {kp.id: kp for kp in pose.keypoints if kp.confidence >= conf_thresh}
    bh = float(pose.bbox.height)
    bw = float(pose.bbox.width)
    cx, cy = pose.bbox.centroid

    # 1. Two-Handed Tactical Firearm Aiming (Isosceles / Weaver grip)
    # Both wrists converge closely in front of torso + extended forward + controlled stance
    if (
        LEFT_WRIST in kp_map
        and RIGHT_WRIST in kp_map
        and LEFT_SHOULDER in kp_map
        and RIGHT_SHOULDER in kp_map
    ):
        s_y = (kp_map[LEFT_SHOULDER].y + kp_map[RIGHT_SHOULDER].y) / 2.0
        w_y = (kp_map[LEFT_WRIST].y + kp_map[RIGHT_WRIST].y) / 2.0

        wrists_close = current_state.wrist_distance < 0.22  # close together (< 22% body height)
        in_firing_plane = s_y - 15 <= w_y <= (cy + bh * 0.15)  # between upper chest and navel
        arms_extended = (
            current_state.left_arm_extension >= 0.12
            and current_state.right_arm_extension >= 0.12
        )
        tactical_speed = norm_speed < 1.0  # steady shooting stance

        # Reject clapping / phone typing: elbows must be extended outward/forward
        elbows_extended = (
            current_state.left_elbow_angle >= 90.0
            or current_state.right_elbow_angle >= 90.0
        )

        if wrists_close and in_firing_plane and arms_extended and tactical_speed and elbows_extended:
            return BehaviorPrediction(
                primary_behavior=BehaviorType.WEAPON_THREAT,
                confidence=0.96,
                threat_level=ThreatLevel.CRITICAL,
                threat_score=0.96,
                reasoning="Two-handed tactical weapon aiming posture (tight wrist convergence & extended arms)",
            )

    # 2. One-Handed Direct Weapon Pointing / Brandishing
    # An arm fully extended horizontally or slightly downward towards target line
    for side, shoulder_id, elbow_id, wrist_id, elbow_angle, arm_ext in [
        ("left", LEFT_SHOULDER, LEFT_ELBOW, LEFT_WRIST, current_state.left_elbow_angle, current_state.left_arm_extension),
        ("right", RIGHT_SHOULDER, RIGHT_ELBOW, RIGHT_WRIST, current_state.right_elbow_angle, current_state.right_arm_extension),
    ]:
        if shoulder_id in kp_map and elbow_id in kp_map and wrist_id in kp_map:
            s_pt = kp_map[shoulder_id]
            w_pt = kp_map[wrist_id]

            # Straight arm: elbow angle >= 145° and substantial arm extension
            is_straight = elbow_angle >= 145.0
            is_extended = arm_ext >= 0.30
            # Horizontal aiming alignment: wrist within elevation tolerance of shoulder
            is_aiming_plane = abs(w_pt.y - s_pt.y) <= (bh * 0.30)
            # Lateral projection away from body center
            is_directed_outward = abs(w_pt.x - cx) >= (bw * 0.35)

            # False positive rejection: Phone talking has elbow < 70° and wrist near head
            is_not_phone = elbow_angle > 80.0 and abs(w_pt.x - cx) >= (bw * 0.35)
            is_stable = current_state.wrist_velocity < 800.0  # pointed weapon is held with intent

            if is_straight and is_extended and is_aiming_plane and is_directed_outward and is_not_phone and is_stable:
                return BehaviorPrediction(
                    primary_behavior=BehaviorType.WEAPON_THREAT,
                    confidence=0.94,
                    threat_level=ThreatLevel.CRITICAL,
                    threat_score=0.95,
                    reasoning=f"Direct one-handed weapon pointing posture ({side} arm fully extended at {elbow_angle:.0f}°)",
                )

    # 3. Overhead Blunt / Slashing Weapon Strike Preparation
    for shoulder_id, elbow_id, wrist_id, elbow_angle in [
        (LEFT_SHOULDER, LEFT_ELBOW, LEFT_WRIST, current_state.left_elbow_angle),
        (RIGHT_SHOULDER, RIGHT_ELBOW, RIGHT_WRIST, current_state.right_elbow_angle),
    ]:
        if shoulder_id in kp_map and wrist_id in kp_map and NOSE in kp_map:
            w_pt = kp_map[wrist_id]
            nose_pt = kp_map[NOSE]
            s_pt = kp_map[shoulder_id]

            is_above_head = w_pt.y < (nose_pt.y - 15.0)
            is_cocked_elbow = 40.0 <= elbow_angle <= 100.0
            is_high_energy = current_state.wrist_velocity > 850.0

            if is_above_head and is_cocked_elbow and is_high_energy:
                return BehaviorPrediction(
                    primary_behavior=BehaviorType.WEAPON_THREAT,
                    confidence=0.92,
                    threat_level=ThreatLevel.CRITICAL,
                    threat_score=0.94,
                    reasoning="High-energy overhead weapon strike preparation / downward slash motion",
                )

    return None


def check_intrusion(
    pose: HumanPoseTrack,
    current_state: TrackHistoryState,
    history: Sequence[TrackHistoryState],
    norm_speed: float,
    conf_thresh: float = KEYPOINT_CONFIDENCE_THRESHOLD,
) -> Optional[BehaviorPrediction]:
    """Detect vertical perimeter scaling / wall climbing intrusion."""
    if len(history) < 10:
        return None

    kp_map = {kp.id: kp for kp in pose.keypoints if kp.confidence >= conf_thresh}
    oldest_state = history[-10]

    # Check vertical rising of lower body joints
    if LEFT_ANKLE in kp_map and RIGHT_ANKLE in kp_map:
        curr_ankle_y = (kp_map[LEFT_ANKLE].y + kp_map[RIGHT_ANKLE].y) / 2.0
        old_ankles = [kp.y for kp in oldest_state.keypoints if kp.id in (LEFT_ANKLE, RIGHT_ANKLE)]
        if old_ankles:
            old_ankle_y = sum(old_ankles) / len(old_ankles)
            vertical_rise = old_ankle_y - curr_ankle_y  # positive if climbing upwards

            # Hands reaching high overhead
            hands_up = False
            if LEFT_WRIST in kp_map and LEFT_SHOULDER in kp_map:
                if kp_map[LEFT_WRIST].y < kp_map[LEFT_SHOULDER].y:
                    hands_up = True
            if RIGHT_WRIST in kp_map and RIGHT_SHOULDER in kp_map:
                if kp_map[RIGHT_WRIST].y < kp_map[RIGHT_SHOULDER].y:
                    hands_up = True

            # Climbing has sustained upward displacement with low horizontal speed
            if vertical_rise > 40.0 and norm_speed < 0.6 and hands_up:
                return BehaviorPrediction(
                    primary_behavior=BehaviorType.INTRUSION,
                    confidence=0.85,
                    threat_level=ThreatLevel.HIGH,
                    threat_score=0.82,
                    reasoning=f"Perimeter climbing / vertical wall scaling motion (rise: {vertical_rise:.0f}px)",
                )

    return None


def evaluate_single_track_behavior(
    pose: HumanPoseTrack,
    current_state: TrackHistoryState,
    history: Sequence[TrackHistoryState],
    dwell_time: float,
    initial_centroid: Tuple[float, float],
    conf_thresh: float = KEYPOINT_CONFIDENCE_THRESHOLD,
    fall_angle_threshold: float = 55.0,
    fall_aspect_ratio_thresh: float = 0.90,
    run_speed_multiplier: float = 1.75,
    loiter_time_threshold: float = 10.0,
) -> Tuple[BehaviorPrediction, float, float]:
    """Evaluate single-track rules in strict priority order.

    Priority:
    1. FALLEN (Critical)
    2. WEAPON_THREAT (Critical)
    3. INTRUSION (High)
    4. HANDS_UP (High)
    5. RUNNING (High)
    6. CROUCHING (Medium)
    7. LOITERING (Medium/High)
    8. NORMAL (Low)
    """
    aspect_ratio = pose.bbox.aspect_ratio
    spine_angle = current_state.spine_angle
    norm_speed = compute_normalized_speed(pose, history)
    kp_map = {kp.id: kp for kp in pose.keypoints if kp.confidence >= conf_thresh}

    # Biometric Gate: Check if head is clearly positioned upright above shoulders
    head_y_candidates = [
        kp_map[kid].y for kid in [NOSE, LEFT_EYE, RIGHT_EYE] if kid in kp_map
    ]
    shoulder_y_candidates = [
        kp_map[kid].y for kid in [LEFT_SHOULDER, RIGHT_SHOULDER] if kid in kp_map
    ]
    is_head_upright = False
    if head_y_candidates and shoulder_y_candidates:
        min_head_y = min(head_y_candidates)
        min_shoulder_y = min(shoulder_y_candidates)
        # In image coordinates, y increases downward. Head above shoulders means min_head_y < min_shoulder_y
        if min_head_y < (min_shoulder_y - 8.0):
            is_head_upright = True

    # Rule 1: FALLEN
    # A subject is FALLEN only if:
    # 1. Torso inclination spine_angle >= fall_angle_threshold (valid when both shoulders and hips are tracked), OR
    # 2. Aspect ratio is horizontal (H/W < fall_aspect_ratio_thresh) AND head is NOT upright (collapsed forward/down or lying horizontally), OR
    # 3. Head is level with or below shoulders (collapsed onto surface or ground) with compressed posture.
    is_fallen = False
    fall_reason = ""

    if spine_angle >= fall_angle_threshold:
        is_fallen = True
        fall_reason = f"Torso angle {spine_angle:.0f}° (>= {fall_angle_threshold:.0f}°) horizontal tilt"
    elif aspect_ratio < fall_aspect_ratio_thresh and not is_head_upright:
        is_fallen = True
        fall_reason = f"Horizontal prone posture H/W {aspect_ratio:.2f} (< {fall_aspect_ratio_thresh:.2f}) with non-upright head"
    elif head_y_candidates and shoulder_y_candidates and not is_head_upright and aspect_ratio < 1.10:
        min_head_y = min(head_y_candidates)
        min_shoulder_y = min(shoulder_y_candidates)
        if min_head_y >= (min_shoulder_y - 5.0):
            is_fallen = True
            fall_reason = "Head level with or collapsed below shoulder plane"

    if is_fallen:
        pred = BehaviorPrediction(
            primary_behavior=BehaviorType.FALLEN,
            confidence=0.95,
            threat_level=ThreatLevel.CRITICAL,
            threat_score=0.98,
            reasoning=fall_reason,
        )
        return pred, norm_speed, aspect_ratio

    # Rule 2: WEAPON_THREAT
    weapon_pred = check_weapon_threat(pose, current_state, history, norm_speed, conf_thresh)
    if weapon_pred is not None:
        return weapon_pred, norm_speed, aspect_ratio

    # Rule 3: INTRUSION (Climbing)
    intrusion_pred = check_intrusion(pose, current_state, history, norm_speed, conf_thresh)
    if intrusion_pred is not None:
        return intrusion_pred, norm_speed, aspect_ratio

    # Rule 4: HANDS_UP
    if head_y_candidates:
        head_y = min(head_y_candidates)
        if (
            LEFT_WRIST in kp_map
            and RIGHT_WRIST in kp_map
            and kp_map[LEFT_WRIST].y < head_y
            and kp_map[RIGHT_WRIST].y < head_y
        ):
            pred = BehaviorPrediction(
                primary_behavior=BehaviorType.HANDS_UP,
                confidence=0.90,
                threat_level=ThreatLevel.HIGH,
                threat_score=0.78,
                reasoning="Both hands raised above head in distress / surrender gesture",
            )
            return pred, norm_speed, aspect_ratio

    # Rule 5: RUNNING
    if norm_speed >= run_speed_multiplier:
        pred = BehaviorPrediction(
            primary_behavior=BehaviorType.RUNNING,
            confidence=0.88,
            threat_level=ThreatLevel.HIGH,
            threat_score=0.80,
            reasoning=f"High movement speed: {norm_speed:.1f} body-heights/sec (> {run_speed_multiplier})",
        )
        return pred, norm_speed, aspect_ratio

    # Rule 6: CROUCHING
    has_knee = (LEFT_KNEE in kp_map) or (RIGHT_KNEE in kp_map)
    has_hip = (LEFT_HIP in kp_map) or (RIGHT_HIP in kp_map)
    if aspect_ratio < 1.30 and spine_angle < 45.0 and has_knee and has_hip:
        pred = BehaviorPrediction(
            primary_behavior=BehaviorType.CROUCHING,
            confidence=0.75,
            threat_level=ThreatLevel.MEDIUM,
            threat_score=0.55,
            reasoning=f"Compressed posture H/W {aspect_ratio:.2f} with bent knees",
        )
        return pred, norm_speed, aspect_ratio

    # Rule 7: LOITERING
    cx, cy = pose.bbox.centroid
    net_disp = math.hypot(cx - initial_centroid[0], cy - initial_centroid[1])
    loiter_disp_limit = max(120.0, float(pose.bbox.width) * 2.5)

    if dwell_time >= loiter_time_threshold and len(history) >= 20 and net_disp < loiter_disp_limit:
        # If subject has upright normal posture at desk/station, loitering is normal seated activity, NOT High/Critical
        if is_head_upright and aspect_ratio < 1.4:
            pred = BehaviorPrediction(
                primary_behavior=BehaviorType.NORMAL,
                confidence=0.92,
                threat_level=ThreatLevel.LOW,
                threat_score=0.10,
                reasoning=f"Normal stationary upright desk presence ({dwell_time:.1f}s)",
            )
            return pred, norm_speed, aspect_ratio
        else:
            threat_level = ThreatLevel.HIGH if dwell_time > 20.0 else ThreatLevel.MEDIUM
            threat_score = 0.72 if dwell_time > 20.0 else 0.52
            pred = BehaviorPrediction(
                primary_behavior=BehaviorType.LOITERING,
                confidence=0.82,
                threat_level=threat_level,
                threat_score=threat_score,
                reasoning=f"Lingering in local area for {dwell_time:.1f}s (disp: {net_disp:.0f}px)",
            )
            return pred, norm_speed, aspect_ratio

    # Rule 8: NORMAL (Default)
    pred = BehaviorPrediction(
        primary_behavior=BehaviorType.NORMAL,
        confidence=0.95,
        threat_level=ThreatLevel.LOW,
        threat_score=0.10,
        reasoning="Normal upright posture and standard gait speed",
    )
    return pred, norm_speed, aspect_ratio
