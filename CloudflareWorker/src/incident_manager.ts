/**
 * CYBERGUARD SOC — REAL INCIDENT & CLOUDFLARE KV STORAGE MANAGER
 * Receives JSON payloads pushed by the external server and stores them directly in Cloudflare KV.
 * Zero AI re-evaluation on Worker, zero mock data, strict Operational HITL [CD-04].
 */

import type {
  IIncidentItem,
  IIncidentPlaybackResponse,
  IServerIngestPayload,
  IServerActor,
  IServerVisualCues,
  Env
} from "./types.ts";

let incidents: IIncidentItem[] = [];
let kvWriteCooldownUntil = 0;

export function getRecentIncidents(): IIncidentItem[] {
  return incidents;
}

export function setRecentIncidents(newIncidents: IIncidentItem[]): void {
  incidents = newIncidents;
}

export function getIncidentById(id: string): IIncidentItem | undefined {
  return incidents.find((i) => i.id === id || i.eventId === id);
}

export function addIncident(item: IIncidentItem): void {
  incidents = [item, ...incidents.filter((i) => i.id !== item.id)].slice(0, 60);
}

/**
 * Loads stored incidents from Cloudflare KV ("kv_recent_incidents") and merges with in-memory state
 * so newer in-memory incidents are never overwritten if KV writes are rate-limited (429 / quota).
 */
export async function loadIncidentsFromKv(env?: Env): Promise<IIncidentItem[]> {
  if (env?.INCIDENT_CACHE) {
    try {
      const raw = await env.INCIDENT_CACHE.get("kv_recent_incidents");
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed)) {
          if (incidents.length === 0) {
            incidents = parsed;
          } else {
            // Merge: keep in-memory items first (freshest state / status updates), append missing KV items
            const seenIds = new Set(incidents.map((i) => i.id));
            for (const kvItem of parsed) {
              if (kvItem && kvItem.id && !seenIds.has(kvItem.id)) {
                incidents.push(kvItem);
                seenIds.add(kvItem.id);
              }
            }
            incidents = incidents.slice(0, 60);
          }
        }
      }
    } catch {
      // Silently keep in-memory incidents if KV read fails
    }
  }
  return incidents;
}

/**
 * Compacts incidents before writing to Cloudflare KV to prevent 25MB limit / oversized payload errors
 * and 6x Base64 duplication. Keeps Base64 snapshots on the 3 most recent incidents in KV.
 */
function buildCompactKvIncidents(list: IIncidentItem[]): IIncidentItem[] {
  return list.slice(0, 25).map((item, idx) => {
    const keepHeavyImages = idx < 3;
    return {
      ...item,
      fullImageBase64: keepHeavyImages ? item.fullImageBase64 : undefined,
      subjectCropBase64: keepHeavyImages ? item.subjectCropBase64 : undefined,
      handCropBase64: keepHeavyImages ? item.handCropBase64 : undefined,
      playbackUrl: keepHeavyImages ? item.playbackUrl : null,
      cameraSnapshots: keepHeavyImages ? item.cameraSnapshots : null
    };
  });
}

/**
 * Saves current incident list to Cloudflare KV ("kv_recent_incidents") with rate-limit cooldown protection.
 */
