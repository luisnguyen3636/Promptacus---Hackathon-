"""Detection package containing YOLO-Pose and fallback engines."""

from urbansoc.detection.base import PoseDetector
from urbansoc.detection.mediapipe_pose import PoseSkeletonDetector
from urbansoc.detection.yolo_pose import YOLOPoseDetector

__all__ = ["PoseDetector", "YOLOPoseDetector", "PoseSkeletonDetector"]
