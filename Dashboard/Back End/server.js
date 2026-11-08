/**
 * CYBERGUARD AI · SOC v2.1 — BACKEND CORE SERVER (PORT 8000)
 * Phục vụ Web App tại /dashboard/ & Tích hợp Toàn diện AI Detection Engine
 * Kết nối Trực tiếp Camera Client, Live MJPEG Streaming & Xử lý Alert AI Qua Lớp Trung Gian
 */

import http from 'http';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';
import express from 'express';
import cors from 'cors';
import { WebSocketServer } from 'ws';

import { getTelemetryOverview, updateThreatScore } from './src/telemetryEngine.js';
import {
  getCameras,
  handlePtzCommand,
  registerOrUpdateCamera,
  updateCameraBoundingBoxes,
  saveCameraFrame,
  getCameraLatestFrame,
  setCameraAlert,
  clearCameraAlert
} from './src/cameraManager.js';
import { getRecentIncidents, getIncidentPlayback, addIncidentFromDetect, getIncidentById } from './src/incidentManager.js';
import { processHitlVerification, getAuditLogs } from './src/hitlDispatcher.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 8000;
const AI_INFERENCE_URL = process.env.AI_INFERENCE_URL || 'http://127.0.0.1:7777';

// Thư mục lưu vết kiểm toán AI & logs
const LOGS_DIR = path.resolve(__dirname, '../../output/audit_logs');
try {
  if (!fs.existsSync(LOGS_DIR)) {
    fs.mkdirSync(LOGS_DIR, { recursive: true });
  }
} catch {
  // Bỏ qua lỗi tạo thư mục
}

app.use(cors());

// Hỗ trợ tiếp nhận cả raw binary JPEG frame từ camera client và JSON payloads
app.use(express.raw({ type: ['image/jpeg', 'application/octet-stream'], limit: '25mb' }));
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ limit: '50mb', extended: true }));

// Đường dẫn tới thư mục build của Web App React (Dashboard/Front End/dist)
const DIST_PATH = path.resolve(__dirname, '../Front End/dist');
const HAS_DIST = fs.existsSync(DIST_PATH) && fs.existsSync(path.join(DIST_PATH, 'index.html'));

// Minimal valid 1x1 JPEG fallback
const MINIMAL_JPEG = Buffer.from(
  '/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA=',
  'base64'
);

// =============================================================================
// 1. PHỤC VỤ WEB APP TẠI /dashboard/ VÀ /
// =============================================================================

if (HAS_DIST) {
  app.use('/dashboard/assets', express.static(path.join(DIST_PATH, 'assets')));
  app.use('/assets', express.static(path.join(DIST_PATH, 'assets')));
  app.use(express.static(DIST_PATH));

  app.get(['/dashboard', '/dashboard/*'], (req, res) => {
    res.sendFile(path.join(DIST_PATH, 'index.html'));
  });

  app.get('/', (req, res) => {
    const accept = req.headers.accept || '';
    if (accept.includes('text/html')) {
      res.sendFile(path.join(DIST_PATH, 'index.html'));
    } else {
      res.json({
        service: "CyberGuard AI SOC Core Server",
        version: "2.1.0",
        status: "RUNNING",
        dashboard_url: `http://localhost:${PORT}/dashboard/`,
        rest_api_overview: `http://localhost:${PORT}/api/soc/overview`,
        live_stream_ws: `ws://localhost:${PORT}/ws/live-stream`,
        ai_inference_target: AI_INFERENCE_URL
      });
    }
  });
} else {
  app.get(['/', '/dashboard', '/dashboard/*'], (req, res) => {
    res.send(`<!DOCTYPE html>
<html><head><title>CyberGuard AI SOC</title><meta charset="utf-8"></head>
<body style="background:#070B14;color:#FFF;font-family:monospace;padding:40px;">
<h2>CYBERGUARD AI · SOC v2.1 CORE SERVICE</h2>
<p>Web App dist đang được đóng gói. Vui lòng chạy: <code>cd "Dashboard/Front End" && npm run build</code></p>
<p>API Endpoint: <a style="color:#06B6D4" href="/api/soc/overview">/api/soc/overview</a></p>
</body></html>`);
  });
}

// =============================================================================
// 2. KẾT NỐI CAMERA CLIENT & LIVE MJPEG STREAMING QUA LỚP AI TRUNG GIAN
// =============================================================================

