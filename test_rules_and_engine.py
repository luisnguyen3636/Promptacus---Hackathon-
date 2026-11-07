"""
Automated Verification & Test Suite for Urban Safety AI-SOC:
Rule System (Rule/) and Threat Marking Engine (Engine/).
Adheres strictly to PLAN-URBAN-RULE-ENGINE-01 verification plan.
"""

import math
import json
import time
from typing import Dict, List, Tuple

from Engine.threat_models import (
    ThreatLevel,
    BehaviorType,
    BehaviorCategory,
    KeypointData,
    SubjectKinematicsSnapshot,
    SOCEngineOutput
)
from Engine.threat_engine import ThreatMarkingEngine
from Rule.registry import RuleRegistry
from Rule.single_rules import (
    FallenCollapseRule,
    HandsUpDistressRule,
    SuddenFleeingRule,
    CrouchingProwlingRule,
    LoiteringRule,
    ConcealedReachRule
)
from Rule.multi_rules import (
    FightingStrikeRule,
    GrapplingStruggleRule,
    ChasingPursuitRule,
    SurroundedVictimRule
)


def create_mock_snapshot(
    track_id: int,
    bbox: Tuple[int, int, int, int] = (100, 100, 180, 300),
    spine_angle_deg: float = 10.0,
    aspect_ratio: float = 2.5,
    velocity_norm: float = 0.2,
    wrist_kinetic_energy: float = 100.0,
    dwell_time_seconds: float = 1.0,
    timestamp: float = 1000.0,
    wrist_mode: str = "normal",
    head_y: float = 120.0
) -> SubjectKinematicsSnapshot:
    """Helper to generate synthetic subject kinematics snapshots for testing."""
    x1, y1, x2, y2 = bbox
    cx = (x1 + x2) / 2.0
    cy = (y1 + y2) / 2.0
    h = max(1, y2 - y1)

    kps: Dict[int, KeypointData] = {
        0: KeypointData(id=0, name="nose", x=cx, y=head_y, confidence=0.95),
        5: KeypointData(id=5, name="left_shoulder", x=cx - 20, y=head_y + 20, confidence=0.90),
        6: KeypointData(id=6, name="right_shoulder", x=cx + 20, y=head_y + 20, confidence=0.90),
        7: KeypointData(id=7, name="left_elbow", x=cx - 25, y=head_y + 50, confidence=0.85),
        8: KeypointData(id=8, name="right_elbow", x=cx + 25, y=head_y + 50, confidence=0.85),
        11: KeypointData(id=11, name="left_hip", x=cx - 15, y=head_y + 90, confidence=0.90),
        12: KeypointData(id=12, name="right_hip", x=cx + 15, y=head_y + 90, confidence=0.90),
        13: KeypointData(id=13, name="left_knee", x=cx - 15, y=head_y + 130, confidence=0.85),
        14: KeypointData(id=14, name="right_knee", x=cx + 15, y=head_y + 130, confidence=0.85),
    }

    if wrist_mode == "hands_up":
        # Both wrists higher than head
        kps[9] = KeypointData(id=9, name="left_wrist", x=cx - 30, y=head_y - 30, confidence=0.95)
        kps[10] = KeypointData(id=10, name="right_wrist", x=cx + 30, y=head_y - 30, confidence=0.95)
    elif wrist_mode == "concealed":
        # Left wrist occluded / hidden
        kps[9] = KeypointData(id=9, name="left_wrist", x=cx - 10, y=head_y + 90, confidence=0.10)
        kps[10] = KeypointData(id=10, name="right_wrist", x=cx + 25, y=head_y + 60, confidence=0.90)
    else:
        kps[9] = KeypointData(id=9, name="left_wrist", x=cx - 25, y=head_y + 70, confidence=0.90)
        kps[10] = KeypointData(id=10, name="right_wrist", x=cx + 25, y=head_y + 70, confidence=0.90)

    return SubjectKinematicsSnapshot(
        track_id=track_id,
        bbox=bbox,
        centroid=(cx, cy),
        keypoints=kps,
        spine_angle_deg=spine_angle_deg,
        aspect_ratio=aspect_ratio,
        velocity_norm=velocity_norm,
        wrist_kinetic_energy=wrist_kinetic_energy,
        dwell_time_seconds=dwell_time_seconds,
        timestamp=timestamp
    )


