"""Geometry abstractions and utilities for BBox and IoU calculations."""

from dataclasses import dataclass
from typing import Tuple, Union, Sequence


@dataclass(frozen=True)
class BBox:
    """Explicit Bounding Box representation with named coordinates (x1, y1, x2, y2)."""
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def width(self) -> int:
        """Width in pixels (guaranteed >= 1)."""
        return max(1, self.x2 - self.x1)

    @property
    def height(self) -> int:
        """Height in pixels (guaranteed >= 1)."""
        return max(1, self.y2 - self.y1)

    @property
    def aspect_ratio(self) -> float:
        """Height divided by width (H / W)."""
        return float(self.height) / float(self.width)

    @property
    def centroid(self) -> Tuple[float, float]:
        """Center coordinate (cx, cy)."""
        return ((self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0)

    def to_xyxy(self) -> Tuple[int, int, int, int]:
        """Convert to (x1, y1, x2, y2) tuple."""
        return (self.x1, self.y1, self.x2, self.y2)

    def to_xywh(self) -> Tuple[int, int, int, int]:
        """Convert to (x, y, w, h) tuple."""
        return (self.x1, self.y1, self.width, self.height)

    @classmethod
    def from_xywh(cls, x: Union[int, float], y: Union[int, float], w: Union[int, float], h: Union[int, float]) -> "BBox":
        """Instantiate BBox from (x, y, w, h)."""
        ix1 = int(round(x))
        iy1 = int(round(y))
        ix2 = int(round(x + w))
        iy2 = int(round(y + h))
        return cls(x1=ix1, y1=iy1, x2=max(ix1 + 1, ix2), y2=max(iy1 + 1, iy2))

    @classmethod
    def from_xyxy(cls, x1: Union[int, float], y1: Union[int, float], x2: Union[int, float], y2: Union[int, float]) -> "BBox":
        """Instantiate BBox from (x1, y1, x2, y2)."""
        ix1 = int(round(x1))
        iy1 = int(round(y1))
        ix2 = int(round(x2))
        iy2 = int(round(y2))
        return cls(x1=ix1, y1=iy1, x2=max(ix1 + 1, ix2), y2=max(iy1 + 1, iy2))


def bbox_from_xywh(x: Union[int, float], y: Union[int, float], w: Union[int, float], h: Union[int, float]) -> BBox:
    """Helper function to create BBox from (x, y, w, h)."""
    return BBox.from_xywh(x, y, w, h)


def bbox_to_xywh(bbox: BBox) -> Tuple[int, int, int, int]:
    """Helper function to convert BBox to (x, y, w, h)."""
    return bbox.to_xywh()


def iou_xyxy(box1: Union[BBox, Sequence[Union[int, float]]], box2: Union[BBox, Sequence[Union[int, float]]]) -> float:
    """Compute Intersection over Union (IoU) between two bounding boxes."""
    if isinstance(box1, BBox):
        b1_x1, b1_y1, b1_x2, b1_y2 = box1.to_xyxy()
    else:
        b1_x1, b1_y1, b1_x2, b1_y2 = box1[0], box1[1], box1[2], box1[3]

    if isinstance(box2, BBox):
        b2_x1, b2_y1, b2_x2, b2_y2 = box2.to_xyxy()
    else:
        b2_x1, b2_y1, b2_x2, b2_y2 = box2[0], box2[1], box2[2], box2[3]

    inter_x1 = max(b1_x1, b2_x1)
    inter_y1 = max(b1_y1, b2_y1)
    inter_x2 = min(b1_x2, b2_x2)
    inter_y2 = min(b1_y2, b2_y2)

    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h

    area1 = max(0.0, b1_x2 - b1_x1) * max(0.0, b1_y2 - b1_y1)
    area2 = max(0.0, b2_x2 - b2_x1) * max(0.0, b2_y2 - b2_y1)

    union_area = area1 + area2 - inter_area
    if union_area <= 1e-6:
        return 0.0

    return float(inter_area / union_area)