// 2.1 Đăng ký Camera Client (EdgeCameraClient / client.py)
app.post('/api/v1/cameras/register', (req, res) => {
  try {
    const payload = req.body;
    if (!payload || !payload.camera_id) {
      return res.status(400).json({ success: false, error: 'camera_id is mandatory for registration' });
    }

    const cam = registerOrUpdateCamera({
      id: payload.camera_id,
      name: payload.name || `Camera ${payload.camera_id}`,
      ip: req.ip || payload.ip || '127.0.0.1',
      latitude: payload.latitude,
      longitude: payload.longitude,
      address: payload.address,
      fps: payload.fps || 30
    });

    broadcastWs({
      type: 'TELEMETRY_AND_AI_TICK',
      cameras: getCameras(),
      timestamp: Date.now()
    });

    res.status(200).json({
      status: "success",
      message: `Camera ${payload.camera_id} successfully registered`,
      camera: cam,
      stream_url: `/api/v1/cameras/${payload.camera_id}/stream`,
      snapshot_url: `/api/v1/cameras/${payload.camera_id}/snapshot`
    });
  } catch (err) {
    res.status(400).json({ success: false, error: err.message });
  }
});

// 2.2 Hàm phụ: Gọi Lớp AI Trung gian để Phân tích Khung hình (Intermediate AI Layer)
async function requestIntermediateAiAnalysis(cameraId, cameraName, frameBuffer, testAction, timestampMs) {
  try {
    const aiTargetUrl = `${AI_INFERENCE_URL}/api/v1/ingest/frame`;
    const headers = {
      'Content-Type': 'image/jpeg',
      'X-Camera-ID': cameraId,
      'X-Timestamp-Ms': String(timestampMs),
      'Content-Length': String(frameBuffer.length),
      'X-Batch-AI': 'false',
      'X-Sync-VLM': 'true',
    };
    if (cameraName) headers['X-Camera-Name'] = encodeURIComponent(cameraName);
    if (testAction) headers['X-Test-Action'] = testAction;

    const aiRes = await fetch(aiTargetUrl, {
      method: 'POST',
      headers,
      body: frameBuffer,
      signal: AbortSignal.timeout(2500)
    });

    if (aiRes.ok) {
      const aiData = await aiRes.json();
      return aiData;
    }
  } catch {
    // Khi AI Server ngoài chưa bật hoặc đang bận, fallback xử lý an toàn
  }
  return null;
}

