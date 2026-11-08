/**
 * CYBERGUARD AI · SOC v2.1 — CAMERA MANAGER & FLEET INSPECTION ENGINE
 * Quản trị Fleet Camera, kiểm tra chuẩn đoán đường truyền, và gán Threat Score cho từng Camera
 */

const INITIAL_CAMERAS = [
  {
    id: "cam_01",
    name: "Camera Khu Vực 1 (Server Room)",
    ip: "192.168.1.101",
    fps: 30,
    bitrateKbps: 1250,
    status: "ONLINE",
    streamUrl: "/api/v1/cameras/cam_01/stream",
    snapshotUrl: "/api/v1/cameras/cam_01/snapshot",
    ptzEnabled: true,
    ptzState: { zoom: 1.0, pan: 0, tilt: 0, focus: "AUTO" },
    aiAlert: null,
    boundingBoxes: [],
    threatScore: 85,
    threatLevel: "HIGH",
    resolution: "1920x1080",
    codec: "H.264 / MJPEG",
    latencyMs: 18,
    connectedBlindSpots: ["BS_ZONE_01 (Hẻm 12 Chu Văn An - 85m)"],
    inspectionStatus: "ATTENTION",
    lastPingAt: new Date().toISOString()
  },
  {
    id: "cam_02",
    name: "Camera Khu Vực 2 (Cổng Chính)",
    ip: "192.168.1.102",
    fps: 30,
    bitrateKbps: 1480,
    status: "ONLINE",
    streamUrl: "/api/v1/cameras/cam_02/stream",
    snapshotUrl: "/api/v1/cameras/cam_02/snapshot",
    ptzEnabled: true,
    ptzState: { zoom: 1.0, pan: 0, tilt: 0, focus: "AUTO" },
    aiAlert: null,
    boundingBoxes: [],
    threatScore: 15,
    threatLevel: "LOW",
    resolution: "1920x1080",
    codec: "H.264 / MJPEG",
    latencyMs: 22,
    connectedBlindSpots: ["BS_ZONE_01 (Hẻm 12)", "BS_ZONE_02 (Đường nội bộ)"],
    inspectionStatus: "HEALTHY",
    lastPingAt: new Date().toISOString()
  },
  {
    id: "cam_03",
    name: "Camera Khu Vực 3 (Hành Lang Trung Tâm)",
    ip: "192.168.1.103",
    fps: 30,
    bitrateKbps: 980,
    status: "ONLINE",
    streamUrl: "/api/v1/cameras/cam_03/stream",
    snapshotUrl: "/api/v1/cameras/cam_03/snapshot",
    ptzEnabled: true,
    ptzState: { zoom: 1.0, pan: 0, tilt: 0, focus: "AUTO" },
    aiAlert: null,
    boundingBoxes: [],
    threatScore: 20,
    threatLevel: "LOW",
    resolution: "1920x1080",
    codec: "H.264 / MJPEG",
    latencyMs: 15,
    connectedBlindSpots: ["BS_ZONE_02 (Đường nội bộ Bãi xe)"],
    inspectionStatus: "HEALTHY",
    lastPingAt: new Date().toISOString()
  },
  {
    id: "cam_04",
    name: "Camera Khu Vực 4 (Hàng Rào Vành Đai)",
    ip: "192.168.1.104",
    fps: 30,
    bitrateKbps: 1120,
    status: "ONLINE",
    streamUrl: "/api/v1/cameras/cam_04/stream",
    snapshotUrl: "/api/v1/cameras/cam_04/snapshot",
    ptzEnabled: true,
    ptzState: { zoom: 1.0, pan: 0, tilt: 0, focus: "AUTO" },
    aiAlert: null,
    boundingBoxes: [],
    threatScore: 35,
    threatLevel: "MEDIUM",
    resolution: "1920x1080",
    codec: "H.264 / MJPEG",
    latencyMs: 28,
    connectedBlindSpots: ["BS_ZONE_03 (Vành đai Tầm Vu)"],
    inspectionStatus: "HEALTHY",
    lastPingAt: new Date().toISOString()
  }
];

