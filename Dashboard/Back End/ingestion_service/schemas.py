from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict

# ==========================================
# 1. SESSION DOMAIN
# ==========================================
class SessionData(BaseModel):
    model_config = ConfigDict(extra="allow")
    authenticated: bool = False
    user: Optional[Dict[str, Any]] = None

# ==========================================
# 2. CONFIG DOMAIN
# ==========================================
class BrandConfig(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str = "CYBERGUARD"
    product: str = "AI · SOC"
    version: str = "2.1"

class SiteConfig(BaseModel):
    model_config = ConfigDict(extra="allow")
    site_id: str
    name: str

class DisplayConfig(BaseModel):
    model_config = ConfigDict(extra="allow")
    timezone: str = "UTC"
    refresh_interval_ms: int = 1000

class NavigationSectionItem(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    label: str
    icon: Optional[str] = None
    route: str
    badge_key: Optional[str] = None

class NavigationSection(BaseModel):
    model_config = ConfigDict(extra="allow")
    section_id: str
    title: str
    items: List[NavigationSectionItem] = []

class NavigationConfig(BaseModel):
    model_config = ConfigDict(extra="allow")
    sections: List[NavigationSection] = []
    footer_items: List[Dict[str, Any]] = []

class ThresholdsConfig(BaseModel):
    model_config = ConfigDict(extra="allow")
    stream_latency_ms: Optional[Dict[str, int]] = None
    nvr_storage_used_percent: Optional[Dict[str, int]] = None
    poe_load_percent: Optional[Dict[str, int]] = None

class ThreatScoreBand(BaseModel):
    model_config = ConfigDict(extra="allow")
    min: int
    max: int
    level: str
    risk_label: str

class ThreatScoreConfig(BaseModel):
    model_config = ConfigDict(extra="allow")
    max_score: int = 100
    gauge_segments_total: int = 15
    bands: List[ThreatScoreBand] = []

class CameraMatrixConfig(BaseModel):
    model_config = ConfigDict(extra="allow")
    title: str = "LIVE CAMERA MATRIX"
    supported_layouts: List[str] = ["1x1", "2x2", "3x3", "4x4"]
    default_layout: str = "2x2"
    toolbar_actions: List[str] = []
    tile_controls: List[str] = []
    bounding_box_format: Dict[str, Any] = {}

class SystemConfigData(BaseModel):
    model_config = ConfigDict(extra="allow")
    brand: Optional[BrandConfig] = None
    site: Optional[SiteConfig] = None
    display: Optional[DisplayConfig] = None
    navigation: Optional[NavigationConfig] = None
    enums: Optional[Dict[str, List[str]]] = None
    severity_palette: Optional[Dict[str, str]] = None
    thresholds: Optional[ThresholdsConfig] = None
    threat_score: Optional[ThreatScoreConfig] = None
    camera_matrix: Optional[CameraMatrixConfig] = None

# ==========================================
# 3. CAMERA FLEET REGISTRY DOMAIN
# ==========================================
class PTZConfig(BaseModel):
    model_config = ConfigDict(extra="allow")
    supported: bool = False
    presets: List[str] = []

class CameraConfigItem(BaseModel):
    model_config = ConfigDict(extra="allow")
    camera_id: str
    location_name: str
    zone: str
    ip_address: str
    codec: str
    resolution: str
    webrtc_endpoint: str
    ptz: PTZConfig

# ==========================================
# 4. LIVE TELEMETRY META DOMAIN
# ==========================================
class LiveMetaData(BaseModel):
    model_config = ConfigDict(extra="allow")
    sequence: int
    generated_at: str
    stream_mode: str = "LIVE"

# ==========================================
# 5. LIVE SYSTEM STATE DOMAIN
# ==========================================
class LiveSystemData(BaseModel):
    model_config = ConfigDict(extra="allow")
    state: str = "ACTIVE"
    engine_status: str = "ONLINE"
    threat_db: Dict[str, str] = {}
    unread_badges: Dict[str, int] = {}
    notifications_unread: int = 0

# ==========================================
# 6. DYNAMIC THREAT OVERVIEW DOMAIN
# ==========================================
class OpenThreatsSummary(BaseModel):
    model_config = ConfigDict(extra="allow")
    by_severity: Dict[str, int] = Field(default_factory=dict)

class ThreatOverviewData(BaseModel):
    model_config = ConfigDict(extra="allow")
    threat_score: int = Field(ge=0, le=100)
    open_threats: OpenThreatsSummary

# ==========================================
# 7. FLEET KPI & HEALTH DOMAIN
# ==========================================
class OfflineCameraItem(BaseModel):
    model_config = ConfigDict(extra="allow")
    camera_id: str
    reason: str
    last_seen_at: str

class CameraFleetKPI(BaseModel):
    model_config = ConfigDict(extra="allow")
    total: int
    online: int
    offline: List[OfflineCameraItem] = []

class KPIData(BaseModel):
    model_config = ConfigDict(extra="allow")
    stream_latency_ms: int
    camera_fleet: CameraFleetKPI

# ==========================================
# 8. INFRASTRUCTURE TELEMETRY DOMAIN
# ==========================================
class NVRStorageData(BaseModel):
    model_config = ConfigDict(extra="allow")
    used_tb: float
    capacity_tb: float

class PoEData(BaseModel):
    model_config = ConfigDict(extra="allow")
    state: str
    load_watts: float
    capacity_watts: float

class InfrastructureData(BaseModel):
    model_config = ConfigDict(extra="allow")
    nvr_storage: NVRStorageData
    poe: PoEData

# ==========================================
# 9. LIVE CAMERA MATRIX & AI DETECTIONS DOMAIN
# ==========================================
class BoundingBox(BaseModel):
    model_config = ConfigDict(extra="allow")
    x_min: float = Field(ge=0.0, le=1.0)
    y_min: float = Field(ge=0.0, le=1.0)
    x_max: float = Field(ge=0.0, le=1.0)
    y_max: float = Field(ge=0.0, le=1.0)

class DetectionItem(BaseModel):
    model_config = ConfigDict(extra="allow")
    detection_id: str
    track_id: str
    incident_id: Optional[str] = None
    object_class: str
    label: str
    confidence: float = Field(ge=0.0, le=1.0)
    severity: str
    detected_at: str
    bbox: BoundingBox

class PTZLiveTelemetry(BaseModel):
    model_config = ConfigDict(extra="allow")
    preset: Optional[str] = None
    pan: float = 0.0
    tilt: float = 0.0
    zoom: float = 1.0

class MatrixTileItem(BaseModel):
    model_config = ConfigDict(extra="allow")
    slot: int
    camera_id: str
    status: str
    telemetry: Dict[str, Any] = {}
    ptz: Optional[PTZLiveTelemetry] = None
    detections: List[DetectionItem] = []

class CameraMatrixPayload(BaseModel):
    model_config = ConfigDict(extra="allow")
    layout: str = "2x2"
    tiles: List[MatrixTileItem] = []

# ==========================================
# 10. SECURITY INCIDENTS & THREAT FEED DOMAIN
# ==========================================
class PlaybackInfo(BaseModel):
    model_config = ConfigDict(extra="allow")
    available: bool = False
    video_url: Optional[str] = None
    start_offset_sec: int = 0
    duration_sec: int = 0

class RecentThreatItem(BaseModel):
    model_config = ConfigDict(extra="allow")
    incident_id: str
    detected_at: str
    updated_at: str
    event_type: str
    title: str
    severity: str
    status: str
    assignee: Optional[str] = None
    zone: str
    primary_camera_id: str
    related_camera_ids: List[str] = []
    detection_ids: List[str] = []
    snapshots: List[str] = []
    playback: Optional[PlaybackInfo] = None

# ==========================================
# 11. FULL COMPOSITE MASTER PAYLOAD
# ==========================================
class FullConfigContainer(BaseModel):
    model_config = ConfigDict(extra="allow")
    brand: Optional[BrandConfig] = None
    site: Optional[SiteConfig] = None
    display: Optional[DisplayConfig] = None
    navigation: Optional[NavigationConfig] = None
    enums: Optional[Dict[str, List[str]]] = None
    severity_palette: Optional[Dict[str, str]] = None
    thresholds: Optional[ThresholdsConfig] = None
    threat_score: Optional[ThreatScoreConfig] = None
    camera_matrix: Optional[CameraMatrixConfig] = None
    cameras: List[CameraConfigItem] = []

class FullLiveContainer(BaseModel):
    model_config = ConfigDict(extra="allow")
    meta: Optional[LiveMetaData] = None
    system: Optional[LiveSystemData] = None
    threat_overview: Optional[ThreatOverviewData] = None
    kpi: Optional[KPIData] = None
    infrastructure: Optional[InfrastructureData] = None
    camera_matrix: Optional[CameraMatrixPayload] = None
    recent_threats: List[RecentThreatItem] = []

class FullCyberguardPayload(BaseModel):
    model_config = ConfigDict(extra="allow")
    schema_version: str = "1.0.0"
    session: Optional[SessionData] = None
    config: Optional[FullConfigContainer] = None
    live: Optional[FullLiveContainer] = None
