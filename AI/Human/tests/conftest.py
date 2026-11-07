"""Pytest fixtures and synthetic pose generators (Zero Network / Zero Weights)."""

import os
import sys
from typing import Callable, List, Optional, Tuple

import numpy as np
import pytest

# Ensure src/ is in sys.path for test discovery
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_dir = os.path.join(root_dir, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from urbansoc.detection.base import PoseDetector
from urbansoc.domain.enums import BehaviorType, ThreatLevel
from urbansoc.domain.geometry import BBox
from urbansoc.domain.keypoints import (
    COCO_KEYPOINT_NAMES,
    LEFT_ANKLE,
    LEFT_ELBOW,
    LEFT_HIP,
    LEFT_KNEE,
    LEFT_SHOULDER,
    LEFT_WRIST,
    NOSE,
    RIGHT_ANKLE,
    RIGHT_ELBOW,
    RIGHT_HIP,
    RIGHT_KNEE,
    RIGHT_SHOULDER,
    RIGHT_WRIST,
)
from urbansoc.domain.schemas import (
    BehaviorPrediction,
    HumanPoseTrack,
    KeypointCOCO,
    SOCFrameAnalysisResult,
)
from urbansoc.domain.synthetic import create_synthetic_pose


class FakeDetector(PoseDetector):
    """Stub detector returning configured poses for end-to-end smoke testing."""

    def __init__(self, poses_sequence: Optional[List[List[HumanPoseTrack]]] = None) -> None:
        self.poses_sequence = poses_sequence or []
        self.call_count = 0
        self.show_debug_box = True

    def toggle_debug_box(self) -> bool:
        self.show_debug_box = not self.show_debug_box
        return self.show_debug_box

    def process_frame(
        self,
        frame_bgr: np.ndarray,
        frame_index: int = 0,
        timestamp: float = 0.0,
    ) -> Tuple[SOCFrameAnalysisResult, np.ndarray]:
        poses = (
            self.poses_sequence[self.call_count % len(self.poses_sequence)]
            if self.poses_sequence
            else []
        )
        self.call_count += 1

        analysis = SOCFrameAnalysisResult(
            frame_index=frame_index,
            timestamp="2026-11-07 12:00:00.000",
            human_count=len(poses),
            humans=poses,
            highest_threat_level=ThreatLevel.LOW,
            highest_threat_score=0.10,
        )
        return analysis, frame_bgr.copy()

    def close(self) -> None:
        pass


@pytest.fixture
def synthetic_pose_factory():
    return create_synthetic_pose
