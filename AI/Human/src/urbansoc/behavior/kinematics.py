"""Kinematic feature extraction from keypoint sequences and bounding box geometry."""

import math
from typing import Optional, Sequence, Tuple

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
from urbansoc.domain.schemas import HumanPoseTrack, KeypointCOCO, TrackHistoryState


def compute_joint_angle(
    pt_a: Tuple[float, float],
    pt_vertex: Tuple[float, float],
    pt_b: Tuple[float, float],
) -> float:
    """Compute the angle at pt_vertex formed by ray(vertex->a) and ray(vertex->b) in degrees [0, 180]."""
    v1_x = pt_a[0] - pt_vertex[0]
    v1_y = pt_a[1] - pt_vertex[1]
    v2_x = pt_b[0] - pt_vertex[0]
    v2_y = pt_b[1] - pt_vertex[1]

    mag1 = math.hypot(v1_x, v1_y)
    mag2 = math.hypot(v2_x, v2_y)

    if mag1 < 1e-4 or mag2 < 1e-4:
        return 0.0

    dot = v1_x * v2_x + v1_y * v2_y
    cos_val = max(-1.0, min(1.0, dot / (mag1 * mag2)))
    return math.degrees(math.acos(cos_val))


def extract_kinematics_state(
    pose: HumanPoseTrack,
    timestamp: float,
    history: Sequence[TrackHistoryState],
    conf_thresh: float = KEYPOINT_CONFIDENCE_THRESHOLD,
) -> TrackHistoryState:
    """Extract biomechanical kinematics (spine angle, velocities, joint angles, arm extensions) with EMA smoothing."""
    cx, cy = pose.bbox.centroid
    bh = float(pose.bbox.height)

    # Keypoint lookup map by id
    kp_map = {kp.id: kp for kp in pose.keypoints if kp.confidence >= conf_thresh}

    # a) Spine Angle calculation
    shoulder_pts = []
    if LEFT_SHOULDER in kp_map:
        shoulder_pts.append((kp_map[LEFT_SHOULDER].x, kp_map[LEFT_SHOULDER].y))
    if RIGHT_SHOULDER in kp_map:
        shoulder_pts.append((kp_map[RIGHT_SHOULDER].x, kp_map[RIGHT_SHOULDER].y))

    hip_pts = []
    if LEFT_HIP in kp_map:
        hip_pts.append((kp_map[LEFT_HIP].x, kp_map[LEFT_HIP].y))
    if RIGHT_HIP in kp_map:
        hip_pts.append((kp_map[RIGHT_HIP].x, kp_map[RIGHT_HIP].y))

    raw_spine_angle = 0.0
    if shoulder_pts and hip_pts:
        s_x = sum(p[0] for p in shoulder_pts) / len(shoulder_pts)
        s_y = sum(p[1] for p in shoulder_pts) / len(shoulder_pts)
        h_x = sum(p[0] for p in hip_pts) / len(hip_pts)
        h_y = sum(p[1] for p in hip_pts) / len(hip_pts)

        dx = abs(s_x - h_x)
        dy = max(1e-4, abs(s_y - h_y))
        raw_spine_angle = math.degrees(math.atan2(dx, dy))
    elif shoulder_pts:
        # Fallback when hips are occluded (e.g. upper-body webcam): compute from head-shoulder axis and shoulder tilt
        head_pts = []
        for hid in (NOSE, LEFT_EYE, RIGHT_EYE):
            if hid in kp_map:
                head_pts.append((kp_map[hid].x, kp_map[hid].y))
        
        s_x = sum(p[0] for p in shoulder_pts) / len(shoulder_pts)
        s_y = sum(p[1] for p in shoulder_pts) / len(shoulder_pts)

        if head_pts:
            hd_x = sum(p[0] for p in head_pts) / len(head_pts)
            hd_y = sum(p[1] for p in head_pts) / len(head_pts)
            dx = abs(hd_x - s_x)
            dy = max(1e-4, abs(hd_y - s_y))
            raw_spine_angle = math.degrees(math.atan2(dx, dy))
        
        if len(shoulder_pts) == 2:
            sh_dx = max(1e-4, abs(shoulder_pts[0][0] - shoulder_pts[1][0]))
            sh_dy = abs(shoulder_pts[0][1] - shoulder_pts[1][1])
            shoulder_tilt = math.degrees(math.atan2(sh_dy, sh_dx))
            if shoulder_tilt >= 35.0:
                raw_spine_angle = max(raw_spine_angle, shoulder_tilt + 25.0)

    if history:
        spine_angle = 0.70 * raw_spine_angle + 0.30 * history[-1].spine_angle
    else:
        spine_angle = raw_spine_angle

    # b) Joint Angles: Left & Right Elbow
    left_elbow_angle = 0.0
    if LEFT_SHOULDER in kp_map and LEFT_ELBOW in kp_map and LEFT_WRIST in kp_map:
        s = (kp_map[LEFT_SHOULDER].x, kp_map[LEFT_SHOULDER].y)
        e = (kp_map[LEFT_ELBOW].x, kp_map[LEFT_ELBOW].y)
        w = (kp_map[LEFT_WRIST].x, kp_map[LEFT_WRIST].y)
        left_elbow_angle = compute_joint_angle(s, e, w)

    right_elbow_angle = 0.0
    if RIGHT_SHOULDER in kp_map and RIGHT_ELBOW in kp_map and RIGHT_WRIST in kp_map:
        s = (kp_map[RIGHT_SHOULDER].x, kp_map[RIGHT_SHOULDER].y)
        e = (kp_map[RIGHT_ELBOW].x, kp_map[RIGHT_ELBOW].y)
        w = (kp_map[RIGHT_WRIST].x, kp_map[RIGHT_WRIST].y)
        right_elbow_angle = compute_joint_angle(s, e, w)

    # c) Arm Extensions normalized by body height
    left_arm_extension = 0.0
    if LEFT_SHOULDER in kp_map and LEFT_WRIST in kp_map:
        d_arm = math.hypot(
            kp_map[LEFT_WRIST].x - kp_map[LEFT_SHOULDER].x,
            kp_map[LEFT_WRIST].y - kp_map[LEFT_SHOULDER].y,
        )
        left_arm_extension = d_arm / max(10.0, bh)

    right_arm_extension = 0.0
    if RIGHT_SHOULDER in kp_map and RIGHT_WRIST in kp_map:
        d_arm = math.hypot(
            kp_map[RIGHT_WRIST].x - kp_map[RIGHT_SHOULDER].x,
            kp_map[RIGHT_WRIST].y - kp_map[RIGHT_SHOULDER].y,
        )
        right_arm_extension = d_arm / max(10.0, bh)

    # d) Wrist Convergence Distance
    wrist_distance = 1.0
    if LEFT_WRIST in kp_map and RIGHT_WRIST in kp_map:
        d_wrists = math.hypot(
            kp_map[LEFT_WRIST].x - kp_map[RIGHT_WRIST].x,
            kp_map[LEFT_WRIST].y - kp_map[RIGHT_WRIST].y,
        )
        wrist_distance = d_wrists / max(10.0, bh)

    # e) Body & Wrist Velocity and Velocity Vector
    body_velocity = 0.0
    wrist_velocity = 0.0
    velocity_vector = (0.0, 0.0)

    if history:
        prev = history[-1]
        dt = max(1e-4, timestamp - prev.timestamp)

        vx = (cx - prev.centroid[0]) / dt
        vy = (cy - prev.centroid[1]) / dt
        velocity_vector = (vx, vy)

        dist = math.hypot(cx - prev.centroid[0], cy - prev.centroid[1])
        raw_body_vel = dist / dt
        body_velocity = 0.70 * raw_body_vel + 0.30 * prev.body_velocity

        # Wrist Velocity calculation
        prev_kp_map = {kp.id: kp for kp in prev.keypoints if kp.confidence >= conf_thresh}
        wrist_ids = [LEFT_WRIST, RIGHT_WRIST]
        wrist_sq_sum = 0.0
        wrist_count = 0

        for wid in wrist_ids:
            if wid in kp_map and wid in prev_kp_map:
                curr_w = kp_map[wid]
                prev_w = prev_kp_map[wid]
                d_w = math.hypot(curr_w.x - prev_w.x, curr_w.y - prev_w.y)
                wrist_sq_sum += (d_w / dt) ** 2
                wrist_count += 1

        if wrist_count > 0:
            raw_wrist_vel = math.sqrt(wrist_sq_sum / wrist_count)
            wrist_velocity = 0.70 * raw_wrist_vel + 0.30 * prev.wrist_velocity
        else:
            wrist_velocity = 0.30 * prev.wrist_velocity

    return TrackHistoryState(
        timestamp=timestamp,
        bbox=pose.bbox,
        centroid=(cx, cy),
        keypoints=pose.keypoints,
        spine_angle=spine_angle,
        wrist_velocity=wrist_velocity,
        body_velocity=body_velocity,
        left_elbow_angle=left_elbow_angle,
        right_elbow_angle=right_elbow_angle,
        left_arm_extension=left_arm_extension,
        right_arm_extension=right_arm_extension,
        wrist_distance=wrist_distance,
        velocity_vector=velocity_vector,
    )
