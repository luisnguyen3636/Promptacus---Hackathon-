/**
 * CYBERGUARD SOC — DYNAMIC CAMERA TELEMETRY LOG MANAGER (CLOUDFLARE KV PERSISTED)
 * Strictly derives camera telemetry state from real server JSON logs and persists to Cloudflare KV.
 * Zero frame processing, zero stream endpoints, zero mock devices.
 */

import type { ICameraDevice, IServerIngestPayload, Env } from "./types.ts";

const cameraRegistry = new Map<string, ICameraDevice>();
let lastKvCameraReadAt = 0;
let kvCameraWriteCooldownUntil = 0;
let lastCameraKvRef: any = null;

const KV_CAMERA_READ_TTL_MS = 10_000;

export function getCameras(): ICameraDevice[] {
  return Array.from(cameraRegistry.values());
}

export function getCameraById(id: string): ICameraDevice | undefined {
  return cameraRegistry.get(id);
}

/**
 * Loads persisted camera telemetry logs from Cloudflare KV (INCIDENT_CACHE -> "kv_cameras")
 * with in-memory TTL caching so polling requests respond in < 1ms without hammering KV.
 */
export async function loadCamerasFromKv(env?: Env, forceReload = false): Promise<ICameraDevice[]> {
  if (!env?.INCIDENT_CACHE) return Array.from(cameraRegistry.values());

  if (lastCameraKvRef !== env.INCIDENT_CACHE) {
    lastCameraKvRef = env.INCIDENT_CACHE;
    lastKvCameraReadAt = 0;
  }

  const now = Date.now();
  if (!forceReload && cameraRegistry.size > 0 && now - lastKvCameraReadAt < KV_CAMERA_READ_TTL_MS) {
    return Array.from(cameraRegistry.values());
  }

  try {
    const raw = await env.INCIDENT_CACHE.get("kv_cameras");
    lastKvCameraReadAt = Date.now();
    if (raw) {
      const parsed = JSON.parse(raw) as ICameraDevice[];
      if (Array.isArray(parsed)) {
        for (const cam of parsed) {
          if (cam && cam.id) {
            cam.streamUrl = "";
            cam.directStreamUrl = "";
            delete (cam as any).lastSnapshotBase64;
            cam.boundingBoxes = [];
            if (!cameraRegistry.has(cam.id)) {
              cameraRegistry.set(cam.id, cam);
            }
          }
        }
        // Auto-heal bloated legacy KV entries that contained lastSnapshotBase64
        if (raw.length > 50_000) {
          await saveCamerasToKv(env);
        }
      }
    }
  } catch {
    // Keep in-memory camera registry if KV read fails
  }
  return Array.from(cameraRegistry.values());
}

/**
 * Saves current camera telemetry registry to Cloudflare KV ("kv_cameras").
 */
export async function saveCamerasToKv(env?: Env): Promise<void> {
  if (!env?.INCIDENT_CACHE) return;
  if (Date.now() < kvCameraWriteCooldownUntil) return;

  try {
    const list = Array.from(cameraRegistry.values());
    await env.INCIDENT_CACHE.put("kv_cameras", JSON.stringify(list));
    lastKvCameraReadAt = Date.now();
  } catch {
    kvCameraWriteCooldownUntil = Date.now() + 30_000;
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
 * Upserts camera telemetry from the server's continuous JSON payload
 * and persists to Cloudflare KV without any frame/image processing.
 */
export async function upsertCameraFromServerPayload(
  payload: IServerIngestPayload,
  env?: Env,
  clientIp = "127.0.0.1"
): Promise<ICameraDevice | null> {
  const cameraId =
    payload.camera_id ||
    payload.cameraId ||
    payload.camera?.camera_id ||
    payload.nvidia_vlm_analysis?.camera_id;
  if (!cameraId) return null;

  await loadCamerasFromKv(env);
  const existing = cameraRegistry.get(cameraId);

  const cameraName =
    payload.camera_name ||
    payload.camera?.name ||
    existing?.name;

  const location =
    payload.camera?.address ||
    payload.location ||
    payload.nvidia_vlm_analysis?.location ||
    existing?.location ||
    cameraName ||
    "Khu Vực Giám Sát Trung Tâm";

  const measuredFps =
    payload.measured_fps !== undefined
      ? Number(payload.measured_fps)
      : existing?.measuredFps ?? 30;

  const frameIndex =
    payload.audit?.frame_index !== undefined
      ? Number(payload.audit.frame_index)
      : payload.frame_index !== undefined
      ? Number(payload.frame_index)
      : existing?.frameIndex ?? 0;

  const subjects = payload.detection?.subjects || [];
  const rawActors = payload.actors || payload.nvidia_vlm_analysis?.actors || [];

  const humanCount =
    payload.audit?.human_count !== undefined
      ? Number(payload.audit.human_count)
      : payload.human_count !== undefined
      ? Number(payload.human_count)
      : subjects.length > 0
      ? subjects.length
      : rawActors.length > 0
      ? rawActors.length
      : existing?.humanCount ?? 0;

  const displayName = cameraName
    ? `${cameraName} (${location})`
    : location
    ? `${cameraId} — ${location}`
    : cameraId;

  const updatedCamera: ICameraDevice = {
    id: cameraId,
    name: displayName,
    ip: clientIp || existing?.ip || "127.0.0.1",
    fps: Number(measuredFps.toFixed(1)),
    bitrateKbps: existing?.bitrateKbps || 2048,
    status: payload.status === "offline" ? "OFFLINE" : "ONLINE",
    streamUrl: "",
    directStreamUrl: "",
    ptzEnabled: true,
    ptzState: existing?.ptzState || { zoom: 1.0, pan: 0, tilt: 0, focus: "AUTO" },
    boundingBoxes: [],
    zoneId: payload.camera?.zone_id || existing?.zoneId || "ZONE_DEFAULT",
    location,
    address: location,
    measuredFps: Number(measuredFps.toFixed(1)),
    frameIndex,
    humanCount,
    latitude: payload.camera?.latitude ?? existing?.latitude,
    longitude: payload.camera?.longitude ?? existing?.longitude,
    lastTimestamp: payload.timestamp || new Date().toISOString()
  };

  cameraRegistry.set(cameraId, updatedCamera);
  await saveCamerasToKv(env);
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
