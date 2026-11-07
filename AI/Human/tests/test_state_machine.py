"""Unit tests for Hysteresis Debounce state machine and anti-flapping stabilization."""

from urbansoc.behavior.engine import BehaviorEngine
from urbansoc.behavior.state_machine import HysteresisDebouncer, TrackDebounceState
from urbansoc.domain.enums import BehaviorType, ThreatLevel
from urbansoc.domain.schemas import BehaviorPrediction


def test_debouncer_noise_rejection():
    debouncer = HysteresisDebouncer(
        enter_debounce_frames=8,
        exit_debounce_frames=12,
        fast_track_debounce_frames=6,
    )
    state = TrackDebounceState(confirmed_behavior=BehaviorType.NORMAL.value)

    # 1. Provide 2 frames of spurious FALLEN noise
    noise_pred = BehaviorPrediction(
        primary_behavior=BehaviorType.FALLEN,
        confidence=0.95,
        threat_level=ThreatLevel.CRITICAL,
        threat_score=0.98,
        reasoning="Spurious noise frame",
    )

    t1 = debouncer.process_candidate(state, noise_pred, curr_time=1.0)
    assert t1 is None
    assert state.confirmed_behavior == BehaviorType.NORMAL.value
    assert state.candidate_streak == 1

    t2 = debouncer.process_candidate(state, noise_pred, curr_time=1.05)
    assert t2 is None
    assert state.confirmed_behavior == BehaviorType.NORMAL.value
    assert state.candidate_streak == 2

    # 2. Return to NORMAL -> streak resets
    normal_pred = BehaviorPrediction(
        primary_behavior=BehaviorType.NORMAL,
        confidence=0.95,
        threat_level=ThreatLevel.LOW,
        threat_score=0.10,
        reasoning="Upright",
    )
    t3 = debouncer.process_candidate(state, normal_pred, curr_time=1.10)
    assert t3 is None
    assert state.candidate_streak == 0
    assert state.confirmed_behavior == BehaviorType.NORMAL.value


def test_debouncer_fast_track_commit():
    debouncer = HysteresisDebouncer(fast_track_debounce_frames=6)
    state = TrackDebounceState(confirmed_behavior=BehaviorType.NORMAL.value)

    fallen_pred = BehaviorPrediction(
        primary_behavior=BehaviorType.FALLEN,
        confidence=0.95,
        threat_level=ThreatLevel.CRITICAL,
        threat_score=0.98,
        reasoning="True fall event",
    )

    # Feed 5 frames -> no commit yet
    for i in range(5):
        transition = debouncer.process_candidate(state, fallen_pred, curr_time=1.0 + i * 0.05)
        assert transition is None

    # 6th frame -> fast-track commits!
    transition = debouncer.process_candidate(state, fallen_pred, curr_time=1.30)
    assert transition is not None
    assert state.confirmed_behavior == BehaviorType.FALLEN.value
    assert state.confirmed_threat_level == ThreatLevel.CRITICAL


def test_debouncer_weapon_threat_fast_track():
    debouncer = HysteresisDebouncer(fast_track_debounce_frames=6)
    state = TrackDebounceState(confirmed_behavior=BehaviorType.NORMAL.value)

    weapon_pred = BehaviorPrediction(
        primary_behavior=BehaviorType.WEAPON_THREAT,
        confidence=0.96,
        threat_level=ThreatLevel.CRITICAL,
        threat_score=0.96,
        reasoning="Tactical weapon aim",
    )

    for i in range(5):
        assert debouncer.process_candidate(state, weapon_pred, curr_time=1.0 + i * 0.05) is None

    transition = debouncer.process_candidate(state, weapon_pred, curr_time=1.30)
    assert transition is not None
    assert state.confirmed_behavior == BehaviorType.WEAPON_THREAT.value
    assert state.confirmed_threat_level == ThreatLevel.CRITICAL


def test_debouncer_exit_to_normal_debounce():
    debouncer = HysteresisDebouncer(exit_debounce_frames=12)
    state = TrackDebounceState(
        confirmed_behavior=BehaviorType.FALLEN.value,
        confirmed_threat_level=ThreatLevel.CRITICAL,
    )

    normal_pred = BehaviorPrediction(
        primary_behavior=BehaviorType.NORMAL,
        confidence=0.95,
        threat_level=ThreatLevel.LOW,
        threat_score=0.10,
        reasoning="Standing back up",
    )

    # Requires 12 consecutive frames of proof to revert to NORMAL
    for i in range(11):
        transition = debouncer.process_candidate(state, normal_pred, curr_time=2.0 + i * 0.05)
        assert transition is None
        assert state.confirmed_behavior == BehaviorType.FALLEN.value

    # 12th frame commits return to NORMAL
    transition = debouncer.process_candidate(state, normal_pred, curr_time=2.60)
    assert transition is not None
    assert state.confirmed_behavior == BehaviorType.NORMAL.value


def test_behavior_engine_anti_flapping_integration(tmp_path, synthetic_pose_factory):
    engine = BehaviorEngine(
        output_dir=str(tmp_path),
        fast_track_debounce_frames=6,
        exit_debounce_frames=12,
    )

    # 6 frames of NORMAL
    for i in range(6):
        p = synthetic_pose_factory(track_id=1, spine_mode="upright")
        poses, _, _ = engine.update([p], timestamp=1.0 + i * 0.05, frame_index=i)
        assert poses[0].behavior.primary_behavior == BehaviorType.NORMAL

    # 2 frames of FALLEN noise -> must stay NORMAL!
    for i in range(6, 8):
        p = synthetic_pose_factory(track_id=1, spine_mode="fallen")
        poses, _, _ = engine.update([p], timestamp=1.0 + i * 0.05, frame_index=i)
        assert poses[0].behavior.primary_behavior == BehaviorType.NORMAL

    # Next 6 frames of continuous FALLEN -> commits to FALLEN!
    for i in range(8, 14):
        p = synthetic_pose_factory(track_id=1, spine_mode="fallen")
        poses, _, _ = engine.update([p], timestamp=1.0 + i * 0.05, frame_index=i)

    assert poses[0].behavior.primary_behavior == BehaviorType.FALLEN
    assert poses[0].behavior.threat_level == ThreatLevel.CRITICAL

    # Verify BBox EMA smoothing is valid
    assert poses[0].bbox.width > 0
    assert poses[0].bbox.height > 0

    engine.close()
