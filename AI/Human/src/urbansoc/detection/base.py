"""Abstract base class and protocol for pose detection engines."""

from abc import ABC, abstractmethod
from typing import Tuple

import numpy as np

from urbansoc.domain.schemas import SOCFrameAnalysisResult


class PoseDetector(ABC):
    """Abstract interface defining required methods for all pose detection engines."""

    @abstractmethod
    def process_frame(
        self,
        frame_bgr: np.ndarray,
        frame_index: int = 0,
        timestamp: float = 0.0,
    ) -> Tuple[SOCFrameAnalysisResult, np.ndarray]:
        """Process a BGR video frame and return structured analysis result with annotated frame."""
        pass

    @abstractmethod
    def toggle_debug_box(self) -> bool:
        """Toggle the visibility state of the diagnostic telemetry HUD box."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Release neural network, tracking engine, and file handles."""
        pass
