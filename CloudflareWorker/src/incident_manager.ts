/**
 * CYBERGUARD SOC — REAL INCIDENT & CLOUDFLARE KV STORAGE MANAGER
 * Receives JSON payloads pushed by the external server and stores them directly in Cloudflare KV.
 * Zero AI re-evaluation on Worker, zero mock data, strict Operational HITL [CD-04].
 */

import type {
  IIncidentItem,
  IIncidentPlaybackResponse,
  IAIRealDetectionPayload,
  IServerIngestPayload,
  Env
} from "./types.ts";

let incidents: IIncidentItem[] = [];

export function getRecentIncidents(): IIncidentItem[] {
  return incidents;
}

export function setRecentIncidents(newIncidents: IIncidentItem[]): void {
  incidents = newIncidents;
}

export function addIncident(item: IIncidentItem): void {
  incidents = [item, ...incidents.filter((i) => i.id !== item.id)].slice(0, 100);
}

/**
 * Loads stored incidents from Cloudflare KV ("kv_recent_incidents").
 */
export async function loadIncidentsFromKv(env?: Env): Promise<IIncidentItem[]> {
  if (env?.INCIDENT_CACHE) {
    try {
      const raw = await env.INCIDENT_CACHE.get("kv_recent_incidents");
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed)) {
          incidents = parsed;
        }
      }
    } catch (err) {
      console.warn("[IncidentManager] Failed to read kv_recent_incidents:", err);
    }
  }
  return incidents;
}

/**
 * Saves current incident list to Cloudflare KV ("kv_recent_incidents").
 */
export async function saveIncidentsToKv(env?: Env, singleIncident?: IIncidentItem): Promise<void> {
  if (env?.INCIDENT_CACHE) {
    try {
      await env.INCIDENT_CACHE.put("kv_recent_incidents", JSON.stringify(incidents));
      if (singleIncident) {
        await env.INCIDENT_CACHE.put(`incident:${singleIncident.id}`, JSON.stringify(singleIncident));
      }
    } catch (err) {
      console.warn("[IncidentManager] Failed to write kv_recent_incidents:", err);
    }
  }
}

/**
 * Normalizes severity string ("critical", "high", "medium", "low") to standard uppercase enum.
 */
function normalizeSeverity(raw?: string): "LOW" | "MEDIUM" | "HIGH" | "CRITICAL" {
  const upper = String(raw || "MEDIUM").toUpperCase();
  if (upper === "CRITICAL") return "CRITICAL";
  if (upper === "HIGH") return "HIGH";
  if (upper === "LOW") return "LOW";
  return "MEDIUM";
}

/**
 * Ingests the server's continuous JSON payload directly into memory and Cloudflare KV.
 */
