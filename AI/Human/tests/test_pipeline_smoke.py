"""Smoke test for the end-to-end pipeline using synthetic stub detectors."""

import numpy as np

from conftest import FakeDetector
from urbansoc.domain.enums import BehaviorType, ThreatLevel
from urbansoc.domain.geometry import BBox
from urbansoc.domain.schemas import BehaviorPrediction, HumanPoseTrack
from urbansoc.io.sources import SimulatedSource


def test_simulated_camera_source():
    sim_source = SimulatedSource(resolution=(320, 240), fps=20.0)
    ret, frame = sim_source.read()
    assert ret is True
    assert frame is not None
    assert frame.shape == (240, 320, 3)
    sim_source.release()


def test_pipeline_smoke_with_fake_detector(synthetic_pose_factory):
    pose = synthetic_pose_factory(track_id=1, bbox=BBox.from_xywh(50, 50, 60, 150))
    pose.behavior = BehaviorPrediction(
        primary_behavior=BehaviorType.NORMAL,
        confidence=0.90,
        threat_level=ThreatLevel.LOW,
        threat_score=0.10,
        reasoning="Normal upright gait",
    )

    detector = FakeDetector(poses_sequence=[[pose]])
    assert detector.show_debug_box is True
    assert detector.toggle_debug_box() is False
    assert detector.toggle_debug_box() is True

    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    analysis, annotated = detector.process_frame(frame, frame_index=1)

    assert analysis.has_human is True
    assert analysis.human_count == 1
    assert analysis.humans[0].track_id == 1
    assert annotated.shape == (480, 640, 3)

    detector.close()
