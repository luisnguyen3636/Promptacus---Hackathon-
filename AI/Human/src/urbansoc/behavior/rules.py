"""Pure rule functions for single-subject behavior classification and dangerous posture detection."""

import math
from typing import Optional, Sequence, Tuple

from urbansoc.domain.enums import BehaviorType, ThreatLevel
from urbansoc.domain.keypoints import (
    KEYPOINT_CONFIDENCE_THRESHOLD,
    LEFT_ANKLE,
    LEFT_EAR,
    LEFT_ELBOW,
    LEFT_EYE,
    LEFT_HIP,
    LEFT_KNEE,
    LEFT_SHOULDER,
    LEFT_WRIST,
    NOSE,
    RIGHT_ANKLE,
    RIGHT_EAR,
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
    # If whole-body movement is high-speed sprinting, reject stabbing false positive
    if norm_speed >= 1.5:
        return None

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
        and LEFT_ELBOW in kp_map
        and RIGHT_ELBOW in kp_map
    ):
        s_y = (kp_map[LEFT_SHOULDER].y + kp_map[RIGHT_SHOULDER].y) / 2.0
        e_y = (kp_map[LEFT_ELBOW].y + kp_map[RIGHT_ELBOW].y) / 2.0
        w_y = (kp_map[LEFT_WRIST].y + kp_map[RIGHT_WRIST].y) / 2.0

        wrists_close = current_state.wrist_distance < 0.22  # close together (< 22% body height)
        # Tactical firing plane: wrists held raised in upper chest/chin plane, NOT resting on desk/lap
        in_firing_plane = (s_y - 20.0) <= w_y <= (s_y + bh * 0.25)
        # Biometric rejection for laptop typing: in firearm aiming, wrists are raised level with or above elbows.
        # When typing on laptop or resting hands on desk, wrists slope down well below elbows (w_y > e_y + 12px).
        is_raised_aim = w_y <= (e_y + 8.0)
        arms_extended = (
            current_state.left_arm_extension >= 0.12
            and current_state.right_arm_extension >= 0.12
        )
        tactical_speed = norm_speed < 1.0  # steady shooting stance

        # Reject clapping / phone typing: elbows must be extended outward/forward
        elbows_extended = (
            current_state.left_elbow_angle >= 85.0
            or current_state.right_elbow_angle >= 85.0
        )

        if wrists_close and in_firing_plane and is_raised_aim and arms_extended and tactical_speed and elbows_extended:
            return BehaviorPrediction(
                primary_behavior=BehaviorType.WEAPON_THREAT,
                confidence=0.96,
                threat_level=ThreatLevel.CRITICAL,
                threat_score=0.96,
                reasoning="Two-handed tactical weapon aiming posture (tight wrist convergence & extended arms)",
            )

    # 2. One-Handed Direct Weapon Pointing / Brandishing
    # An arm extended horizontally, forward, or towards target line
    for side, shoulder_id, elbow_id, wrist_id, elbow_angle, arm_ext, ear_id in [
        ("left", LEFT_SHOULDER, LEFT_ELBOW, LEFT_WRIST, current_state.left_elbow_angle, current_state.left_arm_extension, LEFT_EAR),
        ("right", RIGHT_SHOULDER, RIGHT_ELBOW, RIGHT_WRIST, current_state.right_elbow_angle, current_state.right_arm_extension, RIGHT_EAR),
    ]:
        if shoulder_id in kp_map and elbow_id in kp_map and wrist_id in kp_map:
            s_pt = kp_map[shoulder_id]
            e_pt = kp_map[elbow_id]
            w_pt = kp_map[wrist_id]

            # Extended arm: elbow angle >= 130° and substantial arm extension
            is_straight = elbow_angle >= 130.0
            is_extended = arm_ext >= 0.25
            # Aiming plane: wrist held up level with shoulder/chest plane, NOT hanging down at waist
            is_aiming_plane = abs(w_pt.y - s_pt.y) <= (bh * 0.25)
            # In aiming, wrist is raised level with or higher than elbow (in normal standing arms hang below elbows)
            is_raised = w_pt.y <= (e_pt.y + 14.0)
            # Directed outward laterally OR pointing directly forward toward target
            is_directed = (abs(w_pt.x - cx) >= (bw * 0.28)) or (w_pt.y <= (s_pt.y + 10.0) and elbow_angle >= 140.0)

            # False positive rejection: Phone talking has elbow < 80° and wrist touching ear
            is_phone = False
            if ear_id in kp_map:
                ear_pt = kp_map[ear_id]
                if math.hypot(w_pt.x - ear_pt.x, w_pt.y - ear_pt.y) < max(28.0, bh * 0.15) or elbow_angle < 85.0:
                    is_phone = True

            is_stable = current_state.wrist_velocity < 800.0  # pointed weapon is held with intent

            if is_straight and is_extended and is_aiming_plane and is_raised and is_directed and not is_phone and is_stable:
                return BehaviorPrediction(
                    primary_behavior=BehaviorType.WEAPON_THREAT,
                    confidence=0.94,
                    threat_level=ThreatLevel.CRITICAL,
                    threat_score=0.95,
                    reasoning=f"Direct one-handed weapon pointing posture ({side} arm extended at {elbow_angle:.0f}°)",
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


def check_knife_threat(
    pose: HumanPoseTrack,
    current_state: TrackHistoryState,
    history: Sequence[TrackHistoryState],
    norm_speed: float,
    conf_thresh: float = KEYPOINT_CONFIDENCE_THRESHOLD,
) -> Optional[BehaviorPrediction]:
    """Detect sharp object / knife threat posture (stabbing preparation, forward thrust, or edged weapon guard).

    Kinematic indicators:
    1. Forward Stabbing Thrust: Rapid wrist acceleration forward (wrist_velocity >= 650 px/s) at chest/abdominal height.
    2. Stabbing Ready Stance: One arm cocked tight near waist/flank (elbow 45°-110°, wrist near abdomen/hip)
       combined with opposite guard arm or tactical advancement.
    """
    # If whole-body movement is high-speed sprinting, reject stabbing false positive
    if norm_speed >= 1.5:
        return None

    kp_map = {kp.id: kp for kp in pose.keypoints if kp.confidence >= conf_thresh}
    bh = float(pose.bbox.height)
    bw = float(pose.bbox.width)
    cx, cy = pose.bbox.centroid

    # Analyze left and right arms
    for side, shoulder_id, elbow_id, wrist_id, elbow_angle, arm_ext, other_w_id, other_s_id in [
        ("right", RIGHT_SHOULDER, RIGHT_ELBOW, RIGHT_WRIST, current_state.right_elbow_angle, current_state.right_arm_extension, LEFT_WRIST, LEFT_SHOULDER),
        ("left", LEFT_SHOULDER, LEFT_ELBOW, LEFT_WRIST, current_state.left_elbow_angle, current_state.left_arm_extension, RIGHT_WRIST, RIGHT_SHOULDER),
    ]:
        if shoulder_id in kp_map and elbow_id in kp_map and wrist_id in kp_map:
            s_pt = kp_map[shoulder_id]
            e_pt = kp_map[elbow_id]
            w_pt = kp_map[wrist_id]

            # In stabbing posture, the weapon is held in the abdominal/mid-torso plane
            is_stabbing_height = (s_pt.y - 15.0) <= w_pt.y <= (cy + bh * 0.35)

            # 1. Forward Stabbing Thrust Action: Rapid wrist velocity outward/forward at striking height
            is_high_speed_thrust = current_state.wrist_velocity >= 400.0
            is_projected = abs(w_pt.x - cx) >= (bw * 0.12)
            is_stabbing_angle = 45.0 <= elbow_angle <= 175.0

            if is_stabbing_height and is_high_speed_thrust and is_projected and is_stabbing_angle:
                return BehaviorPrediction(
                    primary_behavior=BehaviorType.KNIFE_THREAT,
                    confidence=0.95,
                    threat_level=ThreatLevel.CRITICAL,
                    threat_score=0.96,
                    reasoning=f"Rapid forward stabbing thrust motion with {side} hand (velocity: {current_state.wrist_velocity:.0f} px/s)",
                )

            # 2. Tactical Knife / Stabbing Ready Stance (Cocked arm + guard hand)
            is_cocked_knife = 35.0 <= elbow_angle <= 115.0 and (0.05 <= arm_ext <= 0.38)
            has_guard_arm = False
            if other_w_id in kp_map and other_s_id in kp_map:
                o_w_pt = kp_map[other_w_id]
                o_s_pt = kp_map[other_s_id]
                # Guard arm raised defensively at chest/chin height, NOT resting on table
                if o_w_pt.y <= (o_s_pt.y + 25.0):
                    has_guard_arm = True
            elif other_w_id in kp_map:
                has_guard_arm = True

            if is_stabbing_height and is_cocked_knife and has_guard_arm and norm_speed < 1.2:
                return BehaviorPrediction(
                    primary_behavior=BehaviorType.KNIFE_THREAT,
                    confidence=0.93,
                    threat_level=ThreatLevel.CRITICAL,
                    threat_score=0.95,
                    reasoning=f"Tactical knife/sharp object ready stance ({side} arm cocked with opposing guard arm)",
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
    bh = float(pose.bbox.height)
    bw = float(pose.bbox.width)
    cx, cy = pose.bbox.centroid
    kp_map = {kp.id: kp for kp in pose.keypoints if kp.confidence >= conf_thresh}

    # Biometric Gate: Check if head is clearly positioned upright above shoulders
    head_y_candidates = [
        kp_map[kid].y for kid in [NOSE, LEFT_EYE, RIGHT_EYE, LEFT_EAR, RIGHT_EAR] if kid in kp_map
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
    # A subject is FALLEN only if their head is NOT upright (collapsed) AND they exhibit horizontal collapse:
    is_fallen = False
    fall_reason = ""

    if not is_head_upright:
        # 1. Torso horizontal tilt (spine_angle >= fall_angle_threshold)
        if spine_angle >= fall_angle_threshold:
            is_fallen = True
            fall_reason = f"Torso angle {spine_angle:.0f}° (>= {fall_angle_threshold:.0f}°) horizontal tilt with non-upright head"
        # 2. Distinctly horizontal prone / supine posture (width significantly greater than height)
        elif aspect_ratio <= 0.65:
            if head_y_candidates and shoulder_y_candidates:
                min_head_y = min(head_y_candidates)
                min_shoulder_y = min(shoulder_y_candidates)
                if min_head_y >= (min_shoulder_y - 4.0):
                    is_fallen = True
                    fall_reason = f"Horizontal prone posture H/W {aspect_ratio:.2f} (<= 0.65) with head level/below shoulders"
            else:
                is_fallen = True
                fall_reason = f"Horizontal body posture H/W {aspect_ratio:.2f} (<= 0.65) collapsed on ground"
        # 3. Head collapsed level with or below shoulder plane in compressed horizontal posture
        elif head_y_candidates and shoulder_y_candidates and aspect_ratio < 0.80:
            min_head_y = min(head_y_candidates)
            min_shoulder_y = min(shoulder_y_candidates)
            if min_head_y >= (min_shoulder_y - 2.0):
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

    # Rule 2: WEAPON_THREAT (Firearm aim or overhead strike)
    weapon_pred = check_weapon_threat(pose, current_state, history, norm_speed, conf_thresh)
    if weapon_pred is not None:
        return weapon_pred, norm_speed, aspect_ratio

    # Rule 2b: KNIFE_THREAT (Sharp object / stabbing thrust / edged weapon guard)
    knife_pred = check_knife_threat(pose, current_state, history, norm_speed, conf_thresh)
    if knife_pred is not None:
        return knife_pred, norm_speed, aspect_ratio

    # Rule 3: INTRUSION (Climbing)
    intrusion_pred = check_intrusion(pose, current_state, history, norm_speed, conf_thresh)
    if intrusion_pred is not None:
        return intrusion_pred, norm_speed, aspect_ratio

    # Rule 4: HANDS_UP
    if head_y_candidates:
        head_y = min(head_y_candidates)
        both_hands_up = (
            LEFT_WRIST in kp_map
            and RIGHT_WRIST in kp_map
            and kp_map[LEFT_WRIST].y < head_y
            and kp_map[RIGHT_WRIST].y < head_y
        )
        one_hand_high = False
        if LEFT_WRIST in kp_map and kp_map[LEFT_WRIST].y < (head_y - 12.0) and current_state.left_elbow_angle >= 105.0:
            one_hand_high = True
        if RIGHT_WRIST in kp_map and kp_map[RIGHT_WRIST].y < (head_y - 12.0) and current_state.right_elbow_angle >= 105.0:
            one_hand_high = True

        if both_hands_up or one_hand_high:
            pred = BehaviorPrediction(
                primary_behavior=BehaviorType.HANDS_UP,
                confidence=0.92 if both_hands_up else 0.86,
                threat_level=ThreatLevel.HIGH,
                threat_score=0.78,
                reasoning="Both hands raised above head in distress / surrender gesture" if both_hands_up else "Hand raised high above head in distress / surrender gesture",
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

    # Rule 5b: FIGHTING / STRIKES (Single-person rapid punch or aggressive combat strike)
    if current_state.wrist_velocity >= 480.0 and norm_speed < run_speed_multiplier:
        for wid in (LEFT_WRIST, RIGHT_WRIST):
            if wid in kp_map:
                w_y = kp_map[wid].y
                if shoulder_y_candidates and (w_y <= min(shoulder_y_candidates) + bh * 0.35):
                    pred = BehaviorPrediction(
                        primary_behavior=BehaviorType.FIGHTING,
                        confidence=0.88,
                        threat_level=ThreatLevel.HIGH,
                        threat_score=0.88,
                        reasoning=f"High-velocity combat punch / strike motion detected (wrist velocity: {current_state.wrist_velocity:.0f} px/s)",
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
        has_legs = (LEFT_ANKLE in kp_map) or (RIGHT_ANKLE in kp_map) or (LEFT_KNEE in kp_map) or (RIGHT_KNEE in kp_map)
        # If subject has upright normal posture at desk/station or webcam crop (no legs visible), presence is NORMAL
        if is_head_upright and (not has_legs or aspect_ratio < 1.4):
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
