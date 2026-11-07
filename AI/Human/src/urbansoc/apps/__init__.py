"""Surveillance applications package."""

from urbansoc.apps.batch import BatchHumanDetector
from urbansoc.apps.live import CameraRecorder

__all__ = ["CameraRecorder", "BatchHumanDetector"]
