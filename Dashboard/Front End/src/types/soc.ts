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
  ptzEnabled: boolean;
  boundingBoxes: IAiBoundingBox[];
}

export interface ICameraSnapshots {
  preEventSnapshotUrl: string;
  eventPeakSnapshotUrl: string;
}

export interface IIncidentItem {
  id: string;
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
  status: 'PENDING_VERIFICATION' | 'OPERATOR_CONFIRMED' | 'DISMISSED';
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