def test_single_rules():
    print("--- [TEST 1/6] Testing Single-Subject Behavior Rules ---")
    all_subs: Dict[int, SubjectKinematicsSnapshot] = {}

    # 1. FallenCollapseRule
    fall_rule = FallenCollapseRule()
    snap_fall = create_mock_snapshot(track_id=1, spine_angle_deg=68.0, aspect_ratio=0.75, velocity_norm=0.1)
    res_fall = fall_rule.evaluate(snap_fall, [], all_subs)
    assert res_fall.matched is True
    assert res_fall.behavior_type == BehaviorType.FALLEN_COLLAPSE
    assert res_fall.category == BehaviorCategory.MEDICAL_DISTRESS
    assert res_fall.base_threat_score >= 0.90
    print("  -> PASSED: FallenCollapseRule correctly triggered for horizontal torso.")

    # 2. HandsUpDistressRule
    hands_rule = HandsUpDistressRule()
    snap_hands = create_mock_snapshot(track_id=2, wrist_mode="hands_up")
    res_hands = hands_rule.evaluate(snap_hands, [], all_subs)
    assert res_hands.matched is True
    assert res_hands.behavior_type == BehaviorType.HANDS_UP_DISTRESS
    assert res_hands.base_threat_score == 0.78
    print("  -> PASSED: HandsUpDistressRule correctly triggered for raised wrists.")

    # 3. SuddenFleeingRule
    flee_rule = SuddenFleeingRule()
    snap_flee = create_mock_snapshot(track_id=3, velocity_norm=2.4)
    res_flee = flee_rule.evaluate(snap_flee, [], all_subs)
    assert res_flee.matched is True
    assert res_flee.behavior_type == BehaviorType.SUDDEN_FLEEING
    assert res_flee.category == BehaviorCategory.POST_CRIME
    print("  -> PASSED: SuddenFleeingRule correctly triggered for velocity_norm >= 1.85.")

    # 4. CrouchingProwlingRule
    crouch_rule = CrouchingProwlingRule()
    snap_crouch = create_mock_snapshot(track_id=4, aspect_ratio=1.1, spine_angle_deg=35.0)
    res_crouch = crouch_rule.evaluate(snap_crouch, [], all_subs)
    assert res_crouch.matched is True
    assert res_crouch.behavior_type == BehaviorType.CROUCHING_PROWLING
    print("  -> PASSED: CrouchingProwlingRule correctly triggered for compressed posture.")

    # 5. LoiteringRule
    loiter_rule = LoiteringRule()
    history_loiter = [create_mock_snapshot(track_id=5, bbox=(100, 100, 180, 300), timestamp=1000.0 + i) for i in range(12)]
    snap_loiter = create_mock_snapshot(track_id=5, bbox=(105, 102, 185, 302), dwell_time_seconds=15.0, timestamp=1015.0)
    res_loiter = loiter_rule.evaluate(snap_loiter, history_loiter, all_subs)
    assert res_loiter.matched is True
    assert res_loiter.behavior_type == BehaviorType.LOITERING
    assert res_loiter.base_threat_score == 0.52
    print("  -> PASSED: LoiteringRule correctly triggered for dwell_time >= 10s within local area.")

    # 6. ConcealedReachRule
    conceal_rule = ConcealedReachRule()
    snap_conceal = create_mock_snapshot(track_id=6, wrist_mode="concealed", dwell_time_seconds=4.0)
    res_conceal = conceal_rule.evaluate(snap_conceal, [], all_subs)
    assert res_conceal.matched is True
    assert res_conceal.behavior_type == BehaviorType.CONCEALED_REACH
    assert res_conceal.category == BehaviorCategory.PRE_CRIME
    print("  -> PASSED: ConcealedReachRule correctly triggered for tucked/concealed wrist.")


