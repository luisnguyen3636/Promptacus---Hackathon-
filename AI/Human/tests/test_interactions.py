"""Unit tests for multi-person dangerous interaction analysis and anti-false-positive validation."""

import json
import os

from urbansoc.behavior.engine import BehaviorEngine
from urbansoc.behavior.interactions import analyze_multi_person_interactions
from urbansoc.domain.enums import BehaviorType, ThreatLevel
from urbansoc.domain.geometry import BBox


def test_fighting_detection_and_audit_event(tmp_path, synthetic_pose_factory):
    engine = BehaviorEngine(
        output_dir=str(tmp_path),
        fast_track_debounce_frames=6,
        fight_distance_norm=1.35,
        fight_wrist_energy_thresh=1200.0,
    )

    bbox1 = BBox.from_xywh(100, 100, 60, 150)
    bbox2 = BBox.from_xywh(140, 100, 60, 150)

    poses_output = []
    for step in range(10):
        t = 1.0 + step * 0.05
        p1 = synthetic_pose_factory(track_id=1, bbox=bbox1, spine_mode="upright", wrists_mode="fighting", step=step)
        p2 = synthetic_pose_factory(track_id=2, bbox=bbox2, spine_mode="upright", wrists_mode="fighting", step=step)

        poses_output, telemetry, alerts = engine.update([p1, p2], timestamp=t, frame_index=step)

    # After 10 frames (> 6 fast-track threshold), both subjects must be confirmed FIGHTING
    assert poses_output[0].behavior.primary_behavior == BehaviorType.FIGHTING
    assert poses_output[0].behavior.threat_level == ThreatLevel.CRITICAL
    assert poses_output[1].behavior.primary_behavior == BehaviorType.FIGHTING
    assert poses_output[1].behavior.threat_level == ThreatLevel.CRITICAL

    engine.close()

    # Verify audit event in JSONL
    jsonl_path = os.path.join(tmp_path, "behavior_events.jsonl")
    assert os.path.exists(jsonl_path)

    critical_events = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            data = json.loads(line.strip())
            if data.get("current_behavior") == "FIGHTING":
                critical_events.append(data)

    assert len(critical_events) >= 2
    assert critical_events[0]["event_type"] == "CRITICAL_ALERT"
    assert critical_events[0]["threat_level"] == "CRITICAL"
    assert critical_events[0]["threat_score"] >= 0.90


def test_anti_false_positive_walking_together(tmp_path, synthetic_pose_factory):
    """Ensure two people walking peacefully in close proximity are NOT falsely flagged as fighting."""
    engine = BehaviorEngine(output_dir=str(tmp_path))

    bbox1 = BBox.from_xywh(100, 100, 60, 150)
    bbox2 = BBox.from_xywh(145, 100, 60, 150)

    for step in range(15):
        t = 1.0 + step * 0.05
        # Normal walking posture with relaxed, low-speed wrists
        p1 = synthetic_pose_factory(track_id=1, bbox=bbox1, spine_mode="upright", wrists_mode="normal")
        p2 = synthetic_pose_factory(track_id=2, bbox=bbox2, spine_mode="upright", wrists_mode="normal")

        poses_output, _, _ = engine.update([p1, p2], timestamp=t, frame_index=step)

    assert poses_output[0].behavior.primary_behavior == BehaviorType.NORMAL
    assert poses_output[0].behavior.threat_level == ThreatLevel.LOW
    assert poses_output[1].behavior.primary_behavior == BehaviorType.NORMAL
    assert poses_output[1].behavior.threat_level == ThreatLevel.LOW
    engine.close()


def test_restraining_chokehold_detection(tmp_path, synthetic_pose_factory):
    """Detect sustained physical entanglement / chokehold grappling."""
    engine = BehaviorEngine(output_dir=str(tmp_path), fast_track_debounce_frames=6)

    # Heavy overlap: x=100 and x=115 -> IoU > 0.40
    bbox1 = BBox.from_xywh(100, 100, 60, 150)
    bbox2 = BBox.from_xywh(115, 100, 60, 150)

    for step in range(8):
        t = 1.0 + step * 0.05
        # Tangled with struggling arm motion
        p1 = synthetic_pose_factory(track_id=1, bbox=bbox1, spine_mode="upright", wrists_mode="fighting", step=step)
        p2 = synthetic_pose_factory(track_id=2, bbox=bbox2, spine_mode="upright", wrists_mode="fighting", step=step)

        poses_output, _, _ = engine.update([p1, p2], timestamp=t, frame_index=step)

    # Entangled bodies with high IoU commit RESTRAINING
    assert poses_output[0].behavior.primary_behavior in (BehaviorType.RESTRAINING, BehaviorType.FIGHTING)
    assert poses_output[0].behavior.threat_level == ThreatLevel.CRITICAL
    engine.close()


