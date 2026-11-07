"""Domain models for Named Camera Topology, Exit Gates, and Blind-Spot Trajectory Graph."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ExitGateConfig:
    """Boundary escape exit or entry gate configuration on a camera's field of view."""
    gate_id: str  # e.g., "EAST_ALLEY_GATE", "NORTH_STREET_EDGE", "WEST_GATE"
    polygon_coords: List[Tuple[float, float]]  # Normalized [0.0 - 1.0] polygon vertices
    connected_blind_spot_id: str  # e.g., "BS_ZONE_01"
    compass_bearing_deg: float  # e.g. 115.0 degrees
    gate_description: str = ""


@dataclass
class BlindSpotRoute:
    """Navigable route through an unmonitored blind spot linking to another named camera."""
    route_id: str
    target_camera_id: str
    target_camera_name: str
    target_camera_location: str
    distance_meters: float
    route_description: str
    expected_entry_gate: str
    friction_penalty: float = 0.0  # 0.0 - 1.0 (stairs, steep slopes, obstacles, dead-end traps)
    features: List[str] = field(default_factory=list)  # e.g. ["TRASH_BIN", "STAIRS", "PARKING_LOT", "DARK_ALLEY"]
    optimal_heading_deg: float = 0.0


@dataclass
class BlindSpotZone:
    """Unmonitored physical corridor or zone between two or more cameras."""
    zone_id: str  # e.g., "BS_ZONE_01"
    name: str  # e.g., "Hẻm cụt sau trường Chu Văn An nối sang Bãi xe B"
    description: str
    routes: List[BlindSpotRoute] = field(default_factory=list)
    has_dumping_spots: bool = True  # Dumpsters, trash bins, drainage canal
    has_vehicle_access: bool = True  # Motorbike or car escape possible


@dataclass
class NamedCameraNode:
    """Full spatial profile of a camera with semantic name, GPS, azimuth, and exit gates."""
    camera_id: str
    camera_name: str  # Semantic location name, e.g. "CAM_01 - Cổng Trường Chu Văn An"
    physical_location: str  # e.g. "Ngã ba Chu Văn An - Đinh Bộ Lĩnh, P.12, Bình Thạnh"
    gps_lat: float
    gps_lng: float
    azimuth_deg: float  # Center FOV compass angle (0 = North, 90 = East, 180 = South, 270 = West)
    exit_gates: Dict[str, ExitGateConfig] = field(default_factory=dict)
    connected_blind_spots: List[str] = field(default_factory=list)


@dataclass
class SubjectTacticalProfile:
    """Biomechanical, psychological, and kinematic tactical evaluation of suspect entering blind spot."""
    dominant_hand: str  # "RIGHT" | "LEFT" | "AMBIDEXTROUS_UNKNOWN"
    active_holding_hand: str  # "RIGHT_HAND" | "LEFT_HAND" | "BOTH_HANDS" | "NONE"
    held_object_description: str  # e.g. "Dao găm ở tay phải / Túi xách màu đen ở tay trái"
    gait_and_biomechanics: str
    psychological_state: str  # "PREMEDITATED_CALM" | "HIGH_PANIC" | "AGGRESSIVE_CONFRONTATIONAL"
    psychological_evidence: str
    exit_velocity_mps: float
    exit_heading_compass_deg: float


@dataclass
class PredictedTargetCamera:
    """Probabilistic prediction of next appearance at a connected named camera."""
    rank: int
    target_camera_id: str
    target_camera_name: str
    target_camera_location: str
    route_id: str
    route_description: str
    blind_spot_distance_meters: float
    expected_entry_gate_on_target_cam: str
    probability: float
    estimated_arrival_seconds: Tuple[int, int]
    expected_arrival_timestamp_window: Tuple[str, str]
    predicted_hidden_actions_in_blind_spot: List[str]
    score_breakdown: Dict[str, float]
    detailed_tactical_reasoning: str