def test_multi_rules():
    print("\n--- [TEST 2/6] Testing Multi-Subject Interaction Rules ---")

    # 1. FightingStrikeRule
    fight_rule = FightingStrikeRule()
    p1 = create_mock_snapshot(track_id=10, bbox=(200, 100, 260, 300), wrist_kinetic_energy=750.0)
    p2 = create_mock_snapshot(track_id=11, bbox=(245, 100, 305, 300), wrist_kinetic_energy=700.0)
    all_f = {10: p1, 11: p2}

    res_fight = fight_rule.evaluate(p1, [], all_f)
    assert res_fight.matched is True
    assert res_fight.behavior_type == BehaviorType.FIGHTING_STRIKE
    assert res_fight.category == BehaviorCategory.IN_PROGRESS_CRIME
    assert 11 in res_fight.interacting_with_track_ids
    assert res_fight.base_threat_score == 0.95
    print("  -> PASSED: FightingStrikeRule triggered for high-energy close contact.")

    # 2. GrapplingStruggleRule
    grapple_rule = GrapplingStruggleRule()
    p_g1 = create_mock_snapshot(track_id=20, bbox=(200, 100, 260, 300), spine_angle_deg=10.0, timestamp=1000.0)
    hist_g1 = [create_mock_snapshot(track_id=20, bbox=(200, 100, 260, 300), spine_angle_deg=50.0, timestamp=999.0)]
    p_g2 = create_mock_snapshot(track_id=21, bbox=(210, 100, 270, 300))  # High IoU overlap
    all_g = {20: p_g1, 21: p_g2}

    res_grapple = grapple_rule.evaluate(p_g1, hist_g1, all_g)
    assert res_grapple.matched is True
    assert res_grapple.behavior_type == BehaviorType.GRAPPLING_STRUGGLE
    print("  -> PASSED: GrapplingStruggleRule triggered for high box overlap & volatile spine shifts.")

    # 3. ChasingPursuitRule
    chase_rule = ChasingPursuitRule()
    # P30 fleeing, P31 chasing along X-axis
    p30 = create_mock_snapshot(track_id=30, bbox=(400, 100, 460, 300), velocity_norm=2.0, timestamp=1001.0)
    p31 = create_mock_snapshot(track_id=31, bbox=(200, 100, 260, 300), velocity_norm=2.1, timestamp=1001.0)
    hist_p31 = [create_mock_snapshot(track_id=31, bbox=(160, 100, 220, 300), velocity_norm=2.1, timestamp=1000.0)]
    all_chase = {30: p30, 31: p31}

    res_chase = chase_rule.evaluate(p31, hist_p31, all_chase)
    assert res_chase.matched is True
    assert res_chase.behavior_type == BehaviorType.CHASING_PURSUIT
    assert 30 in res_chase.interacting_with_track_ids
    print("  -> PASSED: ChasingPursuitRule triggered for collinear velocity pursuit.")

    # 4. SurroundedVictimRule
    surround_rule = SurroundedVictimRule()
    victim = create_mock_snapshot(track_id=40, bbox=(300, 200, 360, 400), velocity_norm=0.1)
    mob1 = create_mock_snapshot(track_id=41, bbox=(200, 200, 260, 400)) # Left
    mob2 = create_mock_snapshot(track_id=42, bbox=(400, 200, 460, 400)) # Right
    all_mob = {40: victim, 41: mob1, 42: mob2}

    res_surround = surround_rule.evaluate(victim, [], all_mob)
    assert res_surround.matched is True
    assert res_surround.behavior_type == BehaviorType.SURROUNDED_VICTIM
    assert len(res_surround.interacting_with_track_ids) == 2
    print("  -> PASSED: SurroundedVictimRule triggered for perimeter encirclement.")


def test_anti_flapping_debounce():
    print("\n--- [TEST 3/6] Testing Anti-Flapping Debounce (Jitter Rejection) ---")
    engine = ThreatMarkingEngine(enter_debounce_frames=8, exit_debounce_frames=12)
    t = 2000.0

    # Phase 1: 5 frames normal upright
    for i in range(5):
        snap = create_mock_snapshot(track_id=50, timestamp=t + i * 0.05)
        out = engine.process_frame(frame_index=i, subjects=[snap], timestamp=t + i * 0.05)
        assert out.threat_marks[0].threat_level == ThreatLevel.LOW

    # Phase 2: Inject 2 glitch frames of crouching
    for i in range(5, 7):
        snap_glitch = create_mock_snapshot(track_id=50, aspect_ratio=1.1, spine_angle_deg=35.0, timestamp=t + i * 0.05)
        out = engine.process_frame(frame_index=i, subjects=[snap_glitch], timestamp=t + i * 0.05)
        # MUST STAY LOW: 2 frames is below enter_debounce_frames=8
        assert out.threat_marks[0].threat_level == ThreatLevel.LOW, (
            f"Glitch frame {i} prematurely altered confirmed threat mark!"
        )
    print("  -> PASSED: 2 transient noise frames successfully filtered (Stayed LOW).")


