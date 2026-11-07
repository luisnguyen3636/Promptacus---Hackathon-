"""Unit and integration tests for Multi-Person Interactions, Combat / Fighting Role Attribution, and False-Positive Mitigation."""

import time
from typing import List

import numpy as np
import pytest

from urbansoc.behavior.engine import BehaviorEngine
from urbansoc.behavior.interactions import analyze_multi_person_interactions
from urbansoc.behavior.kinematics import extract_kinematics_state
from urbansoc.behavior.rules import evaluate_single_track_behavior
from urbansoc.domain.enums import BehaviorType, ThreatLevel
from urbansoc.domain.geometry import BBox
from urbansoc.domain.keypoints import (
    LEFT_ELBOW,
    LEFT_HIP,
    LEFT_SHOULDER,
    LEFT_WRIST,
    NOSE,
    RIGHT_ELBOW,
    RIGHT_HIP,
    RIGHT_SHOULDER,
    RIGHT_WRIST,
)
from urbansoc.domain.schemas import HumanPoseTrack, KeypointCOCO, SOCFrameAnalysisResult
from urbansoc.domain.synthetic import create_synthetic_pose
from urbansoc.domain.webhook_models import CameraLocationConfig, WebhookIncidentPayload


def _create_punching_pose(
    track_id: int,
    base_x: float,
    base_y: float = 100.0,
    target_x: float = 240.0,
    step: int = 0,
) -> HumanPoseTrack:
    """Create a realistic punching pose with one fist extending rapidly towards target_x."""
    bbox = BBox.from_xywh(base_x, base_y, 70, 160)
    # Right arm punches forward towards target_x with rapid strike velocity
    punch_dir = 1.0 if target_x > base_x else -1.0
    # Oscillate punch extension while remaining in forward striking reach of target
    punch_ext = 55.0 if (step % 2 == 1) else 25.0
    rw_x = base_x + 35.0 + punch_dir * punch_ext

    kpts: List[KeypointCOCO] = [
        KeypointCOCO(id=NOSE, name="nose", x=base_x + 35.0, y=base_y + 20.0, confidence=0.95),
        KeypointCOCO(id=LEFT_SHOULDER, name="left_shoulder", x=base_x + 15.0, y=base_y + 40.0, confidence=0.92),
        KeypointCOCO(id=RIGHT_SHOULDER, name="right_shoulder", x=base_x + 55.0, y=base_y + 40.0, confidence=0.92),
        KeypointCOCO(id=LEFT_ELBOW, name="left_elbow", x=base_x + 10.0, y=base_y + 75.0, confidence=0.88),
        KeypointCOCO(id=RIGHT_ELBOW, name="right_elbow", x=base_x + 65.0, y=base_y + 55.0, confidence=0.88),
        KeypointCOCO(id=LEFT_WRIST, name="left_wrist", x=base_x + 20.0, y=base_y + 80.0, confidence=0.85),
        KeypointCOCO(id=RIGHT_WRIST, name="right_wrist", x=rw_x, y=base_y + 45.0, confidence=0.90),
    ]
    return HumanPoseTrack(track_id=track_id, bbox=bbox, detection_conf=0.95, keypoints=kpts)


def _create_victim_pose(
    track_id: int,
    base_x: float,
    base_y: float = 100.0,
    recoil: float = 0.0,
) -> HumanPoseTrack:
    """Create a victim pose recoiling/covering head."""
    bbox = BBox.from_xywh(base_x + recoil, base_y, 65, 160)
    kpts: List[KeypointCOCO] = [
        KeypointCOCO(id=NOSE, name="nose", x=base_x + recoil + 30.0, y=base_y + 25.0, confidence=0.95),
        KeypointCOCO(id=LEFT_SHOULDER, name="left_shoulder", x=base_x + recoil + 15.0, y=base_y + 45.0, confidence=0.92),
        KeypointCOCO(id=RIGHT_SHOULDER, name="right_shoulder", x=base_x + recoil + 50.0, y=base_y + 45.0, confidence=0.92),
        KeypointCOCO(id=LEFT_ELBOW, name="left_elbow", x=base_x + recoil + 20.0, y=base_y + 60.0, confidence=0.85),
        KeypointCOCO(id=RIGHT_ELBOW, name="right_elbow", x=base_x + recoil + 45.0, y=base_y + 60.0, confidence=0.85),
        # Hands up defending face
        KeypointCOCO(id=LEFT_WRIST, name="left_wrist", x=base_x + recoil + 25.0, y=base_y + 35.0, confidence=0.90),
        KeypointCOCO(id=RIGHT_WRIST, name="right_wrist", x=base_x + recoil + 40.0, y=base_y + 35.0, confidence=0.90),
        KeypointCOCO(id=LEFT_HIP, name="left_hip", x=base_x + recoil + 18.0, y=base_y + 110.0, confidence=0.90),
        KeypointCOCO(id=RIGHT_HIP, name="right_hip", x=base_x + recoil + 48.0, y=base_y + 110.0, confidence=0.90),
    ]
    return HumanPoseTrack(track_id=track_id, bbox=bbox, detection_conf=0.95, keypoints=kpts)