def test_pursuit_chase_detection(tmp_path, synthetic_pose_factory):
    """Detect two people in high-speed directional pursuit (same trajectory vector)."""
    engine = BehaviorEngine(output_dir=str(tmp_path), enter_debounce_frames=4)

    # Both moving rightward at high speed (40 px per frame)
    poses_output = []
    for step in range(8):
        t = 1.0 + step * 0.05
        # Subject 1 (runner/fleeing) ahead at x = 300 + step*40
        b1 = BBox.from_xywh(300 + step * 40.0, 100, 60, 150)
        # Subject 2 (chaser) behind at x = 160 + step*40 (distance ~140px, within 1.0 body height)
        b2 = BBox.from_xywh(160 + step * 40.0, 100, 60, 150)

        p1 = synthetic_pose_factory(track_id=1, bbox=b1, spine_mode="upright", speed_offset_x=step * 40.0)
        p2 = synthetic_pose_factory(track_id=2, bbox=b2, spine_mode="upright", speed_offset_x=step * 40.0)

        poses_output, _, _ = engine.update([p1, p2], timestamp=t, frame_index=step)

    assert poses_output[0].behavior.primary_behavior in (BehaviorType.PURSUIT, BehaviorType.RUNNING)
    assert poses_output[0].behavior.threat_level == ThreatLevel.HIGH
    engine.close()


def test_anti_false_positive_running_opposite_directions(tmp_path, synthetic_pose_factory):
    """Ensure two runners moving in opposite directions (passing by each other) are NOT flagged as PURSUIT."""
    engine = BehaviorEngine(output_dir=str(tmp_path))

    for step in range(6):
        t = 1.0 + step * 0.05
        # Subject 1 running rightward (+40 px/frame)
        b1 = BBox.from_xywh(100 + step * 40.0, 100, 60, 150)
        # Subject 2 running leftward (-40 px/frame)
        b2 = BBox.from_xywh(500 - step * 40.0, 100, 60, 150)

        p1 = synthetic_pose_factory(track_id=1, bbox=b1, spine_mode="upright")
        p2 = synthetic_pose_factory(track_id=2, bbox=b2, spine_mode="upright")

        poses_output, _, _ = engine.update([p1, p2], timestamp=t, frame_index=step)

    # Must be RUNNING, NOT PURSUIT
    assert poses_output[0].behavior.primary_behavior != BehaviorType.PURSUIT
    assert poses_output[1].behavior.primary_behavior != BehaviorType.PURSUIT
    engine.close()


def test_surrounding_mob_detection(tmp_path, synthetic_pose_factory):
    """Detect when 3+ people encircle a single target subject."""
    engine = BehaviorEngine(output_dir=str(tmp_path), enter_debounce_frames=4)

    # Target subject at center (300, 200)
    target_box = BBox.from_xywh(300, 200, 60, 150)
    # Attacker 1 at left
    att1_box = BBox.from_xywh(180, 200, 60, 150)
    # Attacker 2 at right
    att2_box = BBox.from_xywh(420, 200, 60, 150)
    # Attacker 3 behind
    att3_box = BBox.from_xywh(300, 120, 60, 150)

    for step in range(6):
        t = 1.0 + step * 0.05
        p_target = synthetic_pose_factory(track_id=10, bbox=target_box)
        p1 = synthetic_pose_factory(track_id=1, bbox=att1_box)
        p2 = synthetic_pose_factory(track_id=2, bbox=att2_box)
        p3 = synthetic_pose_factory(track_id=3, bbox=att3_box)

        poses_output, _, _ = engine.update([p_target, p1, p2, p3], timestamp=t, frame_index=step)

    target_res = next(p for p in poses_output if p.track_id == 10)
    assert target_res.behavior.primary_behavior == BehaviorType.SURROUNDING
    assert target_res.behavior.threat_level == ThreatLevel.HIGH
    engine.close()