def test_fast_track_critical():
    print("\n--- [TEST 4/6] Testing Fast-Track Critical Escalation (Fighting) ---")
    engine = ThreatMarkingEngine(enter_debounce_frames=8, fast_track_critical_frames=5)
    t = 3000.0

    # Inject 6 consecutive frames of active fighting
    confirmed_critical_at_frame_5 = False
    for i in range(6):
        curr_t = t + i * 0.05
        p1 = create_mock_snapshot(track_id=60, bbox=(200, 100, 260, 300), wrist_kinetic_energy=750.0, timestamp=curr_t)
        p2 = create_mock_snapshot(track_id=61, bbox=(245, 100, 305, 300), wrist_kinetic_energy=700.0, timestamp=curr_t)

        out = engine.process_frame(frame_index=i, subjects=[p1, p2], timestamp=curr_t)
        if i == 4: # 5th frame (index 4)
            if out.highest_threat_level == ThreatLevel.CRITICAL:
                confirmed_critical_at_frame_5 = True
                assert out.threat_marks[0].requires_operator_attention is True

    assert confirmed_critical_at_frame_5 is True, "Fast-track critical failed to trigger at 5th frame!"
    print("  -> PASSED: Fighting strike fast-track escalated to CRITICAL at frame 5.")


def test_dwell_time_escalation():
    print("\n--- [TEST 5/6] Testing Dwell Time Escalation (Loitering) ---")
    engine = ThreatMarkingEngine()
    t = 4000.0

    # Simulate loitering up to 25 seconds
    # At 12s -> should be MEDIUM
    snap_12s = create_mock_snapshot(track_id=70, dwell_time_seconds=12.0, timestamp=t + 12.0)
    # Feed history
    for i in range(12):
        s = create_mock_snapshot(track_id=70, timestamp=t + i)
        out_mid = engine.process_frame(frame_index=i, subjects=[s], timestamp=t + i)

    # Fast forward with loitering > 22 seconds
    for i in range(12, 25):
        s_long = create_mock_snapshot(track_id=70, dwell_time_seconds=float(i), timestamp=t + i)
        out_long = engine.process_frame(frame_index=i, subjects=[s_long], timestamp=t + i)

    last_mark = out_long.threat_marks[0]
    assert last_mark.threat_score >= 0.60
    assert last_mark.threat_level in (ThreatLevel.HIGH, ThreatLevel.CRITICAL)
    print(f"  -> PASSED: Dwell time escalated threat score to {last_mark.threat_score} ({last_mark.threat_level.value}).")


def test_json_contract_compatibility():
    print("\n--- [TEST 6/6] Testing JSON Contract Compatibility with standard.md ---")
    engine = ThreatMarkingEngine()
    snap = create_mock_snapshot(track_id=80, spine_angle_deg=65.0, aspect_ratio=0.8) # Fallen
    # Run 6 frames to confirm
    for i in range(6):
        out = engine.process_frame(frame_index=i, subjects=[snap], timestamp=5000.0 + i * 0.05)

    # Serialize to JSON dict
    json_str = out.model_dump_json()
    parsed = json.loads(json_str)

    # Verify standard contract fields
    assert "frame_index" in parsed
    assert "timestamp" in parsed
    assert "highest_threat_level" in parsed
    assert "highest_threat_score" in parsed
    assert "threat_marks" in parsed
    assert len(parsed["threat_marks"]) == 1

    mark_data = parsed["threat_marks"][0]
    assert "track_id" in mark_data
    assert "threat_level" in mark_data
    assert "threat_score" in mark_data
    assert "color_hex" in mark_data
    assert "requires_operator_attention" in mark_data

    print("  -> PASSED: Output schema serialized and validated against SOC API standard contract.")


if __name__ == "__main__":
    print("==================================================================")
    print(" URBAN SAFETY AI-SOC: VERIFICATION SUITE FOR RULE & ENGINE")
    print("==================================================================")
    test_single_rules()
    test_multi_rules()
    test_anti_flapping_debounce()
    test_fast_track_critical()
    test_dwell_time_escalation()
    test_json_contract_compatibility()
    print("\n==================================================================")
    print(" ALL 6 VERIFICATION TEST PHASES PASSED SUCCESSFULLY (100%)")
    print("==================================================================")
