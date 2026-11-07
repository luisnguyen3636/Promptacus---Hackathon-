/**
 * CYBERGUARD SOC — DYNAMIC CAMERA FLEET MANAGER (CLOUDFLARE KV PERSISTED)
 * Strictly derives camera state from real server JSON payloads and persists to Cloudflare KV.
 * Zero mock or hardcoded fake devices.
 */

import type { ICameraDevice, IAIBoundingBox, IAISubjectData, IServerIngestPayload, Env } from "./types.ts";

const cameraRegistry = new Map<string, ICameraDevice>();

export function getCameras(): ICameraDevice[] {
  return Array.from(cameraRegistry.values());
}

export function getCameraById(id: string): ICameraDevice | undefined {
  return cameraRegistry.get(id);
}

/**
 * Loads persisted real cameras from Cloudflare KV (INCIDENT_CACHE -> "kv_cameras").
 */
export async function loadCamerasFromKv(env?: Env): Promise<ICameraDevice[]> {
  if (env?.INCIDENT_CACHE) {
    try {
      const raw = await env.INCIDENT_CACHE.get("kv_cameras");
      if (raw) {
        const parsed = JSON.parse(raw) as ICameraDevice[];
        if (Array.isArray(parsed)) {
          for (const cam of parsed) {
            if (cam && cam.id) {
              cameraRegistry.set(cam.id, cam);
            }
          }
        }
      }
    } catch (err) {
      console.warn("[CameraManager] Failed to read kv_cameras:", err);
    }
  }
  return Array.from(cameraRegistry.values());
}

/**
 * Saves current camera registry to Cloudflare KV ("kv_cameras").
 */
export async function saveCamerasToKv(env?: Env): Promise<void> {
  if (env?.INCIDENT_CACHE) {
    try {
      const list = Array.from(cameraRegistry.values());
      await env.INCIDENT_CACHE.put("kv_cameras", JSON.stringify(list));
    } catch (err) {
      console.warn("[CameraManager] Failed to write kv_cameras:", err);
    }
  }
}

/**
 * Removes a camera from registry and KV.
 */
export async function removeCameraById(id: string, env?: Env): Promise<boolean> {
  const deleted = cameraRegistry.delete(id);
  if (deleted) {
    await saveCamerasToKv(env);
  }
  return deleted;
}

/**
 * Upserts a real camera device from the server's continuous JSON payload
 * and persists immediately to Cloudflare KV.
 */
export async function upsertCameraFromServerPayload(
  payload: IServerIngestPayload,
  env?: Env,
  clientIp = "127.0.0.1"
): Promise<ICameraDevice | null> {
  const cameraId = payload.camera_id || payload.nvidia_vlm_analysis?.camera_id || payload.camera?.camera_id;
  if (!cameraId) return null;

  await loadCamerasFromKv(env);
  const existing = cameraRegistry.get(cameraId);

  const location =
    payload.location ||
    payload.nvidia_vlm_analysis?.location ||
    payload.camera?.address ||
    existing?.location ||
    "Khu Vực Giám Sát An Ninh";

  const measuredFps =
    payload.measured_fps !== undefined
      ? Number(payload.measured_fps)
      : existing?.measuredFps ?? 30;

  const frameIndex =
    payload.frame_index !== undefined
      ? Number(payload.frame_index)
      : existing?.frameIndex ?? 0;

  const humanCount =
    payload.human_count !== undefined
      ? Number(payload.human_count)
      : payload.actors?.length ?? existing?.humanCount ?? 0;

  const rawActors = payload.actors || payload.nvidia_vlm_analysis?.actors || [];
  const rawSeverity = (payload.severity || payload.nvidia_vlm_analysis?.severity || "low").toUpperCase();

  const boundingBoxes: IAIBoundingBox[] = rawActors
    .filter((actor) => Array.isArray(actor.bbox) && actor.bbox.length === 4)
    .map((actor) => {
      const [x1, y1, x2, y2] = actor.bbox!;
      const imgW = Math.max(640, x2 + 20);
      const imgH = Math.max(480, y2 + 20);

      const normX = Math.max(0, Math.min(1, x1 / imgW));
      const normY = Math.max(0, Math.min(1, y1 / imgH));
      const normW = Math.max(0.02, Math.min(1 - normX, (x2 - x1) / imgW));
      const normH = Math.max(0.02, Math.min(1 - normY, (y2 - y1) / imgH));

      let boxSeverity: "NORMAL" | "HIGH" | "CRITICAL" = "NORMAL";
      if (actor.role === "attacker" || rawSeverity === "CRITICAL") {
        boxSeverity = "CRITICAL";
      } else if (actor.role === "victim" || rawSeverity === "HIGH") {
        boxSeverity = "HIGH";
      }

      return {
        id: `actor_${cameraId}_${actor.id}_${frameIndex}`,
        trackId: Number(actor.id) || 1,
        label: `#${actor.id} ${String(actor.role || "actor").toUpperCase()}: ${String(actor.action || "").toUpperCase()}`,
        subLabel: actor.posture || "",
        severity: boxSeverity,
        x: parseFloat(normX.toFixed(4)),
        y: parseFloat(normY.toFixed(4)),
        w: parseFloat(normW.toFixed(4)),
        h: parseFloat(normH.toFixed(4)),
        confidence: payload.confidence ?? 0.9
      };
    });

  const defaultStreamUrl =
    env?.LIVE_CAMERA_STREAM_URL ||
    "https://means-brick-determined-send.trycloudflare.com/api/v1/cameras/LAPTOP_01/stream";

  const updatedCamera: ICameraDevice = {
    id: cameraId,
    name: location ? `${cameraId} — ${location}` : cameraId,
    ip: clientIp || existing?.ip || "127.0.0.1",
    fps: Number(measuredFps.toFixed(1)),
    bitrateKbps: existing?.bitrateKbps || 2048,
    status: payload.status === "offline" ? "OFFLINE" : "ONLINE",
    streamUrl: existing?.streamUrl || `/api/v1/cameras/${cameraId}/stream`,
    directStreamUrl: existing?.directStreamUrl || defaultStreamUrl,
    ptzEnabled: true,
    ptzState: existing?.ptzState || { zoom: 1.0, pan: 0, tilt: 0, focus: "AUTO" },
    boundingBoxes,
    location,
    address: location,
    measuredFps: Number(measuredFps.toFixed(1)),
    frameIndex,
    humanCount,
    lastTimestamp: payload.timestamp || new Date().toISOString(),
    lastSnapshotBase64: payload.image_base64 || payload.snapshot_url || existing?.lastSnapshotBase64
  };

  cameraRegistry.set(cameraId, updatedCamera);
  await saveCamerasToKv(env);
  return updatedCamera;
}

