/**
 * CYBERGUARD SOC — DATA CONTRACTS & TYPE DEFINITIONS
 * Pure Display & Operational HITL Dashboard synchronized with Cloudflare KV.
 */

export type ThreatLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type SystemStatus = 'SAFE' | 'GUARDED' | 'ELEVATED' | 'SEVERE';
export type IncidentSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type IncidentCategory = 'NETWORK' | 'PHYSICAL_CAMERA' | 'ACCESS_CONTROL';

export interface ISocMetrics {
  latencyMs: number;
  downloadMbps: number;
  uploadMbps: number;
  activeNodes: number;
  camerasOnline: number;
  camerasTotal: number;
  packetLossPercent: number;
  openThreats: number;
  criticalThreats: number;
  nvrStoragePercent: number;
  poeLoadWatts: number;
}

export interface ISocOverview {
  threatLevel: ThreatLevel;
  threatScore: number;
  status: SystemStatus;
  timestampUtc: string;
  metrics: ISocMetrics;
}

export interface ISubjectKeypoint {
  id: number;
  name: string;
  x: number;
  y: number;
  confidence: number;
}

export interface ISubjectKinematics {
  spine_angle?: number;
  left_elbow_angle?: number;
  right_elbow_angle?: number;
  left_arm_extension?: number;
  right_arm_extension?: number;
  aspect_ratio?: number;
  wrist_distance?: number;
  wrist_velocity?: number;
}

export interface IDetectionSubject {
  track_id: number;
  role: string;
  behavior: string;
  threat_level: string;
  threat_score: number;
  confidence: number;
  bbox: [number, number, number, number];
  speed?: number;
  velocity_vector?: [number, number];
  kinematics?: ISubjectKinematics;
  keypoints?: ISubjectKeypoint[];
  crop_image_base64?: string;
  crop_image_sha256?: string;
  crop_image_size_bytes?: number;
}

export interface IActionValidation {
  is_valid: boolean;
  validation_source?: string;
  detected_action?: string;
  severity?: string;
  threat_score?: number;
  benign_hypothesis_probability?: number;
  reasoning?: string;
}

export interface IWeaponInfo {
  is_weapon_detected: boolean;
  weapon_types?: string[];
  confidence?: number;
  description?: string;
}

export interface IServerCameraMeta {
  camera_id: string;
  name?: string;
  zone_id?: string;
  address?: string;
  latitude?: number;
  longitude?: number;
}

export interface IServerAuditInfo {
  frame_index?: number;
  human_count?: number;
  action_confirmed?: boolean;
  ai_verified?: boolean;
  ai_model?: string;
  hash_algorithm?: string;
  verification_status?: string;
}

export interface IServerAudioInfo {
  is_audio_active?: boolean;
  audio_threat_detected?: boolean;
}

export interface IAiBoundingBox {
  id: string;
  label: string;
  subLabel?: string;
  confidence?: number;
  severity: 'NORMAL' | 'HIGH' | 'CRITICAL';
  x: number; // 0.0 - 1.0 (relative)
  y: number; // 0.0 - 1.0 (relative)
  w: number; // 0.0 - 1.0 (relative)
  h: number; // 0.0 - 1.0 (relative)
  keypoints?: ISubjectKeypoint[];
}

export interface IServerActor {
  id: number | string;
  role: string;
  action: string;
  posture: string;
  interacting_with?: number | string | null;
  bbox?: [number, number, number, number];
}

export interface IServerVisualCues {
  weapons_visible: boolean;
  physical_contact: boolean;
  fallen_person: boolean;
}

export interface INvidiaVlmAnalysis {
  severity: string;
  timestamp: string;
  action_type: string;
  confidence: number;
  threat_score: number;
  description: string;
  reasoning: string;
  actors?: IServerActor[];
  visual_cues?: IServerVisualCues;
  recommended_action?: string;
  is_urgent?: boolean;
  camera_id?: string;
  location?: string;
  source?: string;
}

