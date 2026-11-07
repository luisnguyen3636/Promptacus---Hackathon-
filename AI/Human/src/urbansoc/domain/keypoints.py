"""Keypoint constants, skeleton topology, and naming conventions."""

from typing import List, Tuple

# Keypoint Confidence Gate
KEYPOINT_CONFIDENCE_THRESHOLD: float = 0.25

# COCO-17 Indices
NOSE: int = 0
LEFT_EYE: int = 1
RIGHT_EYE: int = 2
LEFT_EAR: int = 3
RIGHT_EAR: int = 4
LEFT_SHOULDER: int = 5
RIGHT_SHOULDER: int = 6
LEFT_ELBOW: int = 7
RIGHT_ELBOW: int = 8
LEFT_WRIST: int = 9
RIGHT_WRIST: int = 10
LEFT_HIP: int = 11
RIGHT_HIP: int = 12
LEFT_KNEE: int = 13
RIGHT_KNEE: int = 14
LEFT_ANKLE: int = 15
RIGHT_ANKLE: int = 16

# COCO-17 Names in strict fixed order
COCO_KEYPOINT_NAMES: List[str] = [
    "nose",
    "left_eye",
    "right_eye",
    "left_ear",
    "right_ear",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
]

# COCO-17 Skeleton pairs (16 pairs)
COCO_SKELETON_PAIRS: List[Tuple[int, int]] = [
    # Head
    (0, 1), (0, 2), (1, 3), (2, 4),
    # Torso
    (5, 6), (5, 11), (6, 12), (11, 12),
    # Left Arm
    (5, 7), (7, 9),
    # Right Arm
    (6, 8), (8, 10),
    # Left Leg
    (11, 13), (13, 15),
    # Right Leg
    (12, 14), (14, 16),
]

# MediaPipe 33 Landmark Names
MEDIAPIPE_LANDMARK_NAMES: List[str] = [
    "NOSE",
    "LEFT_EYE_INNER", "LEFT_EYE", "LEFT_EYE_OUTER",
    "RIGHT_EYE_INNER", "RIGHT_EYE", "RIGHT_EYE_OUTER",
    "LEFT_EAR", "RIGHT_EAR",
    "MOUTH_LEFT", "MOUTH_RIGHT",
    "LEFT_SHOULDER", "RIGHT_SHOULDER",
    "LEFT_ELBOW", "RIGHT_ELBOW",
    "LEFT_WRIST", "RIGHT_WRIST",
    "LEFT_PINKY", "RIGHT_PINKY",
    "LEFT_INDEX", "RIGHT_INDEX",
    "LEFT_THUMB", "RIGHT_THUMB",
    "LEFT_HIP", "RIGHT_HIP",
    "LEFT_KNEE", "RIGHT_KNEE",
    "LEFT_ANKLE", "RIGHT_ANKLE",
    "LEFT_HEEL", "RIGHT_HEEL",
    "LEFT_FOOT_INDEX", "RIGHT_FOOT_INDEX",
]

# MediaPipe 33 Skeleton pairs (29 pairs)
MEDIAPIPE_SKELETON_PAIRS: List[Tuple[int, int]] = [
    # Torso
    (11, 12), (11, 23), (12, 24), (23, 24),
    # Left arm
    (11, 13), (13, 15), (15, 17), (15, 19),
    # Right arm
    (12, 14), (14, 16), (16, 18), (16, 20),
    # Left leg
    (23, 25), (25, 27), (27, 29), (29, 31),
    # Right leg
    (24, 26), (26, 28), (28, 30), (30, 32),
    # Face
    (0, 1), (1, 2), (2, 3), (3, 7),
    (0, 4), (4, 5), (5, 6), (6, 8),
    (9, 10),
]