export async function ingestServerPayloadToKv(
  payload: IServerIngestPayload,
  env?: Env,
  clientIp = "127.0.0.1"
): Promise<IIncidentItem> {
  await loadIncidentsFromKv(env);

  if (payload.detection && payload.camera) {
    const legacyItem = createIncidentFromAiDetection(payload as IAIRealDetectionPayload);
    await saveIncidentsToKv(env, legacyItem);
    return legacyItem;
  }

  const vlm = payload.nvidia_vlm_analysis;
  const cameraId = payload.camera_id || vlm?.camera_id || "LAPTOP_01";
  const location =
    payload.location ||
    vlm?.location ||
    payload.location_name ||
    "Cổng Phía Đông - Khu Vực Giám Sát An Ninh";
  const timestamp = payload.timestamp || vlm?.timestamp || new Date().toISOString();
  const frameIndex = payload.frame_index !== undefined ? Number(payload.frame_index) : undefined;
  const measuredFps = payload.measured_fps !== undefined ? Number(payload.measured_fps) : undefined;
  const humanCount =
    payload.human_count !== undefined
      ? Number(payload.human_count)
      : (payload.actors || vlm?.actors || []).length;

  const actionType =
    payload.action_type ||
    vlm?.action_type ||
    payload.title ||
    "OBSERVED_EVENT";

  const severity = normalizeSeverity(payload.severity || vlm?.severity);

  const threatScoreRaw =
    payload.threat_score !== undefined
      ? Number(payload.threat_score)
      : vlm?.threat_score !== undefined
      ? Number(vlm.threat_score)
      : severity === "CRITICAL"
      ? 0.94
      : severity === "HIGH"
      ? 0.78
      : 0.35;

  const confidence =
    payload.confidence !== undefined
      ? Number(payload.confidence)
      : vlm?.confidence !== undefined
      ? Number(vlm.confidence)
      : 0.9;

  const isUrgent =
    payload.is_urgent !== undefined
      ? Boolean(payload.is_urgent)
      : vlm?.is_urgent !== undefined
      ? Boolean(vlm.is_urgent)
      : severity === "CRITICAL";

  const description =
    payload.description ||
    vlm?.description ||
    `Phát hiện hành vi ${actionType} tại ${location}`;

  const reasoning =
    payload.reasoning ||
    vlm?.reasoning ||
    description;

  const recommendedAction =
    payload.recommended_action ||
    vlm?.recommended_action ||
    (isUrgent ? "DISPATCH_SECURITY" : "MONITOR");

  const actors = payload.actors || vlm?.actors || [];
  const visualCues = payload.visual_cues || vlm?.visual_cues || {
    weapons_visible: false,
    physical_contact: false,
    fallen_person: false
  };

  const incidentId =
    payload.event_id ||
    payload.incident_id ||
    payload.id ||
    `EVT_${cameraId}_${frameIndex !== undefined ? frameIndex : Date.now()}_${Date.now().toString().slice(-4)}`;

  const snapshot = payload.snapshot_url || payload.image_base64 || payload.evidence_url || undefined;

  const incident: IIncidentItem = {
    id: incidentId,
    eventId: incidentId,
    title: `${actionType} — ${description}`,
    subTitle: location,
    sourceIp: clientIp || cameraId,
    category: "PHYSICAL_CAMERA",
    severity,
    timestamp,
    cameraId,
    location,
    measuredFps,
    frameIndex,
    humanCount,
    actionType,
    threatScore: threatScoreRaw,
    confidence,
    isUrgent,
    description,
    reasoning,
    recommendedAction,
    actors,
    visualCues,
    nvidiaVlmAnalysis: vlm,
    cameraSnapshots: snapshot
      ? {
          preEventSnapshotUrl: snapshot,
          eventPeakSnapshotUrl: snapshot
        }
      : null,
    playbackUrl: snapshot || null,
    status: "PENDING_VERIFICATION", // Mandatory Operational HITL gate [CD-04]
    vlmAnalysis: `${description} | Lý giải: ${reasoning}`,
    rawDetection: payload,
    fullImageBase64: snapshot
  };

  addIncident(incident);
  await saveIncidentsToKv(env, incident);
  return incident;
}

/**
 * Legacy helper for structured AI detection payload
 */
export function createIncidentFromAiDetection(payload: IAIRealDetectionPayload): IIncidentItem {
  const primarySubject = payload.detection.subjects?.[0];
  const timestamp = payload.timestamp || new Date().toISOString();

  const preSnapshot = primarySubject?.crop_image_base64 || payload.detection.full_image?.image_base64 || null;
  const peakSnapshot = payload.detection.full_image?.image_base64 || null;

  const incident: IIncidentItem = {
    id: payload.event_id,
    eventId: payload.event_id,
    title: payload.detection.primary_action.replace(/_/g, " "),
    subTitle: payload.camera.address || payload.camera.name || payload.camera.camera_id,
    sourceIp: payload.camera.camera_id,
    category: "PHYSICAL_CAMERA",
    severity: payload.detection.threat_level,
    timestamp,
    cameraId: payload.camera.camera_id,
    location: payload.camera.address || payload.camera.name,
    actionType: payload.detection.primary_action,
    threatScore: payload.detection.threat_score,
    confidence: primarySubject?.confidence || 0.9,
    isUrgent: payload.detection.is_urgent,
    description: payload.detection.reasoning,
    reasoning: payload.detection.reasoning,
    recommendedAction: payload.detection.is_urgent ? "DISPATCH_SECURITY" : "MONITOR",
    cameraSnapshots: {
      preEventSnapshotUrl: preSnapshot || undefined,
      eventPeakSnapshotUrl: peakSnapshot || undefined
    },
    playbackUrl: peakSnapshot,
    status: "PENDING_VERIFICATION",
    vlmAnalysis: payload.detection.reasoning,
    rawDetection: payload,
    forensicSha256: payload.detection.full_image?.sha256_hash,
    subjects: payload.detection.subjects,
    fullImageBase64: peakSnapshot || undefined
  };

  addIncident(incident);
  return incident;
}