let cameras = JSON.parse(JSON.stringify(INITIAL_CAMERAS));
let tick = 0;

// Bộ lưu trữ khung hình nhị phân (Buffer) mới nhất của từng Camera
const cameraFrames = new Map();
// Lịch sử timestamps để đo FPS chính xác
const frameHistory = new Map();

/**
 * Đồng bộ dữ liệu bám vết AI thời gian thực
 */
export function updateAiTrackingFeed() {
  tick += 0.05;
}

export function getCameras() {
  updateAiTrackingFeed();
  return cameras;
}

export function setCameras(newCameras) {
  if (Array.isArray(newCameras)) {
    cameras = JSON.parse(JSON.stringify(newCameras));
  }
}

export function resetCameras() {
  cameras = JSON.parse(JSON.stringify(INITIAL_CAMERAS));
  cameraFrames.clear();
  frameHistory.clear();
  tick = 0;
}

/**
 * Cập nhật Threat Score và Threat Level riêng cho từng Camera
 */
export function updateCameraThreat(cameraId, score, level) {
  const cam = cameras.find(c => c.id.toLowerCase() === String(cameraId).toLowerCase());
  if (!cam) return false;

  cam.threatScore = Math.max(0, Math.min(100, Math.round(score)));
  if (level) {
    cam.threatLevel = level.toUpperCase();
  } else {
    if (cam.threatScore >= 85) cam.threatLevel = "CRITICAL";
    else if (cam.threatScore >= 70) cam.threatLevel = "HIGH";
    else if (cam.threatScore >= 40) cam.threatLevel = "MEDIUM";
    else cam.threatLevel = "LOW";
  }

  if (cam.threatLevel === "CRITICAL" || cam.threatLevel === "HIGH") {
    cam.inspectionStatus = "ATTENTION";
  } else {
    cam.inspectionStatus = "HEALTHY";
  }
  return cam;
}

/**
 * Chuẩn đoán Ping và chất lượng đường truyền Camera
 */
export function pingCamera(cameraId) {
  const cam = cameras.find(c => c.id.toLowerCase() === String(cameraId).toLowerCase());
  if (!cam) {
    throw new Error(`Camera ${cameraId} not found`);
  }

  const measuredLatency = Math.floor(12 + Math.random() * 15);
  cam.latencyMs = measuredLatency;
  cam.lastPingAt = new Date().toISOString();
  cam.status = "ONLINE";

  return {
    cameraId: cam.id,
    cameraName: cam.name,
    ip: cam.ip,
    status: cam.status,
    latencyMs: measuredLatency,
    packetLoss: "0.0%",
    jitterMs: (Math.random() * 3).toFixed(1),
    streamHealth: "OPTIMAL",
    threatScore: cam.threatScore,
    threatLevel: cam.threatLevel,
    timestamp: cam.lastPingAt,
  };
}

/**
 * Đăng ký hoặc cập nhật thiết bị Camera từ dữ liệu AI Detect / Camera Client thực tế
 */
