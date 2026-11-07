/**
 * CYBERGUARD AI · SOC v2.1 — DATA CONTRACTS & TYPE DEFINITIONS
 * Đồng bộ với SPEC.md và Dashboard/Back End/standard.md
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
}

export interface ICompactAlertLog {
  id: string;
  eventId: string;
  timestamp: string;
  cameraId: string;
  cameraName: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  behavior: string;
  confidence?: number;
  status: string;
  reasoningSnippet: string;
  rawIncident?: IIncidentItem;
}

export interface ICameraSnapshots {
  preEventSnapshotUrl: string;
  eventPeakSnapshotUrl: string;
}

export interface IDeepSeekObjectDescription {
  primary_action: string;
  role: 'suspect' | 'victim' | 'bystander' | string;
  posture_details: string;
  weapon_detected: string | null;
  weapon_confidence: number;
  kinematics_summary: string;
  keypoints_count: number;
}

export interface IDeepSeekParsedJson {
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  threat_verdict: string;
  investigation_summary: string;
  object_description: IDeepSeekObjectDescription;
}

export interface IStandardKvIncidentOutput {
  event_id: string;
  raw_response: string;
  parsed_json: IDeepSeekParsedJson;
  model_used: string;
  latency_ms: number;
  timestamp: string;
  id?: string;
  camera_id?: string;
  location_name?: string;
  operator_status?: 'PENDING_VERIFICATION' | 'AWAITING_OPERATOR_VERIFICATION' | 'OPERATOR_CONFIRMED' | 'DISMISSED';
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
  cameraSnapshots?: ICameraSnapshots | null;
  playbackUrl?: string | null;
  vlmAnalysis?: string;
  rawResponse?: string;
  status: 'PENDING_VERIFICATION' | 'OPERATOR_CONFIRMED' | 'DISMISSED';

  // Rich metadata from parsed_json
  threatVerdict?: string;
  role?: string;
  postureDetails?: string;
  kinematicsSummary?: string;
  weaponDetected?: string | null;
  weaponConfidence?: number;
  keypointsCount?: number;
  modelUsed?: string;
  latencyMs?: number;
  parsedJson?: IDeepSeekParsedJson;
  fullImageBase64?: string | null;
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
