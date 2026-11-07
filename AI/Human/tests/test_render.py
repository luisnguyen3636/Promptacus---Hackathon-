"""Unit tests verifying visual rendering and multi-resolution layout scaling."""

import numpy as np
import pytest

from urbansoc.domain.enums import BehaviorType, ThreatLevel
from urbansoc.domain.geometry import BBox
from urbansoc.domain.schemas import (
    BehaviorPrediction,
    HumanPoseTrack,
    SOCFrameAnalysisResult,
    TrackKinematicsTelemetry,
)
from urbansoc.render.hud import draw_diagnostic_alert_box, draw_soc_hud_dashboard
from urbansoc.render.skeleton import draw_pose_skeleton_and_indicators
from urbansoc.render.theme import THREAT_COLORS


@pytest.mark.parametrize("resolution", [(640, 480), (1280, 720), (1920, 1080)])
def test_hud_and_debug_box_render_resolutions(resolution, synthetic_pose_factory):
    w, h = resolution
    frame = np.zeros((h, w, 3), dtype=np.uint8)

    pose = synthetic_pose_factory(track_id=1, bbox=BBox.from_xywh(100, 100, 60, 150))
    pose.behavior = BehaviorPrediction(
        primary_behavior=BehaviorType.NORMAL,
        confidence=0.95,
        threat_level=ThreatLevel.LOW,
        threat_score=0.10,
        reasoning="Upright",
    )

    telemetry = TrackKinematicsTelemetry(
        track_id=1,
        spine_angle=12.0,
        aspect_ratio=2.5,
        speed=0.2,
        wrist_energy=15.0,
        dwell_time=3.5,
        confirmed_behavior="NORMAL",
        threat_level=ThreatLevel.LOW,
        threat_score=0.10,
    )

    analysis = SOCFrameAnalysisResult(
        frame_index=1,
        timestamp="2026-11-07 12:00:00.000",
        human_count=1,
        humans=[pose],
        highest_threat_level=ThreatLevel.LOW,
        highest_threat_score=0.10,
        critical_events=[],
        telemetry_list=[telemetry],
        recent_alerts=["[12:00:00] ID #1 INIT -> NORMAL"],
        is_recording_evidence=True,
    )

    # 1. Test skeleton rendering
    palette = THREAT_COLORS[pose.behavior.threat_level]
    draw_pose_skeleton_and_indicators(frame, pose, palette)

    # 2. Test Top HUD rendering
    hud_frame = draw_soc_hud_dashboard(frame, analysis, fps=24.5)
    assert hud_frame.shape == (h, w, 3)

    # 3. Test Diagnostic Telemetry Alert Box rendering
    debug_frame = draw_diagnostic_alert_box(hud_frame, analysis)
    assert debug_frame.shape == (h, w, 3)
