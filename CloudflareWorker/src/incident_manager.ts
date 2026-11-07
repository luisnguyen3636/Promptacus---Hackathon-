/**
 * CYBERGUARD AI · SOC v2.1 — REAL INCIDENT & EVIDENCE ROLLING BUFFER MANAGER (EDGE NATIVE)
 * Receives authentic AI detection events from the YOLO11 / Pose detection pipeline.
 * Zero mock data — fully dynamic incident vault with forensic audit support.
 */

import type { IIncidentItem, IIncidentPlaybackResponse, IAIRealDetectionPayload } from "./types.ts";

// In-Memory Buffer for Live Active Incidents (Synchronized with D1)
let incidents: IIncidentItem[] = [];

export function getRecentIncidents(): IIncidentItem[] {
  return incidents;
}

export function setRecentIncidents(newIncidents: IIncidentItem[]): void {
  incidents = newIncidents;
}

export function addIncident(item: IIncidentItem): void {
  // Deduplicate and insert at the top
  incidents = [item, ...incidents.filter((i) => i.id !== item.id)].slice(0, 50);
}

/**
 * Creates and indexes a new authentic incident item directly from an AI detection payload.
 */
export function createIncidentFromAiDetection(payload: IAIRealDetectionPayload): IIncidentItem {
  const primarySubject = payload.detection.subjects?.[0];
  const timeFormatted = payload.timestamp
    ? (payload.timestamp.includes("T") ? payload.timestamp.split("T")[1].substring(0, 5) : payload.timestamp)
    : new Date().toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });

  let weaponDesc = "";
  if (payload.detection.weapon?.is_weapon_detected) {
    weaponDesc = ` | Chỉ dấu vũ khí: ${payload.detection.weapon.weapon_types.join(", ")} (${Math.round(payload.detection.weapon.confidence * 100)}%) - ${payload.detection.weapon.description}`;
  }

  const vlmAnalysis = `AI Phân tích: ${payload.detection.reasoning}${weaponDesc}`;

  const preSnapshot = primarySubject?.crop_image_base64 || payload.detection.full_image?.image_base64 || null;
  const peakSnapshot = payload.detection.full_image?.image_base64 || null;

  const incident: IIncidentItem = {
    id: payload.event_id,
    title: payload.detection.primary_action.replace(/_/g, " "),
    subTitle: `PHYSICAL_CAMERA / ${payload.camera.address || payload.camera.name || payload.camera.camera_id}`,
    sourceIp: payload.camera.camera_id,
    category: "PHYSICAL_CAMERA",
    severity: payload.detection.threat_level,
    timestamp: timeFormatted,
    cameraId: payload.camera.camera_id,
    cameraSnapshots: {
      preEventSnapshotUrl: preSnapshot || undefined,
      eventPeakSnapshotUrl: peakSnapshot || undefined
    },
    playbackUrl: peakSnapshot,
    status: "PENDING_VERIFICATION", // Mandatory Operational HITL gate [CD-04]
    vlmAnalysis,
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
    vlmReasoning: inc.vlmAnalysis,
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

export function updateIncidentStatus(
  id: string,
  newStatus: "PENDING_VERIFICATION" | "OPERATOR_CONFIRMED" | "DOWNGRADED_MONITORING" | "DISMISSED"
): IIncidentItem | null {
  const inc = incidents.find((i) => i.id === id);
  if (inc) {
    inc.status = newStatus;
  }
  return inc || null;
}

/**
 * Ingests a generic incident payload or an AI detection payload, indexing it as a pending incident.
 * Mandatory HITL [CD-04]: Sets status to PENDING_VERIFICATION.
 */
export function ingestGenericIncident(payload: Record<string, any>, clientIp?: string): IIncidentItem {
  if (payload.detection && payload.camera) {
    return createIncidentFromAiDetection(payload as IAIRealDetectionPayload);
  }

  const incidentId =
    payload.incident_id ||
    payload.id ||
    `INC_${Date.now()}_${Math.random().toString(36).substring(2, 7).toUpperCase()}`;

  const rawSeverity = (payload.severity || "MEDIUM").toUpperCase();
  const severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL" =
    ["LOW", "MEDIUM", "HIGH", "CRITICAL"].includes(rawSeverity)
      ? (rawSeverity as any)
      : "MEDIUM";

  const title = payload.title || "Sự cố an ninh ghi nhận qua API";
  const location = payload.location_name || payload.zone_id || "Khu vực giám sát";
  const category = (payload.category as any) || "PHYSICAL_CAMERA";

  const incident: IIncidentItem = {
    id: incidentId,
    title,
    subTitle: `${category} / ${location}`,
    sourceIp: payload.source_ip || clientIp || "API_CLIENT",
    category,
    severity,
    timestamp: new Date().toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" }),
    cameraId: payload.camera_id || null,
    cameraSnapshots: payload.evidence_url
      ? {
          eventPeakSnapshotUrl: payload.evidence_url,
          preEventSnapshotUrl: payload.evidence_url
        }
      : null,
    playbackUrl: payload.evidence_url || null,
    status: "PENDING_VERIFICATION", // Mandatory HITL [CD-04]
    vlmAnalysis: payload.description || "Bản tin cảnh báo sự cố từ hệ thống ngoại vi",
    rawDetection: payload
  };

  addIncident(incident);
  return incident;
}
