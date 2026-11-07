"""Unit tests verifying all single-subject behavior classification rules and anti-false-positive filters."""

from urbansoc.behavior.kinematics import extract_kinematics_state
from urbansoc.behavior.rules import evaluate_single_track_behavior
from urbansoc.domain.enums import BehaviorType, ThreatLevel


def test_rule_normal(synthetic_pose_factory):
    pose = synthetic_pose_factory(track_id=1, spine_mode="upright", wrists_mode="normal")
    state = extract_kinematics_state(pose, timestamp=1.0, history=[])
    pred, norm_speed, aspect_ratio = evaluate_single_track_behavior(
        pose, state, history=[], dwell_time=1.0, initial_centroid=pose.bbox.centroid
    )
    assert pred.primary_behavior == BehaviorType.NORMAL
    assert pred.threat_level == ThreatLevel.LOW
    assert pred.threat_score <= 0.20


def test_rule_fallen(synthetic_pose_factory):
    pose = synthetic_pose_factory(track_id=1, spine_mode="fallen")
    state = extract_kinematics_state(pose, timestamp=1.0, history=[])
    pred, norm_speed, aspect_ratio = evaluate_single_track_behavior(
        pose, state, history=[], dwell_time=1.0, initial_centroid=pose.bbox.centroid
    )
    assert pred.primary_behavior == BehaviorType.FALLEN
    assert pred.threat_level == ThreatLevel.CRITICAL
    assert pred.threat_score >= 0.90


def test_rule_weapon_threat_two_handed_aim(synthetic_pose_factory):
    pose = synthetic_pose_factory(track_id=1, spine_mode="upright", wrists_mode="two_handed_aim")
    state = extract_kinematics_state(pose, timestamp=1.0, history=[])
    pred, norm_speed, aspect_ratio = evaluate_single_track_behavior(
        pose, state, history=[], dwell_time=1.0, initial_centroid=pose.bbox.centroid
    )
    assert pred.primary_behavior == BehaviorType.WEAPON_THREAT
    assert pred.threat_level == ThreatLevel.CRITICAL
    assert pred.threat_score >= 0.95
    assert "Two-handed tactical weapon" in pred.reasoning


def test_rule_weapon_threat_single_arm_pointing(synthetic_pose_factory):
    pose = synthetic_pose_factory(track_id=1, spine_mode="upright", wrists_mode="weapon_pointing")
    state = extract_kinematics_state(pose, timestamp=1.0, history=[])
    pred, norm_speed, aspect_ratio = evaluate_single_track_behavior(
        pose, state, history=[], dwell_time=1.0, initial_centroid=pose.bbox.centroid
    )
    assert pred.primary_behavior == BehaviorType.WEAPON_THREAT
    assert pred.threat_level == ThreatLevel.CRITICAL
    assert pred.threat_score >= 0.90
    assert "Direct one-handed weapon pointing" in pred.reasoning


def test_anti_false_positive_phone_call(synthetic_pose_factory):
    # Subject holding phone to ear: sharp elbow angle, near head
    pose = synthetic_pose_factory(track_id=1, spine_mode="upright", wrists_mode="phone_call")
    state = extract_kinematics_state(pose, timestamp=1.0, history=[])
    pred, norm_speed, aspect_ratio = evaluate_single_track_behavior(
        pose, state, history=[], dwell_time=1.0, initial_centroid=pose.bbox.centroid
    )
    # Must NOT be classified as WEAPON_THREAT
    assert pred.primary_behavior != BehaviorType.WEAPON_THREAT
    assert pred.primary_behavior == BehaviorType.NORMAL
    assert pred.threat_level == ThreatLevel.LOW


def test_rule_intrusion_climbing(synthetic_pose_factory):
    # Simulate upward climbing kinematics: ankles rising vertically
    history = []
    pose = None
    for i in range(12):
        t = 1.0 + i * 0.05
        # Upward climbing motion: y decreases by 5px per frame (total 55px upward)
        pose = synthetic_pose_factory(track_id=1, spine_mode="upright", wrists_mode="hands_up")
        # Shift keypoint y coordinates upward
        for kp in pose.keypoints:
            kp.y -= (i * 5.0)
        state = extract_kinematics_state(pose, timestamp=t, history=history)
        history.append(state)

    pred, norm_speed, aspect_ratio = evaluate_single_track_behavior(
        pose, history[-1], history=history, dwell_time=1.0, initial_centroid=pose.bbox.centroid
    )
    assert pred.primary_behavior == BehaviorType.INTRUSION
    assert pred.threat_level == ThreatLevel.HIGH
    assert pred.threat_score >= 0.80


def test_rule_hands_up(synthetic_pose_factory):
    pose = synthetic_pose_factory(track_id=1, spine_mode="upright", wrists_mode="hands_up")
    state = extract_kinematics_state(pose, timestamp=1.0, history=[])
    pred, norm_speed, aspect_ratio = evaluate_single_track_behavior(
        pose, state, history=[], dwell_time=1.0, initial_centroid=pose.bbox.centroid
    )
    assert pred.primary_behavior == BehaviorType.HANDS_UP
    assert pred.threat_level == ThreatLevel.HIGH
    assert pred.threat_score >= 0.70


def test_rule_running(synthetic_pose_factory):
    history = []
    pose = None
    for i in range(6):
        t = 1.0 + i * 0.05
        # Move 45 pixels per frame with body height ~150px
        pose = synthetic_pose_factory(
            track_id=1, spine_mode="upright", speed_offset_x=i * 45.0
        )
        state = extract_kinematics_state(pose, timestamp=t, history=history)
        history.append(state)

    pred, norm_speed, aspect_ratio = evaluate_single_track_behavior(
        pose, history[-1], history=history, dwell_time=2.0, initial_centroid=(100.0, 100.0)
    )
    assert norm_speed >= 1.75
    assert pred.primary_behavior == BehaviorType.RUNNING
    assert pred.threat_level == ThreatLevel.HIGH


def test_rule_crouching(synthetic_pose_factory):
    pose = synthetic_pose_factory(track_id=1, spine_mode="crouching")
    state = extract_kinematics_state(pose, timestamp=1.0, history=[])
    pred, norm_speed, aspect_ratio = evaluate_single_track_behavior(
        pose, state, history=[], dwell_time=1.0, initial_centroid=pose.bbox.centroid
    )
    assert pred.primary_behavior == BehaviorType.CROUCHING
    assert pred.threat_level == ThreatLevel.MEDIUM


def test_rule_loitering(synthetic_pose_factory):
    history = []
    pose = synthetic_pose_factory(track_id=1, spine_mode="upright")
    for i in range(25):
        t = 1.0 + i * 0.05
        state = extract_kinematics_state(pose, timestamp=t, history=history)
        history.append(state)

    # dwell_time = 12.0s (> 10s threshold)
    pred, norm_speed, aspect_ratio = evaluate_single_track_behavior(
        pose,
        history[-1],
        history=history,
        dwell_time=12.0,
        initial_centroid=pose.bbox.centroid,
    )
    assert pred.primary_behavior == BehaviorType.LOITERING
    assert pred.threat_level == ThreatLevel.MEDIUM

    # dwell_time = 22.0s (> 20s threshold -> ThreatLevel.HIGH)
    pred_high, _, _ = evaluate_single_track_behavior(
        pose,
        history[-1],
        history=history,
        dwell_time=22.0,
        initial_centroid=pose.bbox.centroid,
    )
    assert pred_high.primary_behavior == BehaviorType.LOITERING
    assert pred_high.threat_level == ThreatLevel.HIGH