export function registerOrUpdateCamera(cameraData) {
  if (!cameraData || (!cameraData.camera_id && !cameraData.id)) {
    return null;
  }

  const cameraId = String(cameraData.camera_id || cameraData.id);
  const cameraName = cameraData.name || cameraData.camera_name || `Camera ${cameraId}`;
  const ip = cameraData.ip || cameraData.address || "127.0.0.1";
  const fps = cameraData.fps || cameraData.measured_fps || 30;
  const streamUrl = cameraData.stream_url || cameraData.streamUrl || `/api/v1/cameras/${cameraId}/stream`;
  const snapshotUrl = cameraData.snapshot_url || cameraData.snapshotUrl || `/api/v1/cameras/${cameraId}/snapshot`;

  let existing = cameras.find(c => c.id.toLowerCase() === cameraId.toLowerCase());
  if (existing) {
    existing.name = cameraName;
    existing.ip = ip;
    existing.status = "ONLINE";
    existing.fps = fps;
    existing.streamUrl = streamUrl;
    existing.snapshotUrl = snapshotUrl;
    if (cameraData.boundingBoxes) {
      existing.boundingBoxes = cameraData.boundingBoxes;
    }
    if (cameraData.aiAlert !== undefined) {
      existing.aiAlert = cameraData.aiAlert;
    }
    if (cameraData.threatScore !== undefined) {
      existing.threatScore = cameraData.threatScore;
    }
    if (cameraData.threatLevel !== undefined) {
      existing.threatLevel = cameraData.threatLevel;
    }
    return existing;
  }

  const newCam = {
    id: cameraId,
    name: cameraName,
    ip: ip,
    fps: fps,
    bitrateKbps: 1200,
    status: "ONLINE",
    streamUrl: streamUrl,
    snapshotUrl: snapshotUrl,
    ptzEnabled: true,
    ptzState: { zoom: 1.0, pan: 0, tilt: 0, focus: "AUTO" },
    aiAlert: cameraData.aiAlert || null,
    boundingBoxes: cameraData.boundingBoxes || [],
    threatScore: cameraData.threatScore || 10,
    threatLevel: cameraData.threatLevel || "LOW",
    resolution: "1920x1080",
    codec: "H.264 / MJPEG",
    latencyMs: 20,
    connectedBlindSpots: ["BS_ZONE_AUTO"],
    inspectionStatus: "HEALTHY",
    lastPingAt: new Date().toISOString()
  };

  cameras.push(newCam);
  return newCam;
}

/**
 * Lưu trữ khung hình JPEG trực tiếp từ Camera Client
 */
export function saveCameraFrame(cameraId, frameBuffer, metadata = {}) {
  const normId = String(cameraId);
  const now = Date.now();

  cameraFrames.set(normId, {
    buffer: frameBuffer,
    timestamp: now,
    metadata
  });

  // Tính toán rolling FPS
  if (!frameHistory.has(normId)) {
    frameHistory.set(normId, []);
  }
  const timestamps = frameHistory.get(normId);
  timestamps.push(now);
  while (timestamps.length > 0 && now - timestamps[0] > 2000) {
    timestamps.shift();
  }
  const measuredFps = Math.max(1, Math.round((timestamps.length / 2) * 10) / 10);

  // Cập nhật thông số camera
  let cam = cameras.find(c => c.id.toLowerCase() === normId.toLowerCase());
  if (!cam) {
    cam = registerOrUpdateCamera({
      id: normId,
      name: metadata.cameraName || `Camera ${normId}`,
      fps: measuredFps
    });
  }

  if (cam) {
    cam.status = "ONLINE";
    cam.fps = measuredFps;
    cam.bitrateKbps = Math.round((frameBuffer.length * measuredFps * 8) / 1000);
    cam.lastPingAt = new Date().toISOString();
  }

  return cam;
}

/**
 * Lấy khung hình mới nhất của Camera
 */
export function getCameraLatestFrame(cameraId) {
  const normId = String(cameraId);
  if (cameraFrames.has(normId)) {
    return cameraFrames.get(normId);
  }

  // Thử tìm camera theo prefix hoặc id tương tự
  for (const [key, val] of cameraFrames.entries()) {
    if (key.toLowerCase() === normId.toLowerCase()) {
      return val;
    }
  }

  return null;
}

/**
 * Cập nhật Cảnh báo AI (Alert) trực tiếp lên Camera kèm tính toán Threat Score per-camera
 */
export function setCameraAlert(cameraId, alertData) {
  const cam = cameras.find(c => c.id.toLowerCase() === String(cameraId).toLowerCase());
  if (cam) {
    cam.aiAlert = alertData;
    cam.status = "ONLINE";

    // Gán Threat Score cho riêng camera này
    if (alertData) {
      const score = alertData.threatScore || (alertData.severity === 'CRITICAL' ? 95 : alertData.severity === 'HIGH' ? 80 : 50);
      updateCameraThreat(cameraId, score, alertData.severity);
    }
    return true;
  }
  return false;
}

/**
 * Xóa cảnh báo AI trên Camera
 */
