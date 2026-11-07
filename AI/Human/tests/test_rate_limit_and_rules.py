"""Unit tests for Anti-False-Positive Biometric Rule refinement and Sliding Window Rate Limiting."""

import time
from typing import List

from urbansoc.behavior.kinematics import extract_kinematics_state
from urbansoc.behavior.rules import evaluate_single_track_behavior
from urbansoc.domain.enums import BehaviorType, ThreatLevel
from urbansoc.domain.geometry import BBox
from urbansoc.domain.keypoints import (
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
from urbansoc.domain.schemas import HumanPoseTrack, KeypointCOCO
from urbansoc.telemetry.webhook_dispatcher import EventThrottler


def _create_webcam_seated_pose(track_id: int = 1) -> HumanPoseTrack:
    """Simulate a typical laptop webcam bust crop (head + shoulders, H < W)."""
    # Width = 250, Height = 200 -> Aspect Ratio = 200/250 = 0.80 (< 0.90)
    bbox = BBox.from_xyxy(100, 100, 350, 300)
    kpts: List[KeypointCOCO] = [
        KeypointCOCO(id=NOSE, name="nose", x=225.0, y=130.0, confidence=0.95),
        KeypointCOCO(id=LEFT_EYE, name="left_eye", x=215.0, y=125.0, confidence=0.95),
        KeypointCOCO(id=RIGHT_EYE, name="right_eye", x=235.0, y=125.0, confidence=0.95),
        KeypointCOCO(id=LEFT_SHOULDER, name="left_shoulder", x=160.0, y=185.0, confidence=0.92),
        KeypointCOCO(id=RIGHT_SHOULDER, name="right_shoulder", x=290.0, y=185.0, confidence=0.92),
        KeypointCOCO(id=LEFT_ELBOW, name="left_elbow", x=140.0, y=250.0, confidence=0.85),
        KeypointCOCO(id=RIGHT_ELBOW, name="right_elbow", x=310.0, y=250.0, confidence=0.85),
        KeypointCOCO(id=LEFT_WRIST, name="left_wrist", x=160.0, y=285.0, confidence=0.80),
        KeypointCOCO(id=RIGHT_WRIST, name="right_wrist", x=290.0, y=285.0, confidence=0.80),
    ]
    return HumanPoseTrack(
        track_id=track_id,
        bbox=bbox,
        detection_conf=0.92,
        keypoints=kpts,
    )


def test_webcam_crop_anti_false_positive_not_fallen():
    """Verify that a person sitting upright in front of a laptop webcam is NOT misclassified as FALLEN."""
    pose = _create_webcam_seated_pose(track_id=1)
    state = extract_kinematics_state(pose, timestamp=1.0, history=[])
    pred, norm_speed, aspect_ratio = evaluate_single_track_behavior(
        pose, state, history=[], dwell_time=1.0, initial_centroid=pose.bbox.centroid
    )

    # Must NOT be FALLEN
    assert pred.primary_behavior != BehaviorType.FALLEN, f"False positive FALLEN detected! Reasoning: {pred.reasoning}"
    # Must be NORMAL
    assert pred.primary_behavior == BehaviorType.NORMAL
    assert pred.threat_level == ThreatLevel.LOW
    assert pred.threat_score <= 0.20


def test_webcam_seated_long_duration_not_critical():
    """Verify that staying seated in front of laptop for 35s is not escalated to Critical/High."""
    pose = _create_webcam_seated_pose(track_id=1)
    history = [extract_kinematics_state(pose, timestamp=float(i), history=[]) for i in range(25)]
    state = history[-1]

    pred, _, _ = evaluate_single_track_behavior(
        pose, state, history=history, dwell_time=35.0, initial_centroid=pose.bbox.centroid
    )

    # Must remain LOW / NORMAL
    assert pred.primary_behavior == BehaviorType.NORMAL
    assert pred.threat_level == ThreatLevel.LOW
    assert pred.threat_score <= 0.25


def test_true_fallen_horizontal_spine_angle():
    """Verify that actual fall with horizontal spine angle is correctly detected as CRITICAL FALLEN."""
    bbox = BBox.from_xyxy(50, 200, 350, 280)  # Horizontal prone body
    # Shoulders at left, hips at right -> spine vector is horizontal
    kpts: List[KeypointCOCO] = [
        KeypointCOCO(id=NOSE, name="nose", x=60.0, y=240.0, confidence=0.95),
        KeypointCOCO(id=LEFT_SHOULDER, name="left_shoulder", x=100.0, y=230.0, confidence=0.95),
        KeypointCOCO(id=RIGHT_SHOULDER, name="right_shoulder", x=100.0, y=250.0, confidence=0.95),
        KeypointCOCO(id=LEFT_HIP, name="left_hip", x=220.0, y=230.0, confidence=0.95),
        KeypointCOCO(id=RIGHT_HIP, name="right_hip", x=220.0, y=250.0, confidence=0.95),
    ]
    pose = HumanPoseTrack(track_id=2, bbox=bbox, detection_conf=0.95, keypoints=kpts)
    state = extract_kinematics_state(pose, timestamp=1.0, history=[])

    assert state.spine_angle >= 55.0, f"Spine angle should be high horizontal, got: {state.spine_angle}"

    pred, _, _ = evaluate_single_track_behavior(
        pose, state, history=[], dwell_time=1.0, initial_centroid=pose.bbox.centroid
    )
    assert pred.primary_behavior == BehaviorType.FALLEN
    assert pred.threat_level == ThreatLevel.CRITICAL
    assert pred.threat_score >= 0.95


def test_true_fallen_head_collapsed_below_shoulders():
    """Verify that someone collapsed forward face-down (head level/below shoulders) triggers FALLEN."""
    bbox = BBox.from_xyxy(100, 100, 300, 220)  # aspect ratio = 120/200 = 0.60
    # Head is lower (higher y in OpenCV) than shoulders
    kpts: List[KeypointCOCO] = [
        KeypointCOCO(id=NOSE, name="nose", x=200.0, y=210.0, confidence=0.95),  # y=210 > y=150
        KeypointCOCO(id=LEFT_SHOULDER, name="left_shoulder", x=140.0, y=150.0, confidence=0.95),
        KeypointCOCO(id=RIGHT_SHOULDER, name="right_shoulder", x=260.0, y=150.0, confidence=0.95),
    ]
    pose = HumanPoseTrack(track_id=3, bbox=bbox, detection_conf=0.95, keypoints=kpts)
    state = extract_kinematics_state(pose, timestamp=1.0, history=[])

    pred, _, _ = evaluate_single_track_behavior(
        pose, state, history=[], dwell_time=1.0, initial_centroid=pose.bbox.centroid
    )
    assert pred.primary_behavior == BehaviorType.FALLEN
    assert pred.threat_level == ThreatLevel.CRITICAL


def test_rate_limiter_max_requests_per_minute_and_cooldown():
    """Verify that EventThrottler limits dispatching to at most 3 req/minute and respects 25s cooldown."""
    throttler = EventThrottler(default_cooldown=25.0, max_requests_per_minute=3)
    t = 100.0

    # Request 1 at t=100s -> Accepted
    assert throttler.should_dispatch(track_id=1, behavior="WEAPON_THREAT", threat_level=ThreatLevel.CRITICAL, now=t) is True

    # Immediate duplicate at t=101s -> Rejected (cooldown not met)
    assert throttler.should_dispatch(track_id=1, behavior="WEAPON_THREAT", threat_level=ThreatLevel.CRITICAL, now=t + 1.0) is False

    # At t=120s (20s later) -> Rejected (20s < 25s cooldown)
    assert throttler.should_dispatch(track_id=1, behavior="WEAPON_THREAT", threat_level=ThreatLevel.CRITICAL, now=t + 20.0) is False

    # Request 2 at t=126s (26s later) -> Accepted (cooldown 25s passed)
    assert throttler.should_dispatch(track_id=1, behavior="WEAPON_THREAT", threat_level=ThreatLevel.CRITICAL, now=t + 26.0) is True

    # Request 3 at t=152s (26s later) -> Accepted (3rd request within 60s)
    assert throttler.should_dispatch(track_id=1, behavior="WEAPON_THREAT", threat_level=ThreatLevel.CRITICAL, now=t + 52.0) is True

    # Request 4 at t=155s -> Rejected (cooldown not met)
    assert throttler.should_dispatch(track_id=1, behavior="WEAPON_THREAT", threat_level=ThreatLevel.CRITICAL, now=t + 55.0) is False

    # Request 4 at t=158s (even if cooldown passed, say t=158s) -> Rate limit of 3 req/min reached!
    assert throttler.should_dispatch(track_id=1, behavior="WEAPON_THREAT", threat_level=ThreatLevel.CRITICAL, now=t + 58.0) is False

    # Request 4 at t=177s (25s after Request 3 at t=152s) -> Request 1 (at t=100s) has aged out (>60s ago)!
    # Now window only has Requests 2 & 3, and cooldown (177 - 152 = 25s) is satisfied -> Accepted!
    assert throttler.should_dispatch(track_id=1, behavior="WEAPON_THREAT", threat_level=ThreatLevel.CRITICAL, now=t + 77.0) is True
