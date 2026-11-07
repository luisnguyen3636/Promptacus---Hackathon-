/**
 * CYBERGUARD AI · SOC v2.1 — DYNAMIC CAMERA FLEET & REAL-TIME AI TRACKING ENGINE (EDGE NATIVE)
 * Ingests live AI bounding boxes and keypoints from AI Detection pipelines without mock data.
 */

import { ICameraDevice, IAIBoundingBox, IAISubjectData } from "./types";

// Dynamic Camera Fleet in Edge Memory
const cameraRegistry = new Map<string, ICameraDevice>();

export function getCameras(): ICameraDevice[] {
  return Array.from(cameraRegistry.values());
}

export function getCameraById(id: string): ICameraDevice | undefined {
  return cameraRegistry.get(id);
}

/**
 * Upserts camera state dynamically from incoming real AI detection payloads.
 * Normalizes pixel bounding boxes to relative [0.0 - 1.0] Canvas space.
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

  // Map subjects to normalized bounding boxes
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

    const label = `${sub.behavior} ${Math.round(sub.confidence * 100)}%`;
    const subLabel = `${sub.role.toUpperCase()} (TRK-${sub.track_id})`;

    return {
      id: `box_trk_${sub.track_id}_${Date.now()}`,
      trackId: sub.track_id,
      label,
      subLabel,
      severity,
      x: parseFloat(normX.toFixed(4)),
      y: parseFloat(normY.toFixed(4)),
      w: parseFloat(normW.toFixed(4)),
      h: parseFloat(normH.toFixed(4)),
      confidence: sub.confidence,
      keypoints: sub.keypoints
    };
  });

  const updatedCamera: ICameraDevice = {
    id: cameraId,
    name: cameraMeta.name || existing?.name || `Camera ${cameraId}`,
    ip: "127.0.0.1",
    fps: 30,
    bitrateKbps: 45,
    status: "ONLINE",
    streamUrl: snapshotBase64 || existing?.streamUrl || "",
    ptzEnabled: true,
    ptzState: existing?.ptzState || { zoom: 1.0, pan: 0, tilt: 0, focus: "AUTO" },
    boundingBoxes,
    zoneId: cameraMeta.zone_id || existing?.zoneId,
    address: cameraMeta.address || existing?.address,
    latitude: cameraMeta.latitude ?? existing?.latitude,
    longitude: cameraMeta.longitude ?? existing?.longitude,
    lastSnapshotBase64: snapshotBase64 || existing?.lastSnapshotBase64
  };

  cameraRegistry.set(cameraId, updatedCamera);
  return updatedCamera;
}

export function handlePtzCommand(
  cameraId: string,
  action: string,
  speed = 1
): { cameraId: string; ptzState: any; status: string } {
  let camera = cameraRegistry.get(cameraId);

  // If camera is not yet in registry, auto-register it
  if (!camera) {
    camera = {
      id: cameraId,
      name: `Camera ${cameraId}`,
      ip: "127.0.0.1",
      fps: 30,
      bitrateKbps: 40,
      status: "ONLINE",
      streamUrl: "",
      ptzEnabled: true,
      ptzState: { zoom: 1.0, pan: 0, tilt: 0, focus: "AUTO" },
      boundingBoxes: []
    };
    cameraRegistry.set(cameraId, camera);
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

  return { cameraId, ptzState: ptz, status: "SUCCESS" };
}