export async function saveIncidentsToKv(env?: Env, _singleIncident?: IIncidentItem): Promise<void> {
  if (!env?.INCIDENT_CACHE) return;
  if (Date.now() < kvWriteCooldownUntil) return;

  try {
    const compactList = buildCompactKvIncidents(incidents);
    await env.INCIDENT_CACHE.put("kv_recent_incidents", JSON.stringify(compactList));
  } catch {
    // Cloudflare KV enforces 1 write/sec per key and daily write limits on Free Tier.
    // Activate a 30s cooldown so continuous server ingestion stays fast in-memory + WebSocket + D1 without error spam.
    kvWriteCooldownUntil = Date.now() + 30_000;
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
 * Unified Server JSON Ingestion -> Cloudflare KV
 * Supports the full WEAPON_THREAT / YOLOv11-Pose + NVIDIA NIM VLM payload as well as actor/visual_cues payloads.
 */
export async function ingestServerPayloadToKv(
  payload: IServerIngestPayload,
  env?: Env,
  clientIp = "127.0.0.1"
): Promise<IIncidentItem> {
  await loadIncidentsFromKv(env);

  const vlm = payload.nvidia_vlm_analysis;
  const det = payload.detection;
  const val = payload.action_validation;
  const camMeta = payload.camera;
  const audit = payload.audit;

  const cameraId =
    payload.camera_id ||
    payload.cameraId ||
    camMeta?.camera_id ||
    vlm?.camera_id ||
    "LAPTOP_01";

  const cameraName =
    payload.camera_name ||
    camMeta?.name ||
    cameraId;

  const location =
    camMeta?.address ||
    payload.location ||
    vlm?.location ||
    payload.location_name ||
    cameraName ||
    "Khu vực Giám sát Trung tâm";

  const timestamp = payload.timestamp || vlm?.timestamp || new Date().toISOString();
  const timestampMs =
    payload.timestamp_ms !== undefined
      ? Number(payload.timestamp_ms)
      : Date.parse(timestamp) || Date.now();

  const frameIndex =
    audit?.frame_index !== undefined
      ? Number(audit.frame_index)
      : payload.frame_index !== undefined
      ? Number(payload.frame_index)
      : undefined;

  const measuredFps =
    payload.measured_fps !== undefined ? Number(payload.measured_fps) : undefined;

  const subjects = det?.subjects || [];
  const rawActors = payload.actors || vlm?.actors || [];

  const humanCount =
    audit?.human_count !== undefined
      ? Number(audit.human_count)
      : payload.human_count !== undefined
      ? Number(payload.human_count)
      : subjects.length > 0
      ? subjects.length
      : rawActors.length;

  const primaryAction =
    payload.primary_action ||
    det?.primary_action ||
    val?.detected_action ||
    payload.action_type ||
    vlm?.action_type ||
    "OBSERVED_EVENT";

  const severity = normalizeSeverity(
    payload.severity ||
      payload.threat_level ||
      det?.threat_level ||
      val?.severity ||
      vlm?.severity
  );

  const threatScoreRaw =
    payload.threat_score !== undefined
      ? Number(payload.threat_score)
      : det?.threat_score !== undefined
      ? Number(det.threat_score)
      : val?.threat_score !== undefined
      ? Number(val.threat_score)
      : vlm?.threat_score !== undefined
      ? Number(vlm.threat_score)
      : severity === "CRITICAL"
      ? 0.95
      : severity === "HIGH"
      ? 0.78
      : 0.35;

  const weaponInfo = payload.weapon_info || det?.weapon
    ? {
        is_weapon_detected: Boolean(
          payload.weapon_info?.is_weapon_detected ?? det?.weapon?.is_weapon_detected
        ),
        weapon_types:
          payload.weapon_info?.weapon_types ||
          det?.weapon?.weapon_types ||
          [],
        confidence:
          payload.weapon_info?.confidence ??
          det?.weapon?.confidence ??
          0.95,
        description:
          payload.weapon_info?.description ||
          det?.weapon?.description ||
          ""
      }
    : undefined;

  const confidence =
    payload.confidence !== undefined
      ? Number(payload.confidence)
      : weaponInfo?.confidence !== undefined
      ? Number(weaponInfo.confidence)
      : subjects[0]?.confidence !== undefined
      ? Number(subjects[0].confidence)
      : vlm?.confidence !== undefined
      ? Number(vlm.confidence)
      : 0.95;

  const isUrgent =
    payload.is_urgent !== undefined
      ? Boolean(payload.is_urgent)
      : det?.is_urgent !== undefined
      ? Boolean(det.is_urgent)
      : vlm?.is_urgent !== undefined
      ? Boolean(vlm.is_urgent)
      : severity === "CRITICAL";

  const actionConfirmed = Boolean(
    payload.action_confirmed ?? det?.action_confirmed ?? audit?.action_confirmed ?? val?.is_valid
  );
  const aiVerified = Boolean(
    payload.ai_verified ?? det?.ai_verified ?? audit?.ai_verified ?? val?.is_valid
  );

  const valReasoning = val?.reasoning;
  const rawReasoning = payload.reasoning || det?.reasoning || vlm?.reasoning;

  const description =
    payload.description ||
    valReasoning ||
    weaponInfo?.description ||
    vlm?.description ||
    rawReasoning ||
    `Phát hiện hành vi ${primaryAction} tại ${location}`;

  const reasoning = rawReasoning || valReasoning || description;
  const vlmAnalysis =
    payload.vlmAnalysis ||
    (valReasoning && rawReasoning && valReasoning !== rawReasoning
      ? `${valReasoning} | ${rawReasoning}`
      : valReasoning || rawReasoning || description);

  const title =
    payload.title ||
    `Cảnh báo: ${primaryAction} (${severity})`;

  const recommendedAction =
    payload.recommended_action ||
    vlm?.recommended_action ||
    (isUrgent ? "DISPATCH_SECURITY" : "MONITOR");

  // Synthesize actors from detection.subjects if actors is not explicitly provided
  const actors: IServerActor[] =
    rawActors.length > 0
      ? rawActors.map((a, idx) => ({
          id: a?.id ?? idx + 1,
          role: String(a?.role || "suspect"),
          action: String(a?.action || primaryAction),
          posture: String(a?.posture || weaponInfo?.description || ""),
          interacting_with: a?.interacting_with ?? null,
          bbox: Array.isArray(a?.bbox) ? a.bbox : undefined
        }))
      : subjects.map((sub, idx) => {
          const kin = sub?.kinematics;
          const postureStr = kin
            ? `Spine: ${kin.spine_angle ?? 0}°, L-Elbow: ${kin.left_elbow_angle ?? 0}°, R-Elbow: ${kin.right_elbow_angle ?? 0}°, L-ArmExt: ${kin.left_arm_extension ?? 0}, R-ArmExt: ${kin.right_arm_extension ?? 0} (Speed: ${sub?.speed ?? 0})`
            : weaponInfo?.description || `Behavior: ${sub?.behavior || primaryAction}`;
          return {
            id: sub?.track_id ?? idx + 1,
            role: String(sub?.role || "suspect"),
            action: String(sub?.behavior || primaryAction),
            posture: String(postureStr),
            bbox: Array.isArray(sub?.bbox) ? sub.bbox : undefined
          };
        });

  const visualCues: IServerVisualCues = payload.visual_cues || vlm?.visual_cues || {
    weapons_visible: Boolean(
      weaponInfo?.is_weapon_detected ||
        primaryAction.includes("WEAPON") ||
        (weaponInfo?.weapon_types && weaponInfo.weapon_types.length > 0)
    ),
    physical_contact: Boolean(
      primaryAction.includes("FIGHT") || primaryAction.includes("ASSAULT")
    ),
    fallen_person: Boolean(primaryAction.includes("FALL"))
  };

  const incidentId =
    payload.event_id ||
    payload.incident_id ||
    payload.id ||
    `EVT_${cameraId}_${frameIndex !== undefined ? frameIndex : Date.now()}_${Date.now().toString().slice(-4)}`;

  const cleanImg = (val?: string | null): string | undefined => {
    if (!val || typeof val !== "string") return undefined;
    if (val.includes("...")) return undefined;
    return val;
  };

  const fullImageBase64 = cleanImg(
    payload.image_base64 ||
      payload.image ||
      det?.full_image?.image_base64 ||
      payload.snapshot_url ||
      payload.evidence_url
  );

  const subjectCropBase64 = cleanImg(
    payload.subject_crop_base64 || subjects[0]?.crop_image_base64
  );

  const handCropBase64 = cleanImg(payload.hand_crop_base64);

  const forensicSha256 =
    payload.forensic_hash ||
    det?.full_image?.sha256_hash ||
    subjects[0]?.crop_image_sha256 ||
    undefined;

  const imageUrl = payload.image_url || (fullImageBase64 ? `/api/v1/incidents/${incidentId}/image.jpg` : undefined);
  const handCropUrl = payload.hand_crop_url || (handCropBase64 ? `/api/v1/incidents/${incidentId}/hand_crop.jpg` : undefined);

  const peakSnapshot = fullImageBase64;
  const preSnapshot = subjectCropBase64 || handCropBase64 || peakSnapshot;

  // Strip duplicate large Base64 blobs from rawDetection so KV values stay compact
  const {
    image: _img,
    image_base64: _imgB64,
    subject_crop_base64: _subB64,
    hand_crop_base64: _handB64,
    snapshot_url: _snapUrl,
    evidence_url: _evUrl,
    ...lightPayload
  } = payload;

  const lightSubjects = subjects.map((s) => {
    const { crop_image_base64: _cropB64, ...restSubject } = s;
    return restSubject;
  });

  const incident: IIncidentItem = {
    id: incidentId,
    eventId: incidentId,
    title,
    subTitle: `${cameraName} • ${location}`,
    sourceIp: clientIp || cameraId,
    category: "PHYSICAL_CAMERA",
    severity,
    timestamp,
    timestampMs,
    cameraId,
    cameraName,
    location,
    measuredFps,
    frameIndex,
    humanCount,
    actionType: primaryAction,
    primaryAction,
    threatLevel: normalizeSeverity(payload.threat_level || det?.threat_level || severity),
    threatScore: threatScoreRaw,
    confidence,
    isUrgent,
    actionConfirmed,
    aiVerified,
    actionValidation: val,
    weaponInfo,
    description,
    reasoning,
    recommendedAction,
    actors,
    visualCues,
    nvidiaVlmAnalysis: vlm,
    cameraSnapshots:
      peakSnapshot || preSnapshot || handCropBase64
        ? {
            preEventSnapshotUrl: preSnapshot,
            eventPeakSnapshotUrl: peakSnapshot,
            handCropSnapshotUrl: handCropBase64 || handCropUrl
          }
        : null,
    playbackUrl: peakSnapshot || null,
    status: "PENDING_VERIFICATION", // Mandatory Operational HITL gate [CD-04]
    vlmAnalysis,
    rawDetection: lightPayload,
    forensicSha256,
    subjects: lightSubjects,
    fullImageBase64,
    subjectCropBase64,
    handCropBase64,
    imageUrl,
    handCropUrl,
    cameraMeta: camMeta || {
      camera_id: cameraId,
      name: cameraName,
      zone_id: "ZONE_DEFAULT",
      address: location
    },
    auditInfo: audit,
    audioInfo: det?.audio
  };

  addIncident(incident);
  await saveIncidentsToKv(env, incident);
  return incident;
}

export function getIncidentPlayback(id: string): IIncidentPlaybackResponse | null {
  const inc = incidents.find((i) => i.id === id || i.eventId === id);
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
    vlmReasoning: inc.vlmAnalysis || inc.reasoning,
    visualEvidence: {
      preEventSnapshot: inc.subjectCropBase64 || inc.cameraSnapshots?.preEventSnapshotUrl || null,
      eventPeakSnapshot: inc.fullImageBase64 || inc.cameraSnapshots?.eventPeakSnapshotUrl || null,
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
  const inc = incidents.find((i) => i.id === id || i.eventId === id);
  if (inc) {
    inc.status = newStatus;
    await saveIncidentsToKv(env, inc);
  }
  return inc || null;
}