export function getIncidentPlayback(id: string): IIncidentPlaybackResponse | null {
  const inc = incidents.find((i) => i.id === id);
  if (!inc) return null;

  return {
    incidentId: inc.id,
    title: inc.title,
    cameraId: inc.cameraId,
    timestamp: inc.timestamp,
    bufferRange: {
      preEventSeconds: 10,
      postEventSeconds: 10,
      totalDurationSeconds: 20
    },
    vlmReasoning: inc.reasoning || inc.vlmAnalysis,
    visualEvidence: {
      preEventSnapshot: inc.cameraSnapshots?.preEventSnapshotUrl || null,
      eventPeakSnapshot: inc.cameraSnapshots?.eventPeakSnapshotUrl || null,
      streamPlaybackUrl: inc.playbackUrl || null
    },
    status: inc.status,
    forensicSha256: inc.forensicSha256,
    fullImageBase64: inc.fullImageBase64,
    subjects: inc.subjects
  };
}

export async function updateIncidentStatus(
  id: string,
  newStatus: "PENDING_VERIFICATION" | "OPERATOR_CONFIRMED" | "DOWNGRADED_MONITORING" | "DISMISSED",
  env?: Env
): Promise<IIncidentItem | null> {
  await loadIncidentsFromKv(env);
  const inc = incidents.find((i) => i.id === id);
  if (inc) {
    inc.status = newStatus;
    await saveIncidentsToKv(env, inc);
  }
  return inc || null;
}

export function ingestGenericIncident(payload: Record<string, any>, clientIp?: string): IIncidentItem {
  if (payload.detection && payload.camera) {
    return createIncidentFromAiDetection(payload as IAIRealDetectionPayload);
  }

  const vlm = payload.nvidia_vlm_analysis;
  const cameraId = payload.camera_id || vlm?.camera_id || "LAPTOP_01";
  const location = payload.location || vlm?.location || payload.location_name || "Khu Vực Giám Sát";
  const actionType = payload.action_type || vlm?.action_type || payload.title || "OBSERVED_EVENT";
  const severity = normalizeSeverity(payload.severity || vlm?.severity);
  const description = payload.description || vlm?.description || actionType;
  const reasoning = payload.reasoning || vlm?.reasoning || description;
  const threatScore =
    payload.threat_score !== undefined
      ? Number(payload.threat_score)
      : vlm?.threat_score !== undefined
      ? Number(vlm.threat_score)
      : 0.5;

  const incidentId =
    payload.event_id ||
    payload.incident_id ||
    payload.id ||
    `EVT_${cameraId}_${payload.frame_index ?? Date.now()}`;

  const incident: IIncidentItem = {
    id: incidentId,
    eventId: incidentId,
    title: payload.action_type ? `${actionType} — ${description}` : description,
    subTitle: location,
    sourceIp: payload.source_ip || clientIp || cameraId,
    category: "PHYSICAL_CAMERA",
    severity,
    timestamp: payload.timestamp || new Date().toISOString(),
    cameraId,
    location,
    measuredFps: payload.measured_fps !== undefined ? Number(payload.measured_fps) : undefined,
    frameIndex: payload.frame_index !== undefined ? Number(payload.frame_index) : undefined,
    humanCount: payload.human_count !== undefined ? Number(payload.human_count) : undefined,
    actionType,
    threatScore,
    confidence: payload.confidence !== undefined ? Number(payload.confidence) : undefined,
    isUrgent: Boolean(payload.is_urgent ?? vlm?.is_urgent),
    description,
    reasoning,
    recommendedAction: payload.recommended_action || vlm?.recommended_action || "DISPATCH_SECURITY",
    actors: payload.actors || vlm?.actors || [],
    visualCues: payload.visual_cues || vlm?.visual_cues,
    nvidiaVlmAnalysis: vlm,
    cameraSnapshots: payload.evidence_url
      ? {
          eventPeakSnapshotUrl: payload.evidence_url,
          preEventSnapshotUrl: payload.evidence_url
        }
      : null,
    playbackUrl: payload.evidence_url || null,
    status: "PENDING_VERIFICATION",
    vlmAnalysis: `${description} | ${reasoning}`,
    rawDetection: payload
  };

  addIncident(incident);
  return incident;
}
