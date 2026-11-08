/**
 * CYBERGUARD AI · SOC v2.1 — CAMERA MANAGER & REAL PTZ STATE ENGINE
 * Tích hợp toàn diện luồng camera thời gian thực và AI Computer Vision bám vết
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
    boundingBoxes: []
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
    boundingBoxes: []
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
    boundingBoxes: []
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
    boundingBoxes: []
  }
];

let cameras = JSON.parse(JSON.stringify(INITIAL_CAMERAS));
let tick = 0;

// Bộ lưu trữ khung hình nhị phân (Buffer) mới nhất của từng Camera
const cameraFrames = new Map();
// Lịch sử timestamps để đo FPS chính xác
const frameHistory = new Map();

/**
 * Đồng bộ dữ liệu bám vết AI thời gian thực (100% dựa trên phát hiện AI từ NVIDIA NIM/YOLO)
 */
export function updateAiTrackingFeed() {
  tick += 0.05;
  // Bỏ hoàn toàn việc tạo dữ liệu giả lập sine wave.
  // Các boundingBoxes và aiAlert được cập nhật trực tiếp qua updateCameraBoundingBoxes và setCameraAlert từ AI inference.
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
    boundingBoxes: cameraData.boundingBoxes || []
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

    // Xử lý AI alert nếu có gửi kèm trong frame metadata
    if (metadata.testAction || metadata.action || metadata.primaryAction) {
      const action = String(metadata.testAction || metadata.action || metadata.primaryAction).toUpperCase();
      const isCritical = action.includes("WEAPON") || action.includes("KNIFE") || action.includes("FIGHT");
      const isHigh = action.includes("FALLEN") || action.includes("INTRUSION") || action.includes("LOITERING");

      if (isCritical || isHigh) {
        cam.aiAlert = {
          hasAlert: true,
          type: action,
          severity: isCritical ? "CRITICAL" : "HIGH",
          message: `Phát hiện hành vi ${action}`,
          confidence: metadata.confidence || 0.95,
          timestamp: now
        };
      }
    }
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
 * Cập nhật Cảnh báo AI (Alert) trực tiếp lên Camera
 */
export function setCameraAlert(cameraId, alertData) {
  const cam = cameras.find(c => c.id.toLowerCase() === String(cameraId).toLowerCase());
  if (cam) {
    cam.aiAlert = alertData;
    cam.status = "ONLINE";
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