// 2.3 Tiếp nhận Frame JPEG trực tiếp từ Camera Client qua HTTP POST
const handleIngestFrame = async (req, res) => {
  try {
    const cameraId = req.headers['x-camera-id'] || req.params.id || 'CAM_01';
    let cameraName = '';
    try {
      cameraName = decodeURIComponent(req.headers['x-camera-name'] || '');
    } catch {
      cameraName = req.headers['x-camera-name'] || '';
    }

    const testAction = req.headers['x-test-action'] || '';
    const timestampMs = parseInt(req.headers['x-timestamp-ms'] || String(Date.now()), 10);

    let frameBuffer = null;
    if (Buffer.isBuffer(req.body)) {
      frameBuffer = req.body;
    } else if (req.body && req.body.image_base64) {
      const b64Data = req.body.image_base64.replace(/^data:image\/\w+;base64,/, '');
      frameBuffer = Buffer.from(b64Data, 'base64');
    }

    if (!frameBuffer || frameBuffer.length === 0) {
      return res.status(400).json({ status: "error", message: "Empty frame buffer received" });
    }

    // 1. Lưu trữ frame vào Frame Buffer để phục vụ live stream ngay lập tức
    const cam = saveCameraFrame(cameraId, frameBuffer, {
      cameraName,
      testAction,
      timestampMs
    });

    // 2. Bắt buộc đi qua lớp xử lý AI ở giữa (Gọi API AI Server)
    const aiAnalysis = await requestIntermediateAiAnalysis(
      cameraId,
      cameraName,
      frameBuffer,
      testAction,
      timestampMs
    );

    // Xác định hành vi phát hiện (từ AI hoặc testAction)
    const primaryAction = String(
      aiAnalysis?.primary_action || aiAnalysis?.action_type || testAction || 'NORMAL'
    ).toUpperCase();

    const isWeapon = primaryAction.includes('WEAPON');
    const isKnife = primaryAction.includes('KNIFE') || primaryAction.includes('SHARP');
    const isFallen = primaryAction.includes('FALLEN');
    const isFighting = primaryAction.includes('FIGHT');
    const isLoitering = primaryAction.includes('LOITER');
    const isIntrusion = primaryAction.includes('INTRUSION');

    const isCritical = isWeapon || isKnife || isFighting || (aiAnalysis?.highest_threat === 'CRITICAL');
    const isHigh = isFallen || isLoitering || isIntrusion || (aiAnalysis?.highest_threat === 'HIGH');

    let detectedAction = primaryAction;
    if (isWeapon) detectedAction = 'WEAPON_THREAT';
    else if (isKnife) detectedAction = 'KNIFE_THREAT';
    else if (isFallen) detectedAction = 'FALLEN';
    else if (isFighting) detectedAction = 'FIGHTING';
    else if (isIntrusion) detectedAction = 'INTRUSION';
    else if (isLoitering) detectedAction = 'LOITERING';

    // 3. Luôn cập nhật Bounding Box từ kết quả AI phát hiện đối tượng để bám vết liên tục trên Dashboard
    if (aiAnalysis?.humans && Array.isArray(aiAnalysis.humans)) {
      updateCameraBoundingBoxes(cameraId, aiAnalysis.humans);
    }

    // 4. Nếu AI phát hiện hành vi nguy cấp: Gắn nhãn aiAlert, cập nhật Bounding Box, đẩy Incident & Lưu Log
    if (isCritical || isHigh) {
      const severity = isCritical ? 'CRITICAL' : 'HIGH';
      const confidence = aiAnalysis?.confidence || (aiAnalysis?.highest_threat_score || 0.96);
      const reasoning = aiAnalysis?.reasoning || `AI VLM đã nhận diện hành vi ${detectedAction} trên luồng camera.`;

      // Cập nhật trường aiAlert trực tiếp trên Camera
      setCameraAlert(cameraId, {
        hasAlert: true,
        type: detectedAction,
        severity,
        message: reasoning,
        confidence: confidence <= 1.0 ? confidence : confidence / 100,
        timestamp: Date.now()
      });

      // Đẩy sự cố lên Dashboard & Lưu vào Log kiểm toán
      const incidentPayload = {
        event_id: `EVT-AI-${detectedAction}-${cameraId}-${Date.now()}`,
        primary_action: detectedAction,
        severity,
        threat_score: confidence <= 1.0 ? Math.round(confidence * 100) : confidence,
        camera_id: cameraId,
        camera_name: cameraName || cam?.name,
        reasoning,
        vlmAnalysis: reasoning,
        subjects: aiAnalysis?.humans || []
      };

      const addedIncident = addIncidentFromDetect(incidentPayload);

      // Lưu log kiểm toán vào tệp disk
      try {
        const logFile = path.join(LOGS_DIR, `incident_${Date.now()}_${cameraId}.json`);
        fs.writeFileSync(logFile, JSON.stringify(addedIncident, null, 2), 'utf-8');
      } catch {
        // bỏ qua lỗi ghi disk nếu có
      }

      // Phát thông điệp cảnh báo thời gian thực qua WebSocket
      broadcastWs({
        type: 'INCIDENT_ALERT',
        incident: addedIncident,
        timestamp: Date.now()
      });
    }

    // Phát broadcast cập nhật telemetry & camera state tới WebSocket client
    broadcastWs({
      type: 'TELEMETRY_AND_AI_TICK',
      cameras: getCameras(),
      timestamp: Date.now()
    });

    res.status(200).json({
      status: "success",
      camera_id: cameraId,
      timestamp_ms: timestampMs,
      action_detected: detectedAction,
      threat_level: (isCritical ? "CRITICAL" : isHigh ? "HIGH" : "LOW"),
      ai_analyzed: Boolean(aiAnalysis),
      fps: cam?.fps || 30
    });
  } catch (err) {
    res.status(400).json({ status: "error", message: err.message });
  }
};

app.post('/api/v1/cameras/:id/stream', handleIngestFrame);
app.post(['/api/v1/ingest/frame', '/api/v1/stream/push'], handleIngestFrame);

