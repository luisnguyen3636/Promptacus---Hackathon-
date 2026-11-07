/**
 * TypeScript Data Models and Interfaces for Urban Safety AI-SOC Cloudflare Worker.
 * Unified Edge Stack: React Static Assets, REST APIs, WebSockets, Workers AI, D1 Database.
 * Adheres strictly to SPEC-CF-UNIFIED-SOC-01, SPEC-AI-REAL-INGESTION-01, and standard.md.
 */

export interface Env {
  AI: any;                      // Cloudflare Workers AI Binding
  DB: D1Database;               // Cloudflare D1 SQL Database Binding
  INCIDENT_CACHE?: KVNamespace; // Cloudflare KV Cache
  ASSETS?: Fetcher;             // Cloudflare Workers Static Assets Fetcher
  ENVIRONMENT?: string;
  API_AUTH_TOKEN?: string;
  DEFAULT_AI_MODEL?: string;
  FALLBACK_AI_MODEL?: string;
  ALLOWED_ORIGINS?: string;     // Comma-separated CORS allowed origins
  ALLOWED_IPS?: string;         // Comma-separated IP / CIDR whitelist
  ENFORCE_IP_WHITELIST?: string;// "true" to enforce strict IP blocking
}

// =============================================================================
// 1. Telemetry & Overview Types
// =============================================================================

export interface ISocOverviewResponse {
  threatLevel: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  threatScore: number;
  status: "SAFE" | "GUARDED" | "ELEVATED" | "SEVERE";
  timestampUtc: string;
  metrics: {
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
  };
}

// =============================================================================
// 2. Camera, AI Tracking & PTZ Types
// =============================================================================

export interface IAIBoundingBox {
  id: string;
  label: string;
  subLabel: string;
  severity: "NORMAL" | "HIGH" | "CRITICAL";
  x: number; // Normalized 0.0 - 1.0
  y: number;
  w: number;
  h: number;
  trackId?: number;
  confidence?: number;
  keypoints?: Array<{ id: number; name: string; x: number; y: number; confidence: number }>;
}

export interface IPtzState {
  zoom: number;
  pan: number;
  tilt: number;
  focus: string;
}

export interface ICameraDevice {
  id: string;
  name: string;
  ip: string;
  fps: number;
  bitrateKbps: number;
  status: "ONLINE" | "OFFLINE" | "DEGRADED";
  streamUrl: string;
  ptzEnabled: boolean;
  ptzState: IPtzState;
  boundingBoxes: IAIBoundingBox[];
  zoneId?: string;
  address?: string;
  latitude?: number;
  longitude?: number;
  lastSnapshotBase64?: string;
}

export interface IPtzCommandRequest {
  action: "ZOOM_IN" | "ZOOM_OUT" | "PAN" | "AUTO_FOCUS";
  speed?: number;
}

// =============================================================================
// 3. Incident & Playback Types
// =============================================================================

export interface IIncidentItem {
  id: string;
  title: string;
  subTitle: string;
  sourceIp: string;
  category: "NETWORK" | "PHYSICAL_CAMERA";
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  timestamp: string;
  cameraId?: string | null;
  cameraSnapshots?: {
    preEventSnapshotUrl?: string;
    eventPeakSnapshotUrl?: string;
  } | null;
  playbackUrl?: string | null;
  status: "PENDING_VERIFICATION" | "OPERATOR_CONFIRMED" | "DOWNGRADED_MONITORING" | "DISMISSED";
  vlmAnalysis?: string;
  rawDetection?: any;
  forensicSha256?: string;
  subjects?: IAISubjectData[];
  fullImageBase64?: string;
}

export interface IIncidentPlaybackResponse {
  incidentId: string;
  title: string;
  cameraId?: string | null;
  timestamp: string;
  bufferRange: {
    preEventSeconds: number;
    postEventSeconds: number;
    totalDurationSeconds: number;
  };
  vlmReasoning?: string;
  visualEvidence: {
    preEventSnapshot: string | null;
    eventPeakSnapshot: string | null;
    streamPlaybackUrl: string | null;
  };
  status: string;
  forensicSha256?: string;
  fullImageBase64?: string;
  subjects?: IAISubjectData[];
}

