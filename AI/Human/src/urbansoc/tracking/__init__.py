"""Cross-Camera Re-Identification and Multi-Camera Global Identity Tracking Module."""

from urbansoc.tracking.cross_camera_reid import (
    CrossCameraReIDCoordinator,
    GlobalSubjectProfile,
    ReIDAppearanceSignature,
    extract_appearance_signature,
)

__all__ = [
    "CrossCameraReIDCoordinator",
    "GlobalSubjectProfile",
    "ReIDAppearanceSignature",
    "extract_appearance_signature",
]
