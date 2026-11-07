/**
 * CYBERGUARD AI · SOC v2.1 — CAMERA MANAGER & REAL PTZ STATE ENGINE
 */

let cameras = [
  {
    id: "cam_01",
    name: "Server Room",
    ip: "163.16.8.259",
    fps: 30,
    bitrateKbps: 37,
    status: "ONLINE",
    streamUrl: "/streams/cam_01.m3u8",
    ptzEnabled: true,
    ptzState: { zoom: 1.0, pan: 0, tilt: 0, focus: "AUTO" },
    boundingBoxes: [
      {
        id: "box_01",
        label: "PERSON 98%",
        subLabel: "INTRUSION",
        severity: "CRITICAL",
        x: 0.35,
        y: 0.22,
        w: 0.22,
        h: 0.65
      }
    ]
  },
  {
    id: "cam_02",
    name: "Main Gate",
    ip: "185.220.161.45",
    fps: 30,
    bitrateKbps: 47,
    status: "ONLINE",
    streamUrl: "/streams/cam_02.m3u8",
    ptzEnabled: true,
    ptzState: { zoom: 1.0, pan: 0, tilt: 0, focus: "AUTO" },
    boundingBoxes: [
      {
        id: "box_02",
        label: "VEHICLE 94%",
        subLabel: "MONITORED",
        severity: "NORMAL",
        x: 0.15,
        y: 0.40,
        w: 0.35,
        h: 0.45
      }
    ]
  },
  {
    id: "cam_03",
    name: "Server Room",
    ip: "192.168.16.121",
    fps: 30,
    bitrateKbps: 35,
    status: "ONLINE",
    streamUrl: "/streams/cam_03.m3u8",
    ptzEnabled: true,
    ptzState: { zoom: 1.0, pan: 0, tilt: 0, focus: "AUTO" },
    boundingBoxes: []
  },
  {
    id: "cam_04",
    name: "Main Gate",
    ip: "185.220.161.45",
    fps: 30,
    bitrateKbps: 37,
    status: "ONLINE",
    streamUrl: "/streams/cam_04.m3u8",
    ptzEnabled: true,
    ptzState: { zoom: 1.0, pan: 0, tilt: 0, focus: "AUTO" },
    boundingBoxes: [
      {
        id: "box_04",
        label: "PERSON 91%",
        subLabel: "LOITERING",
        severity: "HIGH",
        x: 0.55,
        y: 0.28,
        w: 0.18,
        h: 0.58
      }
    ]
  }
];

let tick = 0;

/**
 * Cập nhật tọa độ bám vết mượt mà mô phỏng AI Computer Vision theo thời gian thực
 */
export function updateAiTrackingFeed() {
  tick += 0.05;

  // Camera 1: Đối tượng di chuyển chậm dọc hành lang phòng Server
  const cam1 = cameras.find(c => c.id === 'cam_01');
  if (cam1 && cam1.boundingBoxes[0]) {
    const zoom = cam1.ptzState.zoom;
    const baseW = 0.22 / zoom;
    const baseH = 0.65 / zoom;
    cam1.boundingBoxes[0].x = Math.max(0.1, Math.min(0.65, 0.35 + Math.sin(tick) * 0.08));
    cam1.boundingBoxes[0].y = Math.max(0.15, Math.min(0.3, 0.22 + Math.cos(tick * 0.7) * 0.03));
    cam1.boundingBoxes[0].w = baseW;
    cam1.boundingBoxes[0].h = baseH;
  }

  // Camera 2: Xe cộ di chuyển trước cổng chính
  const cam2 = cameras.find(c => c.id === 'cam_02');
  if (cam2 && cam2.boundingBoxes[0]) {
    cam2.boundingBoxes[0].x = (0.15 + (tick * 0.04) % 0.6);
  }
}

export function getCameras() {
  updateAiTrackingFeed();
  return cameras;
}

export function handlePtzCommand(cameraId, action, speed = 1) {
  const camera = cameras.find(c => c.id === cameraId);
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
    case 'AUTO_FOCUS':
      ptz.focus = 'LOCKED_99%';
      break;
    default:
      break;
  }

  console.log(`[PTZ STATE] Camera ${cameraId} -> Action: ${action} | New State:`, ptz);
  return { cameraId, ptzState: ptz, status: 'SUCCESS' };
}