export interface IGenericIncidentPostPayload {
  incident_id?: string;
  title?: string;
  severity?: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  camera_id?: string;
  zone_id?: string;
  location_name?: string;
  description?: string;
  source_ip?: string;
  evidence_url?: string;
  raw_payload?: Record<string, any>;
  [key: string]: any;
}

export interface IIncidentPostResponse {
  success: boolean;
  message: string;
  log_id: string;
  incident_id: string;
  timestamp: string;
  status: string;
  operator_status: string;
  audit: {
    action: string;
    actor: string;
    storage: string;
  };
  incident?: IIncidentItem;
}

// =============================================================================
// 4. Operational HITL & Dispatch Types (CD-04)
// =============================================================================

export interface IHitlVerificationRequest {
  operatorId: string; // Mandatory [CD-04]
  decision: "CONFIRM_AND_DISPATCH" | "DOWNGRADE_MONITOR" | "DISMISS_FALSE_POSITIVE";
  notes?: string;
  verifiedAt?: string;
}

export interface IIncidentDispatchPackage {
  packageId: string;
  incidentId: string;
  dispatchedByOperator: string;
  verifiedAt: string;
  camera?: {
    id: string;
    name: string;
    zoneId?: string;
    address?: string;
  };
  coordinates: {
    latitude: number;
    longitude: number;
  };
  threatAssessment?: {
    severity: string;
    threatScore: number;
    reasoning?: string;
  };
  visualEvidence?: {
    annotatedSnapshot?: string | null;
    subjectCrop?: string | null;
    evidenceClipUrl?: string | null;
  };
  dispatchStatus?: string;
  urgency: "IMMEDIATE_INTERVENTION" | "MONITOR_ONLY" | "NONE";
  notes: string;
  evidenceClipUrl?: string;
}

export interface IHitlVerificationResponse {
  success: boolean;
  decision: string;
  auditEntry: {
    auditId: string;
    incidentId: string;
    operatorId: string;
    decision: string;
    timestamp: string;
    status: string;
  };
  incidentPackage: IIncidentDispatchPackage | null;
  systemThreatScore: number;
}

// =============================================================================
// 5. WebSocket Live Protocol Types
// =============================================================================

export type WebSocketServerMessage =
  | {
      type: "CONNECTED";
      serverTime: string;
    }
  | {
      type: "TELEMETRY_AND_AI_TICK";
      cameras: ICameraDevice[];
      timestamp: number;
    }
  | {
      type: "NEW_INCIDENT";
      incident: IIncidentItem;
      timestamp: number;
    };

// =============================================================================
// 6. Real AI Detection Payload (Sent from AI/Human WebhookDispatcher)
// =============================================================================

export interface IAISubjectKeypoint {
  id: number;
  name: string;
  x: number;
  y: number;
  confidence: number;
}

export interface IAISubjectKinematics {
  spine_angle: number;
  aspect_ratio: number;
  left_elbow_angle: number;
  right_elbow_angle: number;
  left_arm_extension: number;
  right_arm_extension: number;
  wrist_distance: number;
  wrist_velocity: number;
}

export interface IAISubjectData {
  track_id: number;
  role: "suspect" | "victim" | "participant" | "bystander" | string;
  behavior: string;
  threat_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  threat_score: number;
  confidence: number;
  bbox: [number, number, number, number]; // [x1, y1, x2, y2]
  bbox_geometry: {
    width: number;
    height: number;
    aspect_ratio: number;
    area: number;
  };
  dwell_time_seconds: number;
  speed: number;
  velocity_vector: [number, number];
  kinematics: IAISubjectKinematics;
  keypoints: IAISubjectKeypoint[];
  crop_image_base64?: string;
  crop_image_sha256?: string;
  crop_image_size_bytes?: number;
}

