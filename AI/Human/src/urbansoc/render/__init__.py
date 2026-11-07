"""SOC Rendering and HUD composition package."""

from urbansoc.render.hud import (
    draw_diagnostic_alert_box,
    draw_soc_hud_dashboard,
)
from urbansoc.render.skeleton import (
    draw_corner_bounding_box,
    draw_pose_skeleton_and_indicators,
)
from urbansoc.render.theme import PERSON_PALETTES, THREAT_COLORS

__all__ = [
    "THREAT_COLORS",
    "PERSON_PALETTES",
    "draw_corner_bounding_box",
    "draw_pose_skeleton_and_indicators",
    "draw_soc_hud_dashboard",
    "draw_diagnostic_alert_box",
]
