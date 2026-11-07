"""Visual themes, threat palettes, and font configurations for SOC rendering."""

from typing import Dict, Tuple

from urbansoc.domain.enums import ThreatLevel

# Threat level color schemes in BGR format
THREAT_COLORS: Dict[ThreatLevel, Dict[str, Tuple[int, int, int]]] = {
    ThreatLevel.LOW: {
        "box": (0, 220, 0),
        "bone": (0, 255, 127),
        "joint": (0, 255, 0),
        "label": (0, 180, 0),
    },
    ThreatLevel.MEDIUM: {
        "box": (0, 215, 255),
        "bone": (0, 215, 255),
        "joint": (0, 255, 255),
        "label": (0, 165, 255),
    },
    ThreatLevel.HIGH: {
        "box": (0, 120, 255),
        "bone": (0, 140, 255),
        "joint": (0, 165, 255),
        "label": (0, 100, 255),
    },
    ThreatLevel.CRITICAL: {
        "box": (0, 0, 255),
        "bone": (50, 50, 255),
        "joint": (0, 0, 255),
        "label": (0, 0, 220),
    },
}

# 6 Person palettes for MediaPipe multi-person tracker (bone, joint, box)
PERSON_PALETTES = [
    {"name": "CYAN", "bone": (0, 255, 255), "joint": (0, 255, 0), "box": (0, 255, 127)},
    {"name": "ORANGE", "bone": (0, 140, 255), "joint": (0, 215, 255), "box": (0, 165, 255)},
    {"name": "MAGENTA", "bone": (255, 0, 255), "joint": (255, 105, 180), "box": (255, 0, 255)},
    {"name": "BLUE", "bone": (255, 215, 0), "joint": (0, 255, 255), "box": (255, 191, 0)},
    {"name": "GREEN", "bone": (50, 205, 50), "joint": (124, 252, 0), "box": (0, 255, 0)},
    {"name": "RED", "bone": (80, 80, 255), "joint": (0, 215, 255), "box": (0, 69, 255)},
]
