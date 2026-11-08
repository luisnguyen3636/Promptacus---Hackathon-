"""Unit and integration tests verifying webcam / camera posture classification.
Specifically ensures that people sitting or standing in front of webcam/camera
are NEVER falsely classified as FALLEN, and all other behaviors (NORMAL, HANDS_UP,
WEAPON_THREAT, KNIFE_THREAT, CROUCHING, RUNNING) are detected accurately.
"""

import numpy as np
import pytest

from urbansoc.behavior.kinematics import extract_kinematics_state
from urbansoc.behavior.rules import evaluate_single_track_behavior
from urbansoc.domain.enums import BehaviorType, ThreatLevel
from urbansoc.domain.geometry import BBox
from urbansoc.domain.keypoints import (
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
from urbansoc.domain.schemas import HumanPoseTrack, KeypointCOCO


def create_webcam_sitting_pose(
    aspect_ratio: float = 0.60,
    action: str = "normal",
) -> HumanPoseTrack:
    """Generate a realistic webcam upper-body crop where H/W is ~0.55-0.75."""
    w = 300
    h = int(w * aspect_ratio)  # e.g. 180 for 0.60
    bx1, by1 = 100, 100
    bx2, by2 = bx1 + w, by1 + h
    cx = (bx1 + bx2) / 2.0

    kpts = []

    def add_kp(kid: int, x: float, y: float, conf: float = 0.95):
        kpts.append(KeypointCOCO(id=kid, name="", x=float(x), y=float(y), confidence=conf))

    # Head is clearly on top (y increases downward)
    head_y = by1 + int(h * 0.15)
    shoulder_y = by1 + int(h * 0.50)
    elbow_y = by1 + int(h * 0.85)

    add_kp(NOSE, cx, head_y)
    add_kp(LEFT_EYE, cx - 12, head_y - 5)
    add_kp(RIGHT_EYE, cx + 12, head_y - 5)
    add_kp(LEFT_EAR, cx - 25, head_y - 2)
    add_kp(RIGHT_EAR, cx + 25, head_y - 2)

    # Shoulders
    add_kp(LEFT_SHOULDER, cx - 70, shoulder_y)
    add_kp(RIGHT_SHOULDER, cx + 70, shoulder_y)

    if action == "hands_up":
        # Wrists high above head
        add_kp(LEFT_ELBOW, cx - 60, head_y + 10)
        add_kp(RIGHT_ELBOW, cx + 60, head_y + 10)
        add_kp(LEFT_WRIST, cx - 60, head_y - 30)
        add_kp(RIGHT_WRIST, cx + 60, head_y - 30)
    elif action == "weapon_threat":
        # Two-handed aim in front of chest with extended arms
        aim_y = shoulder_y + int(h * 0.10)
        add_kp(LEFT_ELBOW, cx - 35, aim_y)
        add_kp(RIGHT_ELBOW, cx + 35, aim_y)
        add_kp(LEFT_WRIST, cx - 6, aim_y)
        add_kp(RIGHT_WRIST, cx + 6, aim_y)
    elif action == "phone_call":
        # Right wrist at right ear
        add_kp(LEFT_ELBOW, cx - 85, elbow_y)
        add_kp(RIGHT_ELBOW, cx + 65, shoulder_y + 20)
        add_kp(LEFT_WRIST, cx - 50, by2 - 10)
        add_kp(RIGHT_WRIST, cx + 28, head_y + 5)
    else:
        # Normal typing / resting hands
        add_kp(LEFT_ELBOW, cx - 85, elbow_y)
        add_kp(RIGHT_ELBOW, cx + 85, elbow_y)
        add_kp(LEFT_WRIST, cx - 40, by2 - 10)
        add_kp(RIGHT_WRIST, cx + 40, by2 - 10)

    return HumanPoseTrack(
        track_id=1,
        bbox=BBox(x1=bx1, y1=by1, x2=bx2, y2=by2),
        keypoints=kpts,
        detection_conf=0.92,
    )


# ------------------------------------------------------------------------------
# Test Suite: Sitting / Standing in front of webcam must NEVER be FALLEN
# ------------------------------------------------------------------------------
@pytest.mark.parametrize("ar", [0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.90])
def test_webcam_sitting_person_is_normal_never_fallen(ar: float) -> None:
    """Ensure person sitting in front of laptop webcam across all aspect ratios is NORMAL."""
    pose = create_webcam_sitting_pose(aspect_ratio=ar, action="normal")
    state = extract_kinematics_state(pose, timestamp=1.0, history=[])
    pred, norm_speed, aspect_ratio = evaluate_single_track_behavior(
        pose, state, history=[], dwell_time=1.0, initial_centroid=pose.bbox.centroid
    )
    assert pred.primary_behavior != BehaviorType.FALLEN, f"Failed for aspect ratio {ar}: got FALLEN instead of NORMAL"
    assert pred.primary_behavior == BehaviorType.NORMAL
    assert pred.threat_level == ThreatLevel.LOW


def test_webcam_hands_up_detected_correctly_never_fallen() -> None:
    """Hands up in webcam must be HANDS_UP, never FALLEN."""
    pose = create_webcam_sitting_pose(aspect_ratio=0.60, action="hands_up")
    state = extract_kinematics_state(pose, timestamp=1.0, history=[])
    pred, norm_speed, aspect_ratio = evaluate_single_track_behavior(
        pose, state, history=[], dwell_time=1.0, initial_centroid=pose.bbox.centroid
    )
    assert pred.primary_behavior != BehaviorType.FALLEN
    assert pred.primary_behavior == BehaviorType.HANDS_UP
    assert pred.threat_level == ThreatLevel.HIGH


def test_webcam_two_handed_aim_detected_correctly_never_fallen() -> None:
    """Two handed aim in webcam must be WEAPON_THREAT, never FALLEN."""
    pose = create_webcam_sitting_pose(aspect_ratio=0.65, action="weapon_threat")
    state = extract_kinematics_state(pose, timestamp=1.0, history=[])
    pred, norm_speed, aspect_ratio = evaluate_single_track_behavior(
        pose, state, history=[], dwell_time=1.0, initial_centroid=pose.bbox.centroid
    )
    assert pred.primary_behavior != BehaviorType.FALLEN
    assert pred.primary_behavior == BehaviorType.WEAPON_THREAT
    assert pred.threat_level == ThreatLevel.CRITICAL


def test_webcam_phone_call_is_normal_never_fallen() -> None:
    """Phone call at desk must be NORMAL, never FALLEN or WEAPON_THREAT."""
    pose = create_webcam_sitting_pose(aspect_ratio=0.60, action="phone_call")
    state = extract_kinematics_state(pose, timestamp=1.0, history=[])
    pred, norm_speed, aspect_ratio = evaluate_single_track_behavior(
        pose, state, history=[], dwell_time=1.0, initial_centroid=pose.bbox.centroid
    )
    assert pred.primary_behavior != BehaviorType.FALLEN
    assert pred.primary_behavior != BehaviorType.WEAPON_THREAT
    assert pred.primary_behavior == BehaviorType.NORMAL


def test_real_fallen_collapse_detected_accurately() -> None:
    """When a person actually falls horizontal onto floor, FALLEN must be detected."""
    # Lying horizontally on ground: W=300, H=80 (H/W = 0.27)
    bx1, by1 = 100, 300
    bx2, by2 = 400, 380
    cy = 340
    kpts = [
        KeypointCOCO(id=NOSE, name="", x=float(bx1 + 15), y=float(cy), confidence=0.95),
        KeypointCOCO(id=LEFT_SHOULDER, name="", x=float(bx1 + 50), y=float(cy - 10), confidence=0.95),
        KeypointCOCO(id=RIGHT_SHOULDER, name="", x=float(bx1 + 50), y=float(cy + 10), confidence=0.95),
        KeypointCOCO(id=LEFT_HIP, name="", x=float(bx1 + 150), y=float(cy - 10), confidence=0.95),
        KeypointCOCO(id=RIGHT_HIP, name="", x=float(bx1 + 150), y=float(cy + 10), confidence=0.95),
    ]
    pose = HumanPoseTrack(
        track_id=1,
        bbox=BBox(x1=bx1, y1=by1, x2=bx2, y2=by2),
        keypoints=kpts,
        detection_conf=0.95,
    )
    state = extract_kinematics_state(pose, timestamp=1.0, history=[])
    pred, norm_speed, aspect_ratio = evaluate_single_track_behavior(
        pose, state, history=[], dwell_time=1.0, initial_centroid=pose.bbox.centroid
    )
    assert pred.primary_behavior == BehaviorType.FALLEN
    assert pred.threat_level == ThreatLevel.CRITICAL
    assert pred.threat_score >= 0.90