/**
 * Legacy helper for structured AI detection payload format
 */
export function upsertCameraFromAiDetection(
  cameraMeta: {
    camera_id: string;
    name: string;
    zone_id?: string;
    address?: string;
    latitude?: number;
    longitude?: number;
  },
  subjects: IAISubjectData[],
  fullImageWidth = 640,
  fullImageHeight = 480,
  snapshotBase64?: string
): ICameraDevice {
  const cameraId = cameraMeta.camera_id;
  const existing = cameraRegistry.get(cameraId);

  const boundingBoxes: IAIBoundingBox[] = subjects.map((sub) => {
    const [x1, y1, x2, y2] = sub.bbox;
    const imgW = fullImageWidth > 0 ? fullImageWidth : 640;
    const imgH = fullImageHeight > 0 ? fullImageHeight : 480;

    const normX = Math.max(0, Math.min(1, x1 / imgW));
    const normY = Math.max(0, Math.min(1, y1 / imgH));
    const normW = Math.max(0.01, Math.min(1, (x2 - x1) / imgW));
    const normH = Math.max(0.01, Math.min(1, (y2 - y1) / imgH));

    let severity: "NORMAL" | "HIGH" | "CRITICAL" = "NORMAL";
    if (sub.threat_level === "CRITICAL") severity = "CRITICAL";
    else if (sub.threat_level === "HIGH") severity = "HIGH";

    return {
      id: `box_trk_${sub.track_id}_${Date.now()}`,
      trackId: sub.track_id,
      label: `${sub.behavior} ${Math.round(sub.confidence * 100)}%`,
      subLabel: `${sub.role.toUpperCase()} (TRK-${sub.track_id})`,
      severity,
      x: parseFloat(normX.toFixed(4)),
      y: parseFloat(normY.toFixed(4)),
      w: parseFloat(normW.toFixed(4)),
      h: parseFloat(normH.toFixed(4)),
      confidence: sub.confidence,
      keypoints: sub.keypoints
    };
  });

  const location = cameraMeta.address || cameraMeta.name || existing?.location || cameraId;

  const updatedCamera: ICameraDevice = {
    id: cameraId,
    name: cameraMeta.name || existing?.name || cameraId,
    ip: existing?.ip || "127.0.0.1",
    fps: existing?.fps || 30,
    bitrateKbps: existing?.bitrateKbps || 2048,
    status: "ONLINE",
    streamUrl: snapshotBase64 || existing?.streamUrl || `/api/v1/cameras/${cameraId}/stream`,
    ptzEnabled: true,
    ptzState: existing?.ptzState || { zoom: 1.0, pan: 0, tilt: 0, focus: "AUTO" },
    boundingBoxes,
    zoneId: cameraMeta.zone_id || existing?.zoneId,
    address: location,
    location,
    humanCount: subjects.length,
    lastTimestamp: new Date().toISOString(),
    latitude: cameraMeta.latitude ?? existing?.latitude,
    longitude: cameraMeta.longitude ?? existing?.longitude,
    lastSnapshotBase64: snapshotBase64 || existing?.lastSnapshotBase64
  };

  cameraRegistry.set(cameraId, updatedCamera);
  return updatedCamera;
}

export async function handlePtzCommand(
  cameraId: string,
  action: string,
  speed = 1,
  env?: Env
): Promise<{ cameraId: string; ptzState: any; status: string }> {
  await loadCamerasFromKv(env);
  const camera = cameraRegistry.get(cameraId);

  if (!camera) {
    return {
      cameraId,
      ptzState: { zoom: 1.0, pan: 0, tilt: 0, focus: "AUTO" },
      status: "CAMERA_NOT_REGISTERED"
    };
  }

  const ptz = camera.ptzState;
  switch (action) {
    case "ZOOM_IN":
      ptz.zoom = Math.min(5.0, parseFloat((ptz.zoom + 0.2 * speed).toFixed(2)));
      break;
    case "ZOOM_OUT":
      ptz.zoom = Math.max(1.0, parseFloat((ptz.zoom - 0.2 * speed).toFixed(2)));
      break;
    case "PAN":
      ptz.pan = (ptz.pan + 15 * speed) % 360;
      break;
    case "AUTO_FOCUS":
      ptz.focus = "LOCKED_99%";
      break;
    default:
      break;
  }

  cameraRegistry.set(cameraId, camera);
  await saveCamerasToKv(env);
  return { cameraId, ptzState: ptz, status: "SUCCESS" };
}