export interface IAIRealDetectionPayload {
  event_id: string;
  timestamp: string;
  timestamp_ms: number;
  camera: {
    camera_id: string;
    name: string;
    zone_id: string;
    address: string;
    latitude: number;
    longitude: number;
  };
  detection: {
    primary_action: string;
    threat_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
    threat_score: number;
    is_urgent: boolean;
    reasoning: string;
    weapon: {
      is_weapon_detected: boolean;
      weapon_types: string[];
      confidence: number;
      description: string;
    };
    subjects: IAISubjectData[];
    full_image: {
      format: string;
      width: number;
      height: number;
      image_base64: string;
      sha256_hash: string;
      image_size_bytes: number;
    };
    audio?: {
      screaming_detected: boolean;
      gunshot_detected: boolean;
      decibel_peak: number;
    };
  };
  audit: {
    verification_status: string;
    human_count: number;
    pipeline_version: string;
  };
}

// =============================================================================
// 7. Workers AI & Edge Ingestion Types
// =============================================================================

export interface EvaluationRequestPayload {
  incident_id?: string;
  camera_id: string;
  location_name: string;
  latitude: number;
  longitude: number;
  timestamp: string;
  frame_index: number;
  engine_behavior: string;
  engine_category: string;
  engine_threat_level: string;
  engine_threat_score: number;
  primary_subject_id: number;
  interacting_subject_ids?: number[];
  telemetry: {
    spine_angle_deg: number;
    aspect_ratio: number;
    velocity_norm: number;
    wrist_kinetic_energy: number;
    dwell_time_seconds: number;
    state_dwell_seconds: number;
    bounding_box: [number, number, number, number];
  };
  evidence_clip_url?: string;
  snapshot_url?: string;
  diagnostic_reasoning: string;
}

export interface SubjectFeatures {
  posture_assessment: string;
  suspicious_concealment: boolean;
  movement_intent: string;
  estimated_threat_actor_count: number;
}

export interface WeaponsIdentified {
  has_weapon_indicator: boolean;
  weapon_type: "NONE" | "BLUNT_OBJECT" | "EDGED_WEAPON" | "CONCEALED_FIREARM" | "IMPROVISED_WEAPON";
  weapon_confidence: number;
  description: string;
}

export interface VictimAssessment {
  has_victim_present: boolean;
  victim_track_id?: number;
  victim_condition: "NONE" | "UNDER_ATTACK" | "FALLEN_UNRESPONSIVE" | "FLEEING_INJURED";
  bystander_count: number;
}

export interface DispatchRecommendation {
  priority: "ROUTINE" | "URGENT" | "IMMEDIATE_RESPONSE" | "DISMISS";
  recommended_units: ("POLICE" | "AMBULANCE" | "FIRE_RESCUE" | "SECURITY_GUARD")[];
  action_notes: string;
}

export interface AIEvaluationOutput {
  severity_score_10: number;
  false_positive_probability: number;
  is_false_positive: boolean;
  threat_verdict: "CONFIRMED_THREAT" | "BENIGN_ACTIVITY" | "SUSPICIOUS_MONITOR" | "CRITICAL_EMERGENCY";
  subject_features: SubjectFeatures;
  weapons_identified: WeaponsIdentified;
  victim_assessment: VictimAssessment;
  dispatch_recommendation: DispatchRecommendation;
  investigation_summary: string;
}

export interface IncidentRecord {
  id: string;
  timestamp: string;
  camera_id: string;
  location_name: string;
  latitude: number;
  longitude: number;
  engine_behavior: string;
  engine_threat_score: number;
  ai_severity_score_10: number;
  false_positive_prob: number;
  is_false_positive: number;
  threat_verdict: string;
  subject_features: string;
  weapons_identified: string;
  victim_assessment: string;
  dispatch_recommendation: string;
  investigation_summary: string;
  evidence_clip_url?: string | null;
  snapshot_url?: string | null;
  operator_status: "AWAITING_OPERATOR_VERIFICATION" | "OPERATOR_CONFIRMED" | "DISMISSED_FALSE_POSITIVE";
  operator_id?: string | null;
  verified_at?: string | null;
  operator_notes?: string | null;
  created_at?: string;
}

export interface OperatorVerifyRequest {
  action: "CONFIRM_AND_DISPATCH" | "DOWNGRADE_MONITOR" | "DISMISS_FALSE_POSITIVE";
  operator_id: string;
  operator_notes?: string;
}
