/**
 * CYBERGUARD AI · PSOC v3.0 — DATA CONTRACTS & TYPE DEFINITIONS
 * Đồng bộ với SPEC.md và Dashboard Backend standard
 */

export type ThreatLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type SystemStatus = 'SAFE' | 'GUARDED' | 'ELEVATED' | 'SEVERE';
export type IncidentSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type IncidentCategory = 'NETWORK' | 'PHYSICAL_CAMERA' | 'ACCESS_CONTROL' | 'CRIMINAL_BEHAVIOR';

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
  wantedCount?: number;
  blindSpotSessionsCount?: number;
  vlmVerifiedCount?: number;
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

export interface IAiCameraAlert {
  hasAlert: boolean;
  type: string;
  severity: 'NORMAL' | 'HIGH' | 'CRITICAL';
  message?: string;
  confidence?: number;
  timestamp?: number;
  aiProvider?: string | null;
  model?: string | null;
  threatScore?: number;
}

export interface ICameraDevice {
  id: string;
  name: string;
  ip: string;
  fps: number;
  bitrateKbps: number;
  status: 'ONLINE' | 'OFFLINE' | 'DEGRADED';
  streamUrl: string;
  snapshotUrl?: string;
  ptzEnabled: boolean;
  aiAlert?: IAiCameraAlert | null;
  boundingBoxes: IAiBoundingBox[];
  threatScore: number;
  threatLevel: ThreatLevel;
  resolution?: string;
  codec?: string;
  latencyMs?: number;
  connectedBlindSpots?: string[];
  inspectionStatus?: 'HEALTHY' | 'ATTENTION' | 'OFFLINE';
  lastPingAt?: string;
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
  cameraName?: string | null;
  cameraSnapshots?: ICameraSnapshots | null;
  playbackUrl?: string | null;
  vlmAnalysis?: string;
  aiVerified?: boolean;
  aiProvider?: string | null;
  threatScore?: number;
  primaryAction?: string;
  criminalCategory?: string;
  nvidiaVlmAnalysis?: Record<string, unknown> | null;
  status: 'AI_VERIFICATION_PENDING' | 'PENDING_VERIFICATION' | 'OPERATOR_CONFIRMED' | 'DISMISSED' | 'DOWNGRADED_MONITORING';
}

export interface IPtzCommandPayload {
  action: 'ZOOM_IN' | 'ZOOM_OUT' | 'PAN' | 'TILT' | 'AUTO_FOCUS';
  speed?: number;
}

export interface IOperatorVerifyPayload {
  incidentId: string;
  operatorId: string;
  decision: 'CONFIRM_AND_DISPATCH' | 'DOWNGRADE_MONITOR' | 'DISMISS_FALSE_POSITIVE';
  notes?: string;
  verifiedAt: string;
}

// Bằng chứng đóng dấu pháp y vào hồ sơ truy nã
export interface IEvidenceStamp {
  stampId: string;
  incidentId?: string;
  evidenceType: 'KEYFRAME_SNAPSHOT' | 'VIDEO_CLIP' | 'FORENSIC_CROP';
  evidenceUrl: string;
  sha256Hash: string;
  stampedBy: string;
  stampedAt: string;
  notes?: string;
}

// Đối tượng trong Danh Sách Truy Nã
export interface IWantedPerson {
  id: string;
  name: string;
  alias?: string;
  threatLevel: 'CRITICAL' | 'HIGH' | 'MEDIUM';
  status: 'WANTED' | 'APPREHENDED' | 'RED_ALERT' | 'MONITORING';
  charges: string[];
  identificationFeatures: {
    height?: string;
    build?: string;
    clothing?: string;
    distinguishingMarks?: string;
  };
  avatarUrl?: string;
  lastSeenCameraId?: string;
  lastSeenLocation?: string;
  lastSeenTimestamp?: string;
  evidenceStamps: IEvidenceStamp[];
  createdAt?: string;
  updatedAt?: string;
}

// Phiên suy luận vùng mù đa camera
export interface IBlindSpotCandidate {
  targetCameraId: string;
  targetCameraName: string;
  distanceMeters: number;
  estimatedTransitSec: number;
  softmaxProbability: number;
  arrivalWindow: string;
}

export interface IBlindSpotSession {
  sessionId: string;
  status: string;
  sourceCameraId: string;
  sourceCameraName: string;
  sourceKeyframeUrl: string;
  sourceExitTime: string;
  exitGate: string;
  blindSpotZone: string;
  blindSpotDescription: string;
  targetCandidates: IBlindSpotCandidate[];
  destinationCameraId: string;
  destinationCameraName: string;
  destinationKeyframeUrl: string;
  destinationEntryTime: string;
  actualTransitSec: number;
  reidSimilarityScore: number;
  clothingMatch: {
    upperBody?: string;
    lowerBody?: string;
    accessories?: string;
  };
  hiddenActionPredictions: string[];
  operatorVerification: 'CONFIRMED' | 'AWAITING_CONFIRMATION' | 'REJECTED';
  verifiedBy?: string | null;
  verifiedAt?: string | null;
}
