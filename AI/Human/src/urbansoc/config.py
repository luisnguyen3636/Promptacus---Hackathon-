"""Configuration data structures and YAML loader."""

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import yaml

# ==============================================================================
# HARDCODED DESTINATION URL FOR DOWNSTREAM AI MODEL (E.G. DEEPSEEK V4 FLASH / URBANSTRIKE)
# Mọi sự cố phát hiện (High/Critical) sẽ được tự động gửi thẳng tới URL này
# mà KHÔNG CẦN BƯỚC DUYỆT (NO OPERATOR APPROVAL REQUIRED).
# ==============================================================================
HARDCODED_MODEL_URL = os.environ.get(
    "INCIDENT_MODEL_URL",
    "https://urbanstrike.tech/api/incident"
)


@dataclass
class DetectorConfig:
    model_weights: str = "yolo/yolo11n-pose.pt"
    device: Optional[str] = None
    conf_threshold: float = 0.25
    iou_threshold: float = 0.45
    track_activation_threshold: float = 0.25
    lost_track_buffer: int = 45
    minimum_matching_threshold: float = 0.80
    keypoint_confidence_threshold: float = 0.25


@dataclass
class BehaviorConfig:
    history_window_size: int = 30
    fall_angle_threshold: float = 55.0
    fall_aspect_ratio_thresh: float = 0.90
    run_speed_multiplier: float = 1.75
    loiter_time_threshold: float = 10.0
    fight_wrist_energy_thresh: float = 1200.0
    fight_distance_norm: float = 1.35
    enter_debounce_frames: int = 8
    exit_debounce_frames: int = 12
    fast_track_debounce_frames: int = 6
    bbox_ema_alpha: float = 0.65
    track_disappeared_timeout: float = 5.0
    heartbeat_interval: float = 1.0


@dataclass
class EvidenceConfig:
    pre_roll_seconds: float = 1.5
    post_roll_seconds: float = 2.0
    trigger_policy: str = "HUMAN_PRESENCE"
    threat_threshold: str = "HIGH"


@dataclass
class RenderConfig:
    show_skeleton: bool = True
    show_debug_box: bool = True
    hud_height_px: int = 44
    debug_box_width_px: int = 410
    debug_box_height_px: int = 165


@dataclass
class AppConfig:
    mode: str = "live"
    camera_index: int = 0
    fps: float = 20.0
    resolution: Tuple[int, int] = (640, 480)
    output_dir: str = "output"
    records_dir: str = "records"
    record_all: bool = False

    detector: DetectorConfig = field(default_factory=DetectorConfig)
    behavior: BehaviorConfig = field(default_factory=BehaviorConfig)
    evidence: EvidenceConfig = field(default_factory=EvidenceConfig)
    render: RenderConfig = field(default_factory=RenderConfig)


def load_config(yaml_path: Optional[str] = None, overrides: Optional[Dict[str, Any]] = None) -> AppConfig:
    """Load configuration from YAML file and apply optional overrides."""
    config = AppConfig()

    if yaml_path and os.path.exists(yaml_path):
        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            if "system" in data:
                sys_cfg = data["system"]
                config.fps = float(sys_cfg.get("fps", config.fps))
                res = sys_cfg.get("resolution", config.resolution)
                config.resolution = (int(res[0]), int(res[1]))

            if "detector" in data:
                det = data["detector"]
                config.detector.model_weights = det.get("model_weights", config.detector.model_weights)
                config.detector.conf_threshold = float(det.get("conf_threshold", config.detector.conf_threshold))
                config.detector.iou_threshold = float(det.get("iou_threshold", config.detector.iou_threshold))
                config.detector.track_activation_threshold = float(det.get("track_activation_threshold", config.detector.track_activation_threshold))
                config.detector.lost_track_buffer = int(det.get("lost_track_buffer", config.detector.lost_track_buffer))
                config.detector.minimum_matching_threshold = float(det.get("minimum_matching_threshold", config.detector.minimum_matching_threshold))
                config.detector.keypoint_confidence_threshold = float(det.get("keypoint_confidence_threshold", config.detector.keypoint_confidence_threshold))

            if "paths" in data:
                paths = data["paths"]
                config.output_dir = paths.get("output_dir", config.output_dir)
                config.records_dir = paths.get("records_dir", config.records_dir)
        except Exception:
            pass

    if overrides:
        for k, v in overrides.items():
            if v is not None:
                if hasattr(config, k):
                    setattr(config, k, v)
                elif hasattr(config.detector, k):
                    setattr(config.detector, k, v)

    return config