def _create_bystander_pose(
    track_id: int,
    base_x: float = 480.0,
    base_y: float = 100.0,
) -> HumanPoseTrack:
    """Create a stationary bystander observing from a distance."""
    bbox = BBox.from_xywh(base_x, base_y, 60, 160)
    kpts: List[KeypointCOCO] = [
        KeypointCOCO(id=NOSE, name="nose", x=base_x + 30.0, y=base_y + 20.0, confidence=0.95),
        KeypointCOCO(id=LEFT_SHOULDER, name="left_shoulder", x=base_x + 15.0, y=base_y + 45.0, confidence=0.92),
        KeypointCOCO(id=RIGHT_SHOULDER, name="right_shoulder", x=base_x + 45.0, y=base_y + 45.0, confidence=0.92),
        KeypointCOCO(id=LEFT_ELBOW, name="left_elbow", x=base_x + 15.0, y=base_y + 80.0, confidence=0.85),
        KeypointCOCO(id=RIGHT_ELBOW, name="right_elbow", x=base_x + 45.0, y=base_y + 80.0, confidence=0.85),
        KeypointCOCO(id=LEFT_WRIST, name="left_wrist", x=base_x + 15.0, y=base_y + 115.0, confidence=0.85),
        KeypointCOCO(id=RIGHT_WRIST, name="right_wrist", x=base_x + 45.0, y=base_y + 115.0, confidence=0.85),
    ]
    return HumanPoseTrack(track_id=track_id, bbox=bbox, detection_conf=0.95, keypoints=kpts)


def test_three_person_scene_attacker_victim_bystander_attribution(tmp_path):
    """Verify that in a 3-person scene:

    Track #1 (Attacker) hitting Track #2 (Victim) is detected as FIGHTING (CRITICAL) with roles assigned.
    Track #3 (Bystander standing 300px away) is identified as NORMAL (LOW) BYSTANDER.
    """
    engine = BehaviorEngine(
        output_dir=str(tmp_path),
        fast_track_debounce_frames=4,
    )

    poses_output = []
    # Stream 8 frames of Track 1 punching Track 2 while Track 3 observes
    for step in range(8):
        t = 1.0 + step * 0.066  # ~15 FPS
        p1 = _create_punching_pose(track_id=1, base_x=120.0, target_x=220.0, step=step)
        p2 = _create_victim_pose(track_id=2, base_x=220.0, recoil=float(min(12.0, step * 2.0)))
        p3 = _create_bystander_pose(track_id=3, base_x=480.0)

        poses_output, telemetry, alerts = engine.update([p1, p2, p3], timestamp=t, frame_index=step)

    p1_res = [p for p in poses_output if p.track_id == 1][0]
    p2_res = [p for p in poses_output if p.track_id == 2][0]
    p3_res = [p for p in poses_output if p.track_id == 3][0]

    # Person A (Track 1) must be FIGHTING / ATTACKER targeting #2
    assert p1_res.behavior.primary_behavior == BehaviorType.FIGHTING
    assert p1_res.behavior.threat_level == ThreatLevel.CRITICAL
    assert p1_res.behavior.interacting_with_track_id == 2
    assert getattr(p1_res.behavior, "role") == "attacker"

    # Person B (Track 2) must be FIGHTING / VICTIM targeted by #1
    assert p2_res.behavior.primary_behavior == BehaviorType.FIGHTING
    assert p2_res.behavior.threat_level == ThreatLevel.CRITICAL
    assert p2_res.behavior.interacting_with_track_id == 1
    assert getattr(p2_res.behavior, "role") == "victim"

    # Person C (Track 3) must be NORMAL / BYSTANDER
    assert p3_res.behavior.primary_behavior == BehaviorType.NORMAL
    assert p3_res.behavior.threat_level == ThreatLevel.LOW
    assert getattr(p3_res.behavior, "role") == "bystander"

    engine.close()


