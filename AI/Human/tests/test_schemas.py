"""Unit tests for domain schemas, BBox geometry, and IoU algorithms."""

import pytest
from urbansoc.domain.enums import BehaviorType, ThreatLevel
from urbansoc.domain.geometry import BBox, bbox_from_xywh, bbox_to_xywh, iou_xyxy
from urbansoc.domain.schemas import (
    BehaviorPrediction,
    FrameAnalysisResult,
    HumanIncidentClip,
    HumanPose,
    HumanPoseTrack,
    Keypoint,
    KeypointCOCO,
    SOCFrameAnalysisResult,
)


def test_bbox_creation_and_properties():
    box = BBox.from_xywh(10, 20, 100, 200)
    assert box.x1 == 10
    assert box.y1 == 20
    assert box.x2 == 110
    assert box.y2 == 220
    assert box.width == 100
    assert box.height == 200
    assert box.aspect_ratio == 2.0
    assert box.centroid == (60.0, 120.0)
    assert box.to_xywh() == (10, 20, 100, 200)
    assert box.to_xyxy() == (10, 20, 110, 220)


def test_bbox_helpers():
    b = bbox_from_xywh(5, 5, 20, 30)
    assert isinstance(b, BBox)
    assert bbox_to_xywh(b) == (5, 5, 20, 30)


def test_iou_calculation():
    box_a = BBox.from_xyxy(0, 0, 10, 10)
    box_b = BBox.from_xyxy(0, 0, 10, 10)
    assert iou_xyxy(box_a, box_b) == 1.0

    box_c = BBox.from_xyxy(10, 10, 20, 20)
    assert iou_xyxy(box_a, box_c) == 0.0

    box_d = BBox.from_xyxy(5, 0, 15, 10)
    # intersection: 5x10 = 50, union: 100 + 100 - 50 = 150 -> 50/150 = 1/3
    assert abs(iou_xyxy(box_a, box_d) - (1.0 / 3.0)) < 1e-4


def test_soc_schemas_initialization():
    kp = KeypointCOCO(id=0, name="nose", x=12.5, y=34.2, confidence=0.98)
    assert kp.id == 0
    assert kp.name == "nose"

    pred = BehaviorPrediction(
        primary_behavior=BehaviorType.NORMAL,
        confidence=0.95,
        threat_level=ThreatLevel.LOW,
        threat_score=0.10,
        reasoning="Normal upright posture",
    )
    assert pred.primary_behavior == BehaviorType.NORMAL
    assert pred.threat_level == ThreatLevel.LOW

    track = HumanPoseTrack(
        track_id=1,
        bbox=BBox.from_xyxy(10, 10, 50, 100),
        detection_conf=0.88,
        keypoints=[kp],
        behavior=pred,
    )
    assert track.posture_label == "NORMAL"
    assert track.confidence == 0.88

    soc_res = SOCFrameAnalysisResult(
        frame_index=1,
        timestamp="2026-11-07 10:00:00.000",
        human_count=1,
        humans=[track],
        highest_threat_level=ThreatLevel.LOW,
        highest_threat_score=0.10,
    )
    assert soc_res.has_human is True
    assert soc_res.requires_operator_attention is False


def test_legacy_schemas():
    kp = Keypoint(id=0, name="NOSE", x=10, y=20, z=0.5, visibility=0.9)
    human = HumanPose(
        track_id=1,
        bbox=BBox.from_xywh(0, 0, 50, 100),
        confidence=0.9,
        keypoints=[kp],
        posture_label="Standing",
    )
    res = FrameAnalysisResult(
        frame_index=0, timestamp="2026", human_count=1, humans=[human]
    )
    assert res.has_human is True

    clip = HumanIncidentClip(
        event_id="INC-1",
        source_video="test.mp4",
        start_time="0.0s",
        end_time="5.0s",
        start_frame=0,
        end_frame=100,
        duration_seconds=5.0,
        output_filepath="out.mp4",
    )
    assert clip.event_id == "INC-1"
