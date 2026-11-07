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
  location?: string;
  address?: string;
  measuredFps?: number;
  frameIndex?: number;
  humanCount?: number;
  lastTimestamp?: string;
}

export interface ICameraSnapshots {
  preEventSnapshotUrl: string;
  eventPeakSnapshotUrl: string;
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
  cameraId?: string | null;
  location?: string;
  measuredFps?: number;
  frameIndex?: number;
  humanCount?: number;
  actionType?: string;
  threatScore?: number;
  confidence?: number;
  isUrgent?: boolean;
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
  fullImageBase64?: string | null;
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