def test_mutual_combat_brawl_both_striking(tmp_path):
    """Verify that when both subjects throw punches at each other, both are identified as mutual_combatants."""
    engine = BehaviorEngine(
        output_dir=str(tmp_path),
        fast_track_debounce_frames=4,
    )

    poses_output = []
    for step in range(8):
        t = 1.0 + step * 0.066
        # Both throw punches at each other
        p1 = _create_punching_pose(track_id=1, base_x=120.0, target_x=220.0, step=step)
        p2 = _create_punching_pose(track_id=2, base_x=220.0, target_x=120.0, step=step)

        poses_output, _, _ = engine.update([p1, p2], timestamp=t, frame_index=step)

    p1_res = [p for p in poses_output if p.track_id == 1][0]
    p2_res = [p for p in poses_output if p.track_id == 2][0]

    assert p1_res.behavior.primary_behavior == BehaviorType.FIGHTING
    assert p1_res.behavior.threat_level == ThreatLevel.CRITICAL
    assert getattr(p1_res.behavior, "role") in ("mutual_combatant", "attacker")

    assert p2_res.behavior.primary_behavior == BehaviorType.FIGHTING
    assert p2_res.behavior.threat_level == ThreatLevel.CRITICAL
    assert getattr(p2_res.behavior, "role") in ("mutual_combatant", "attacker")

    engine.close()


def test_anti_false_positive_three_people_peaceful_conversation(tmp_path):
    """Verify that 3 people standing peacefully in close proximity having a normal conversation

    are NOT falsely triggered as fighting or loitering.
    """
    engine = BehaviorEngine(output_dir=str(tmp_path))

    poses_output = []
    for step in range(12):
        t = 1.0 + step * 0.066
        p1 = _create_bystander_pose(track_id=1, base_x=140.0)
        p2 = _create_bystander_pose(track_id=2, base_x=220.0)
        p3 = _create_bystander_pose(track_id=3, base_x=300.0)

        poses_output, _, _ = engine.update([p1, p2, p3], timestamp=t, frame_index=step)

    for p in poses_output:
        assert p.behavior.primary_behavior == BehaviorType.NORMAL
        assert p.behavior.threat_level == ThreatLevel.LOW

    engine.close()


def test_anti_false_positive_webcam_standing_presence_not_loitering_high():
    """Verify that a subject standing upright in webcam view for > 25 seconds

    is NOT falsely elevated to LOITERING HIGH alert.
    """
    bbox = BBox.from_xyxy(100, 80, 260, 380)
    # Head and shoulders tracked, no legs visible in webcam view
    kpts: List[KeypointCOCO] = [
        KeypointCOCO(id=NOSE, name="nose", x=180.0, y=110.0, confidence=0.95),
        KeypointCOCO(id=LEFT_SHOULDER, name="left_shoulder", x=130.0, y=160.0, confidence=0.92),
        KeypointCOCO(id=RIGHT_SHOULDER, name="right_shoulder", x=230.0, y=160.0, confidence=0.92),
        KeypointCOCO(id=LEFT_WRIST, name="left_wrist", x=140.0, y=280.0, confidence=0.85),
        KeypointCOCO(id=RIGHT_WRIST, name="right_wrist", x=220.0, y=280.0, confidence=0.85),
    ]
    pose = HumanPoseTrack(track_id=1, bbox=bbox, detection_conf=0.94, keypoints=kpts)

    history = []
    for step in range(25):
        t = 1.0 + step * 0.05
        state = extract_kinematics_state(pose, timestamp=t, history=history)
        history.append(state)

    pred, _, _ = evaluate_single_track_behavior(
        pose,
        history[-1],
        history=history,
        dwell_time=35.0,  # 35 seconds standing in front of webcam
        initial_centroid=pose.bbox.centroid,
    )

    # Must remain NORMAL with LOW threat, not spamming LOITERING HIGH
    assert pred.threat_level == ThreatLevel.LOW
    assert pred.primary_behavior == BehaviorType.NORMAL


