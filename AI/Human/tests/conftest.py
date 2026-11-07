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


def create_synthetic_pose(
    track_id: int = 1,
    bbox: Optional[BBox] = None,
    spine_mode: str = "upright",       # "upright" | "fallen" | "crouching"
    wrists_mode: str = "normal",       # "normal" | "hands_up" | "fighting"
    step: int = 0,
    speed_offset_x: float = 0.0,
) -> HumanPoseTrack:
    """Generate a mathematically determined synthetic COCO-17 human pose for deterministic testing."""
    if bbox is None:
        if spine_mode == "fallen":
            # Horizontal bbox (W > H)
            bbox = BBox.from_xywh(100 + speed_offset_x, 300, 150, 50)
        elif spine_mode == "crouching":
            # Squat bbox (H/W ~ 1.1)
            bbox = BBox.from_xywh(100 + speed_offset_x, 200, 70, 75)
        else:
            # Upright standing bbox (H/W ~ 2.5)
            bbox = BBox.from_xywh(100 + speed_offset_x, 100, 60, 150)

    bx1, by1, bx2, by2 = bbox.to_xyxy()
    cx, cy = bbox.centroid
    bw = float(bbox.width)
    bh = float(bbox.height)

    # Base keypoints mapped across bbox
    kpts: List[KeypointCOCO] = []

    def add_kp(kid: int, x: float, y: float, conf: float = 0.95):
        name = COCO_KEYPOINT_NAMES[kid]
        kpts.append(KeypointCOCO(id=kid, name=name, x=float(x), y=float(y), confidence=conf))

    if spine_mode == "fallen":
        # Torso aligned horizontally: shoulders at left, hips at right (dx >> dy)
        add_kp(NOSE, bx1 + 10, cy)
        add_kp(LEFT_SHOULDER, bx1 + 30, cy - 10)
        add_kp(RIGHT_SHOULDER, bx1 + 30, cy + 10)
        add_kp(LEFT_HIP, bx1 + 90, cy - 10)
        add_kp(RIGHT_HIP, bx1 + 90, cy + 10)
        add_kp(LEFT_KNEE, bx1 + 120, cy - 10)
        add_kp(RIGHT_KNEE, bx1 + 120, cy + 10)
        add_kp(LEFT_ANKLE, bx2 - 10, cy - 10)
        add_kp(RIGHT_ANKLE, bx2 - 10, cy + 10)
    elif spine_mode == "crouching":
        # Compressed posture with bent knees
        add_kp(NOSE, cx, by1 + 10)
        add_kp(LEFT_SHOULDER, cx - 15, by1 + 25)
        add_kp(RIGHT_SHOULDER, cx + 15, by1 + 25)
        add_kp(LEFT_HIP, cx - 15, by1 + 45)
        add_kp(RIGHT_HIP, cx + 15, by1 + 45)
        add_kp(LEFT_KNEE, cx - 20, by1 + 55)
        add_kp(RIGHT_KNEE, cx + 20, by1 + 55)
        add_kp(LEFT_ANKLE, cx - 15, by2 - 5)
        add_kp(RIGHT_ANKLE, cx + 15, by2 - 5)
    else:
        # Standard upright posture
        add_kp(NOSE, cx, by1 + 15)
        add_kp(LEFT_SHOULDER, cx - 18, by1 + 35)
        add_kp(RIGHT_SHOULDER, cx + 18, by1 + 35)
        add_kp(LEFT_HIP, cx - 15, by1 + 80)
        add_kp(RIGHT_HIP, cx + 15, by1 + 80)
        add_kp(LEFT_KNEE, cx - 15, by1 + 115)
        add_kp(RIGHT_KNEE, cx + 15, by1 + 115)
        add_kp(LEFT_ANKLE, cx - 15, by2 - 5)
        add_kp(RIGHT_ANKLE, cx + 15, by2 - 5)

    # Configure Wrists
    nose_y = by1 + 15
    if wrists_mode == "hands_up":
        # Both wrists raised above nose
        add_kp(LEFT_ELBOW, cx - 25, by1 + 20)
        add_kp(RIGHT_ELBOW, cx + 25, by1 + 20)
        add_kp(LEFT_WRIST, cx - 25, nose_y - 20)
        add_kp(RIGHT_WRIST, cx + 25, nose_y - 20)
    elif wrists_mode == "two_handed_aim":
        # Both wrists tightly converging in front of chest, elbows extended
        add_kp(LEFT_ELBOW, cx - 15, by1 + 50)
        add_kp(RIGHT_ELBOW, cx + 15, by1 + 50)
        add_kp(LEFT_WRIST, cx - 5, by1 + 50)
        add_kp(RIGHT_WRIST, cx + 5, by1 + 50)
    elif wrists_mode == "weapon_pointing":
        # Right arm straight pointing horizontally outward
        add_kp(LEFT_ELBOW, cx - 20, by1 + 55)
        add_kp(LEFT_WRIST, cx - 20, by1 + 75)
        # Right arm extended horizontally: shoulder -> elbow -> wrist in a straight line
        add_kp(RIGHT_ELBOW, cx + 35, by1 + 35)
        add_kp(RIGHT_WRIST, cx + 70, by1 + 35)
    elif wrists_mode == "phone_call":
        # Right wrist near ear/nose, elbow bent sharply (< 65 degrees)
        add_kp(LEFT_ELBOW, cx - 20, by1 + 55)
        add_kp(LEFT_WRIST, cx - 20, by1 + 75)
        add_kp(RIGHT_ELBOW, cx + 25, by1 + 55)
        add_kp(RIGHT_WRIST, cx + 15, nose_y)
    elif wrists_mode == "fighting":
        # Oscillating high-velocity wrists
        osc = 40.0 if (step % 2 == 0) else -40.0
        add_kp(LEFT_ELBOW, cx - 20, by1 + 50)
        add_kp(RIGHT_ELBOW, cx + 20, by1 + 50)
        add_kp(LEFT_WRIST, cx - 20 + osc, by1 + 45)
        add_kp(RIGHT_WRIST, cx + 20 - osc, by1 + 45)
    else:
        # Normal relaxed wrists hanging by sides
        add_kp(LEFT_ELBOW, cx - 20, by1 + 55)
        add_kp(RIGHT_ELBOW, cx + 20, by1 + 55)
        add_kp(LEFT_WRIST, cx - 20, by1 + 75)
        add_kp(RIGHT_WRIST, cx + 20, by1 + 75)

    # Fill in eye/ear dummy points if missing
    for dummy_id in [1, 2, 3, 4]:
        add_kp(dummy_id, cx, by1 + 10, conf=0.8)

    return HumanPoseTrack(
        track_id=track_id,
        bbox=bbox,
        detection_conf=0.92,
        keypoints=kpts,
    )


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