// 2.4 Phát luồng MJPEG Video Stream thời gian thực (multipart/x-mixed-replace)
const handleMjpegStream = (req, res) => {
  const cameraId = req.params.id || 'cam_01';

  res.writeHead(200, {
    'Content-Type': 'multipart/x-mixed-replace; boundary=frame',
    'Cache-Control': 'no-cache, no-store, must-revalidate',
    'Pragma': 'no-cache',
    'Expires': '0',
    'Connection': 'close',
    'Access-Control-Allow-Origin': '*'
  });

  const pushFrame = () => {
    const frameData = getCameraLatestFrame(cameraId);
    const buf = (frameData && frameData.buffer) ? frameData.buffer : MINIMAL_JPEG;

    res.write(`--frame\r\nContent-Type: image/jpeg\r\nContent-Length: ${buf.length}\r\n\r\n`);
    res.write(buf);
    res.write('\r\n');
  };

  pushFrame();

  const timer = setInterval(() => {
    try {
      pushFrame();
    } catch {
      clearInterval(timer);
    }
  }, 100);

  req.on('close', () => {
    clearInterval(timer);
  });
};

app.get(['/api/v1/cameras/:id/stream', '/api/v1/cameras/:id/stream.mjpg'], handleMjpegStream);
app.get(['/stream.mjpg', '/live.mjpg'], handleMjpegStream);

// 2.5 Phát Ảnh Chụp Tức Thời (Snapshot JPEG)
app.get('/api/v1/cameras/:id/snapshot', (req, res) => {
  const cameraId = req.params.id;
  const frameData = getCameraLatestFrame(cameraId);
  const buf = (frameData && frameData.buffer) ? frameData.buffer : MINIMAL_JPEG;

  res.setHeader('Content-Type', 'image/jpeg');
  res.setHeader('Content-Length', buf.length);
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.send(buf);
});

// =============================================================================
// 3. REST APIS CHUẨN CHO SOC DASHBOARD (standard.md)
// =============================================================================

// 3.1 Dashboard & Telemetry Overview
app.get('/api/soc/overview', (req, res) => {
  const incidents = getRecentIncidents();
  const activeThreats = incidents.filter(i => i.status === 'PENDING_VERIFICATION').length;
  const criticalThreats = incidents.filter(i => i.severity === 'CRITICAL' && i.status === 'PENDING_VERIFICATION').length;
  const overview = getTelemetryOverview(activeThreats, criticalThreats);
  res.json(overview);
});

// 3.2 Danh sách Camera & AI Stream
app.get(['/api/devices/cameras', '/api/v1/cameras'], (req, res) => {
  res.json(getCameras());
});