def test_multi_person_webhook_payload_summary():
    """Verify WebhookIncidentPayload properly formats multi-person interaction roles in title and prompt."""
    from urbansoc.domain.webhook_models import SubjectCropData

    sub1 = SubjectCropData(
        track_id=1,
        role="attacker",
        behavior="FIGHTING",
        threat_level="CRITICAL",
        threat_score=0.98,
        confidence=0.95,
        bbox=[100, 100, 170, 260],
        bbox_width=70,
        bbox_height=160,
        bbox_aspect_ratio=2.28,
        bbox_area=11200,
        dwell_time_seconds=5.0,
        speed=0.1,
        velocity_vector=[0.0, 0.0],
        kinematics={"spine_angle": 5.0, "wrist_velocity": 450.0},
        keypoints=[],
        crop_image_base64="data:image/jpeg;base64,sub1",
        crop_image_sha256="sha1",
        crop_image_size_bytes=100,
        interacting_with_track_id=2,
    )
    sub2 = SubjectCropData(
        track_id=2,
        role="victim",
        behavior="FIGHTING",
        threat_level="CRITICAL",
        threat_score=0.92,
        confidence=0.95,
        bbox=[200, 100, 270, 260],
        bbox_width=70,
        bbox_height=160,
        bbox_aspect_ratio=2.28,
        bbox_area=11200,
        dwell_time_seconds=5.0,
        speed=0.1,
        velocity_vector=[0.0, 0.0],
        kinematics={"spine_angle": 18.0, "wrist_velocity": 120.0},
        keypoints=[],
        crop_image_base64="data:image/jpeg;base64,sub2",
        crop_image_sha256="sha2",
        crop_image_size_bytes=100,
        interacting_with_track_id=1,
    )
    sub3 = SubjectCropData(
        track_id=3,
        role="bystander",
        behavior="NORMAL",
        threat_level="LOW",
        threat_score=0.10,
        confidence=0.95,
        bbox=[450, 100, 510, 260],
        bbox_width=60,
        bbox_height=160,
        bbox_aspect_ratio=2.67,
        bbox_area=9600,
        dwell_time_seconds=5.0,
        speed=0.0,
        velocity_vector=[0.0, 0.0],
        kinematics={"spine_angle": 2.0, "wrist_velocity": 30.0},
        keypoints=[],
        crop_image_base64="data:image/jpeg;base64,sub3",
        crop_image_sha256="sha3",
        crop_image_size_bytes=100,
        interacting_with_track_id=None,
    )

    cam_cfg = CameraLocationConfig(camera_id="CAM_TEST", name="Test Cam")
    payload = WebhookIncidentPayload(
        event_id="EVT_MULTI_TEST",
        timestamp="2026-11-07T21:00:00",
        timestamp_ms=1000,
        camera=cam_cfg,
        primary_action="FIGHTING",
        threat_level="CRITICAL",
        threat_score=0.98,
        is_urgent=True,
        reasoning="Physical altercation",
        weapon={"is_weapon_detected": False},
        subjects=[sub1, sub2, sub3],
        full_image={"image_base64": "data:image/jpeg;base64,full"},
    )

    p_dict = payload.to_dict()
    assert "Assault Incident: Attacker (#1) striking Victim (#2)" in p_dict["title"]
    assert "Observing Bystander: #3" in p_dict["title"]
    assert "Multi-person dynamic: Assault Incident: Attacker (#1) striking Victim (#2)" in p_dict["ai_prompt"]
    assert len(p_dict["detection"]["subjects"]) == 3
    assert p_dict["detection"]["subjects"][0]["role"] == "attacker"
    assert p_dict["detection"]["subjects"][1]["role"] == "victim"
    assert p_dict["detection"]["subjects"][2]["role"] == "bystander"
