"""Pose skeleton, joint markers, and sleek corner-styled bounding box rendering."""

import math
from typing import Dict, Tuple

import cv2
import numpy as np

from urbansoc.domain.geometry import BBox
from urbansoc.domain.keypoints import (
    COCO_SKELETON_PAIRS,
    KEYPOINT_CONFIDENCE_THRESHOLD,
)
from urbansoc.domain.schemas import HumanPoseTrack


def draw_corner_bounding_box(
    image: np.ndarray,
    bbox: BBox,
    color: Tuple[int, int, int],
    corner_fraction: float = 0.15,
) -> None:
    """Draw an aesthetic high-tech bounding box with corner accent brackets."""
    x1, y1, x2, y2 = bbox.to_xyxy()
    w = bbox.width
    h = bbox.height

    # Thin outer rectangle
    cv2.rectangle(image, (x1, y1), (x2, y2), color, 1, cv2.LINE_AA)

    # Corner bracket length clamped between 8 and 20 px
    corner_len = min(20, max(8, int(min(w, h) * corner_fraction)))

    # Top-Left
    cv2.line(image, (x1, y1), (x1 + corner_len, y1), color, 2, cv2.LINE_AA)
    cv2.line(image, (x1, y1), (x1, y1 + corner_len), color, 2, cv2.LINE_AA)

    # Top-Right
    cv2.line(image, (x2, y1), (x2 - corner_len, y1), color, 2, cv2.LINE_AA)
    cv2.line(image, (x2, y1), (x2, y1 + corner_len), color, 2, cv2.LINE_AA)

    # Bottom-Left
    cv2.line(image, (x1, y2), (x1 + corner_len, y2), color, 2, cv2.LINE_AA)
    cv2.line(image, (x1, y2), (x1, y2 - corner_len), color, 2, cv2.LINE_AA)

    # Bottom-Right
    cv2.line(image, (x2, y2), (x2 - corner_len, y2), color, 2, cv2.LINE_AA)
    cv2.line(image, (x2, y2), (x2, y2 - corner_len), color, 2, cv2.LINE_AA)


def draw_pose_skeleton_and_indicators(
    image: np.ndarray,
    human: HumanPoseTrack,
    palette: Dict[str, Tuple[int, int, int]],
    conf_thresh: float = KEYPOINT_CONFIDENCE_THRESHOLD,
) -> None:
    """Render skeleton bones, joint rings, corner bounding box, and ID/behavior label banner."""
    box_color = palette.get("box", (0, 220, 0))
    bone_color = palette.get("bone", (0, 255, 127))
    joint_color = palette.get("joint", (0, 255, 0))

    kp_map = {kp.id: kp for kp in human.keypoints if kp.confidence >= conf_thresh}
    bw = float(human.bbox.width)
    bh = float(human.bbox.height)
    max_bone_len = max(50.0, 0.85 * math.hypot(bw, bh))

    # 1. Draw Bones
    for idx1, idx2 in COCO_SKELETON_PAIRS:
        if idx1 in kp_map and idx2 in kp_map:
            p1 = kp_map[idx1]
            p2 = kp_map[idx2]
            bone_dist = math.hypot(p1.x - p2.x, p1.y - p2.y)
            if bone_dist <= max_bone_len:
                pt1 = (int(round(p1.x)), int(round(p1.y)))
                pt2 = (int(round(p2.x)), int(round(p2.y)))
                cv2.line(image, pt1, pt2, bone_color, 2, cv2.LINE_AA)

    # 2. Draw Joints
    for kp in kp_map.values():
        pt = (int(round(kp.x)), int(round(kp.y)))
        cv2.circle(image, pt, 3, joint_color, -1, cv2.LINE_AA)
        cv2.circle(image, pt, 5, (255, 255, 255), 1, cv2.LINE_AA)

    # 3. Draw Corner Box
    draw_corner_bounding_box(image, human.bbox, box_color)

    # 4. Draw Header Label
    x1, y1, _, _ = human.bbox.to_xyxy()
    score_pct = int(round(human.behavior.threat_score * 100))
    label_text = f"ID #{human.track_id} | {human.behavior.primary_behavior.value} [{score_pct}%]"
    if human.behavior.interacting_with_track_id is not None:
        label_text += f" vs #{human.behavior.interacting_with_track_id}"

    font_scale = 0.42
    font_thick = 1
    (tw, th), baseline = cv2.getTextSize(
        label_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, font_thick
    )

    badge_y1 = max(0, y1 - th - 10)
    badge_y2 = y1
    badge_x1 = x1
    badge_x2 = x1 + tw + 10

    # Solid dark background with matching border
    cv2.rectangle(image, (badge_x1, badge_y1), (badge_x2, badge_y2), (15, 15, 15), -1)
    cv2.rectangle(image, (badge_x1, badge_y1), (badge_x2, badge_y2), box_color, 1)

    cv2.putText(
        image,
        label_text,
        (badge_x1 + 5, badge_y2 - 5),
        cv2.FONT_HERSHEY_SIMPLEX,
        font_scale,
        (255, 255, 255),
        font_thick,
        cv2.LINE_AA,
    )