// 3.3 Điều khiển Camera PTZ
app.post('/api/cameras/:id/ptz', (req, res) => {
  try {
    const { action, speed } = req.body || {};
    const result = handlePtzCommand(req.params.id, action, speed);
    res.json(result);
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

// 3.4 Incident Feed & Recent Threats
app.get('/api/incidents/recent', (req, res) => {
  res.json(getRecentIncidents());
});

// 3.5 Bằng chứng Playback từ Rolling Buffer
app.get('/api/incidents/:id/playback', (req, res) => {
  const evidence = getIncidentPlayback(req.params.id);
  if (!evidence) {
    return res.status(404).json({ error: 'Incident not found' });
  }
  res.json(evidence);
});

// 3.6 Chốt chặn Xác thực Operational HITL (CD-04)
app.post(['/api/incidents/:id/verify', '/api/v1/operator/action'], (req, res) => {
  try {
    const incidentId = req.params.id || req.body?.incidentId || req.body?.event_id;
    const operatorId = req.body?.operatorId || req.body?.operator_id;
    const decision = req.body?.decision;
    const notes = req.body?.notes;
    const verifiedAt = req.body?.verifiedAt || req.body?.timestamp;

    const result = processHitlVerification({
      incidentId,
      operatorId,
      decision,
      notes,
      verifiedAt
    });

    // Phát thông điệp cập nhật trạng thái HITL tới WebSocket
    broadcastWs({
      type: 'DECISION_PROCESSED',
      incidentId,
      decision,
      newStatus: decision === 'DISMISS_FALSE_POSITIVE' ? 'DISMISSED' : decision === 'DOWNGRADE_MONITOR' ? 'DOWNGRADED_MONITORING' : 'OPERATOR_CONFIRMED'
    });

    res.json(result);
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

// 3.7 Audit Log Kiểm toán Bất biến
app.get('/api/soc/audit-logs', (req, res) => {
  res.json(getAuditLogs());
});

// =============================================================================
// 4. TIẾP NHẬN DỮ LIỆU TỪ AI DETECTION ENGINE & XỬ LÝ ALERT
// =============================================================================

const handleIngestDetection = (req, res) => {
  try {
    const payload = req.body;
    if (!payload || typeof payload !== 'object') {
      return res.status(400).json({ success: false, error: 'Empty or invalid JSON payload' });
    }

    // 1. Ghi nhận sự cố vào Incident Manager
    const incident = addIncidentFromDetect(payload);

    // 2. Cập nhật hoặc đăng ký Camera nếu có
    if (payload.camera || payload.camera_id) {
      registerOrUpdateCamera(payload.camera || { id: payload.camera_id, name: payload.camera_name });
    }

    // 3. Cập nhật AI Bounding Boxes lên Camera tương ứng
    if (payload.subjects || payload.boxes || payload.detection?.subjects) {
      updateCameraBoundingBoxes(
        incident.cameraId,
        payload.subjects || payload.boxes || payload.detection?.subjects
      );
    }

    // 4. Nhận diện các lớp hành vi nguy cấp & Gắn nhãn Cảnh báo AI (aiAlert):
    // WEAPON_THREAT, KNIFE_THREAT, FALLEN, FIGHTING, LOITERING, INTRUSION
    const action = String(incident.primary_action || incident.action_type || incident.title).toUpperCase();
    const isWeapon = action.includes('WEAPON');
    const isKnife = action.includes('KNIFE') || action.includes('SHARP');
    const isFallen = action.includes('FALLEN');
    const isFighting = action.includes('FIGHT');
    const isLoitering = action.includes('LOITER');
    const isIntrusion = action.includes('INTRUSION');

    const isCritical = incident.severity === 'CRITICAL' || isWeapon || isKnife || isFighting;
    const isHigh = incident.severity === 'HIGH' || isFallen || isIntrusion || isLoitering;

    if (isCritical || isHigh) {
      let normAction = incident.primary_action;
      if (isWeapon) normAction = 'WEAPON_THREAT';
      else if (isKnife) normAction = 'KNIFE_THREAT';
      else if (isFallen) normAction = 'FALLEN';
      else if (isFighting) normAction = 'FIGHTING';
      else if (isIntrusion) normAction = 'INTRUSION';
      else if (isLoitering) normAction = 'LOITERING';

      setCameraAlert(incident.cameraId, {
        hasAlert: true,
        type: normAction,
        severity: isCritical ? 'CRITICAL' : 'HIGH',
        message: incident.vlmAnalysis || `Cảnh báo AI: ${normAction}`,
        confidence: incident.threatScore ? (incident.threatScore > 1 ? incident.threatScore / 100 : incident.threatScore) : 0.96,
        timestamp: Date.now()
      });
    }

    // 5. Đồng bộ điểm rủi ro Threat Score
    updateThreatScore(incident.threatScore);

    // 6. Ghi log sự cố ra file audit log trên đĩa
    try {
      const logFile = path.join(LOGS_DIR, `webhook_${Date.now()}_${incident.id}.json`);
      fs.writeFileSync(logFile, JSON.stringify(incident, null, 2), 'utf-8');
    } catch {
      // bỏ qua lỗi disk
    }

    // 7. Phát thông điệp cảnh báo lập tức qua WebSocket & SSE
    broadcastWs({
      type: 'INCIDENT_ALERT',
      incident,
      timestamp: Date.now()
    });

    broadcastWs({
      type: 'TELEMETRY_AND_AI_TICK',
      cameras: getCameras(),
      timestamp: Date.now()
    });

    broadcastSse({
      event: 'incident',
      data: incident
    });

    res.status(200).json({
      success: true,
      status: 'RECEIVED_AND_INDEXED',
      event_id: incident.id,
      threat_level: incident.severity,
      threat_score: incident.threatScore,
      timestamp: new Date().toISOString()
    });
  } catch (err) {
    res.status(400).json({ success: false, error: err.message });
  }
};

app.post('/api/v1/incidents', handleIngestDetection);
app.post('/api/incidents/webhook', handleIngestDetection);
app.post('/api/soc/incidents', handleIngestDetection);
app.post('/api/v1/test/receive', handleIngestDetection);

// =============================================================================
// 5. API TƯƠNG THÍCH AI-SOC INFERENCE SERVER (/api/v1/dashboard/*)
// =============================================================================

app.get('/api/v1/dashboard/state', (req, res) => {
  const incidents = getRecentIncidents();
  const activeThreats = incidents.filter(i => i.status === 'PENDING_VERIFICATION').length;
  const criticalThreats = incidents.filter(i => i.severity === 'CRITICAL' && i.status === 'PENDING_VERIFICATION').length;
  const overview = getTelemetryOverview(activeThreats, criticalThreats);

  res.json({
    status: "online",
    active_cameras: getCameras().filter(c => c.status === 'ONLINE').length,
    cameras: getCameras(),
    global_threat_level: overview.threatLevel,
    highest_threat_score: overview.threatScore,
    open_threats: overview.metrics.openThreats,
    critical_threats: overview.metrics.criticalThreats,
    latest_incident: incidents[0] || null,
    recent_logs: getAuditLogs().slice(-30)
  });
});

app.get('/api/v1/dashboard/logs', (req, res) => {
  const { severity, keyword } = req.query;
  let logs = getAuditLogs();

  if (severity) {
    logs = logs.filter(l => (l.decision || '').toLowerCase().includes(severity.toLowerCase()));
  }
  if (keyword) {
    logs = logs.filter(l => JSON.stringify(l).toLowerCase().includes(keyword.toLowerCase()));
  }

  res.json({
    count: logs.length,
    logs
  });
});

app.get('/api/v1/dashboard/logs/download', (req, res) => {
  const logs = getAuditLogs();
  const textContent = logs.map(l => `[${l.timestamp}] [${l.decision}] Op: ${l.operatorId} Inc: ${l.incidentId}`).join('\n');
  res.setHeader('Content-Type', 'text/plain; charset=utf-8');
  res.setHeader('Content-Disposition', 'attachment; filename="soc_audit_logs.txt"');
  res.send(textContent);
});

// SSE Stream: /api/v1/dashboard/events
const sseClients = new Set();
app.get('/api/v1/dashboard/events', (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.flushHeaders();

  sseClients.add(res);
  res.write(`data: ${JSON.stringify({ type: 'CONNECTED', timestamp: Date.now() })}\n\n`);

  req.on('close', () => {
    sseClients.delete(res);
  });
});

function broadcastSse({ event = 'tick', data = {} }) {
  const payload = `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
  for (const client of sseClients) {
    try {
      client.write(payload);
    } catch {
      sseClients.delete(client);
    }
  }
}

// =============================================================================
// 6. MÁY CHỦ HTTP & WEBSOCKET ENGINE
// =============================================================================

const server = http.createServer(app);
const wss = new WebSocketServer({ server, path: '/ws/live-stream' });

export function broadcastWs(messageObj) {
  const raw = JSON.stringify(messageObj);
  wss.clients.forEach(client => {
    if (client.readyState === 1 /* OPEN */) {
      try {
        client.send(raw);
      } catch {
        // bỏ qua socket ngắt kết nối
      }
    }
  });
}

wss.on('connection', (ws) => {
  ws.send(JSON.stringify({
    type: 'CONNECTED',
    serverTime: new Date().toISOString()
  }));

  ws.send(JSON.stringify({
    type: 'TELEMETRY_AND_AI_TICK',
    cameras: getCameras(),
    timestamp: Date.now()
  }));
});

// Vòng lặp bắn Telemetry định kỳ
const telemetryInterval = setInterval(() => {
  broadcastWs({
    type: 'TELEMETRY_AND_AI_TICK',
    cameras: getCameras(),
    timestamp: Date.now()
  });
}, 300);

process.on('SIGTERM', () => {
  clearInterval(telemetryInterval);
  server.close();
});
process.on('SIGINT', () => {
  clearInterval(telemetryInterval);
  server.close();
});

if (process.env.NODE_ENV !== 'test') {
  server.listen(PORT, () => {
    console.log(`====================================================`);
    console.log(` CYBERGUARD AI · SOC v2.1 BACKEND RUNNING ON :${PORT}`);
    console.log(` Web App:   http://localhost:${PORT}/dashboard/`);
    console.log(` REST:      http://localhost:${PORT}/api/soc/overview`);
    console.log(` Camera In: http://localhost:${PORT}/api/v1/cameras/:id/stream`);
    console.log(` MJPEG Out: http://localhost:${PORT}/api/v1/cameras/:id/stream`);
    console.log(` Snapshot:  http://localhost:${PORT}/api/v1/cameras/:id/snapshot`);
    console.log(` Ingest:    http://localhost:${PORT}/api/v1/incidents`);
    console.log(` AI Target: ${AI_INFERENCE_URL}`);
    console.log(` WS:        ws://localhost:${PORT}/ws/live-stream`);
    console.log(`====================================================`);
  });
}

export { app, server };