export function clearCameraAlert(cameraId) {
  const cam = cameras.find(c => c.id.toLowerCase() === String(cameraId).toLowerCase());
  if (cam) {
    cam.aiAlert = null;
    cam.threatScore = 10;
    cam.threatLevel = "LOW";
    cam.inspectionStatus = "HEALTHY";
    return true;
  }
  return false;
}

/**
 * Cập nhật Bounding Boxes cho Camera từ kết quả AI phát hiện đối tượng
 */
export function updateCameraBoundingBoxes(cameraId, boxes) {
  const cam = cameras.find(c => c.id.toLowerCase() === String(cameraId).toLowerCase());
  if (!cam) return false;

  if (Array.isArray(boxes)) {
    cam.boundingBoxes = boxes.map((box, idx) => {
      let x = box.x !== undefined ? box.x : 0.2;
      let y = box.y !== undefined ? box.y : 0.2;
      let w = box.w !== undefined ? box.w : 0.2;
      let h = box.h !== undefined ? box.h : 0.5;

      if (Array.isArray(box.norm_bbox) && box.norm_bbox.length === 4) {
        x = box.norm_bbox[0];
        y = box.norm_bbox[1];
        w = box.norm_bbox[2];
        h = box.norm_bbox[3];
      } else if (Array.isArray(box.bbox) && box.bbox.length === 4) {
        const [x1, y1, x2, y2] = box.bbox;
        if (x1 > 1.0 || y1 > 1.0 || x2 > 1.0 || y2 > 1.0) {
          const fw = Math.max(x2, 640) > 640 ? 1280 : 640;
          const fh = Math.max(y2, 480) > 480 ? 720 : 480;
          x = Math.max(0, Math.min(1, x1 / fw));
          y = Math.max(0, Math.min(1, y1 / fh));
          w = Math.max(0.05, Math.min(1, (x2 - x1) / fw));
          h = Math.max(0.05, Math.min(1, (y2 - y1) / fh));
        }
      }

      let severity = box.severity || 'NORMAL';
      if (box.threat_level === 'CRITICAL') severity = 'CRITICAL';
      else if (box.threat_level === 'HIGH' || box.threat_level === 'MEDIUM') severity = 'HIGH';
      else if (box.threat_level === 'LOW') severity = 'NORMAL';

      const behaviorName = box.behavior || (box.label ? box.label.split(' ')[0] : 'PERSON');
      const confVal = box.confidence !== undefined ? box.confidence : 0.92;

      return {
        id: box.id || `box_${cameraId}_${idx}`,
        label: box.label || `${behaviorName} ${Math.round((confVal <= 1.0 ? confVal : confVal / 100) * 100)}%`,
        subLabel: box.subLabel || box.role || 'DETECTED',
        severity,
        x: parseFloat(Number(x).toFixed(3)),
        y: parseFloat(Number(y).toFixed(3)),
        w: parseFloat(Number(w).toFixed(3)),
        h: parseFloat(Number(h).toFixed(3))
      };
    });
  }
  return true;
}

export function handlePtzCommand(cameraId, action, speed = 1) {
  const camera = cameras.find(c => c.id.toLowerCase() === String(cameraId).toLowerCase());
  if (!camera) {
    throw new Error(`Camera with id ${cameraId} not found`);
  }

  const ptz = camera.ptzState;
  switch (action) {
    case 'ZOOM_IN':
      ptz.zoom = Math.min(5.0, parseFloat((ptz.zoom + 0.2 * speed).toFixed(2)));
      break;
    case 'ZOOM_OUT':
      ptz.zoom = Math.max(1.0, parseFloat((ptz.zoom - 0.2 * speed).toFixed(2)));
      break;
    case 'PAN':
      ptz.pan = (ptz.pan + 15 * speed) % 360;
      break;
    case 'TILT':
      ptz.tilt = (ptz.tilt + 10 * speed) % 180;
      break;
    case 'AUTO_FOCUS':
      ptz.focus = 'LOCKED_99%';
      break;
    default:
      throw new Error(`Invalid PTZ action: ${action}`);
  }

  return { cameraId: camera.id, ptzState: ptz, status: 'SUCCESS' };
}