export interface ICameraDevice {
  id: string;
  name: string;
  ip: string;
  fps: number;
  bitrateKbps: number;
  status: 'ONLINE' | 'OFFLINE' | 'DEGRADED';
  streamUrl: string;
  directStreamUrl?: string;
  ptzEnabled: boolean;
  ptzState?: {
    zoom: number;
    pan: number;
    tilt: number;
    focus: string;
  };
  boundingBoxes: IAiBoundingBox[];
  zoneId?: string;
  location?: string;
  address?: string;
  measuredFps?: number;
  frameIndex?: number;
  humanCount?: number;
  latitude?: number;
  longitude?: number;
  lastTimestamp?: string;
  lastSnapshotBase64?: string;
}

export interface ICameraSnapshots {
  preEventSnapshotUrl?: string;
  eventPeakSnapshotUrl?: string;
  handCropSnapshotUrl?: string;
}

export interface IIncidentItem {
  id: string;
  eventId?: string;
  title: string;
  subTitle?: string;
  sourceIp: string;
  category: IncidentCategory;
  severity: IncidentSeverity;
  timestamp: string;
  timestampMs?: number;
  cameraId?: string | null;
  cameraName?: string;
  location?: string;
  measuredFps?: number;
  frameIndex?: number;
  humanCount?: number;
  actionType?: string;
  primaryAction?: string;
  threatLevel?: IncidentSeverity;
  threatScore?: number;
  confidence?: number;
  isUrgent?: boolean;
  actionConfirmed?: boolean;
  aiVerified?: boolean;
  actionValidation?: IActionValidation;
  weaponInfo?: IWeaponInfo;
  description?: string;
  reasoning?: string;
  recommendedAction?: string;
  actors?: IServerActor[];
  visualCues?: IServerVisualCues;
  nvidiaVlmAnalysis?: INvidiaVlmAnalysis;
  cameraSnapshots?: ICameraSnapshots | null;
  playbackUrl?: string | null;
  vlmAnalysis?: string;
  rawResponse?: string;
  status: 'PENDING_VERIFICATION' | 'OPERATOR_CONFIRMED' | 'DOWNGRADED_MONITORING' | 'DISMISSED';

  // Extended forensic & multimodal fields from Server JSON
  forensicSha256?: string;
  subjects?: IDetectionSubject[];
  fullImageBase64?: string | null;
  subjectCropBase64?: string | null;
  handCropBase64?: string | null;
  imageUrl?: string;
  handCropUrl?: string;
  cameraMeta?: IServerCameraMeta;
  auditInfo?: IServerAuditInfo;
  audioInfo?: IServerAudioInfo;

  // Legacy fields for backwards compatibility
  threatVerdict?: string;
  role?: string;
  postureDetails?: string;
  kinematicsSummary?: string;
  weaponDetected?: string | null;
  weaponConfidence?: number;
  keypointsCount?: number;
  modelUsed?: string;
  latencyMs?: number;
}

export interface ISocSettings {
  operatorId: string;
  operatorName: string;
  shiftRotation: string;
  liveStreamUrl: string;
  criticalThreshold: number;
  preBufferSeconds: number;
  postBufferSeconds: number;
  dispatchWebhook: string;
  autoSirenOnCritical: boolean;
  updatedAt?: string;
}

export interface IOperatorSession {
  token: string;
  operatorId: string;
  operatorName: string;
  role: string;
  shift: string;
  loggedInAt: string;
}

export interface IPtzCommandPayload {
  action: 'ZOOM_IN' | 'ZOOM_OUT' | 'PAN' | 'AUTO_FOCUS';
  speed?: number;
}

export interface IOperatorVerifyPayload {
  incidentId: string;
  operatorId: string;
  decision: 'CONFIRM_AND_DISPATCH' | 'DOWNGRADE_MONITOR' | 'DISMISS_FALSE_POSITIVE';
  notes?: string;
  verifiedAt: string;
}
