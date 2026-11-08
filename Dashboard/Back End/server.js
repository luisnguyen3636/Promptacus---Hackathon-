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
  updateCameraThreat,
  pingCamera,
} from './src/cameraManager.js';
import { getRecentIncidents, getIncidentPlayback, addIncidentFromDetect, getIncidentById } from './src/incidentManager.js';
import { processHitlVerification, getAuditLogs } from './src/hitlDispatcher.js';
import {
  getWantedList,
  getWantedPersonById,
  createWantedPerson,
  updateWantedPerson,
  deleteWantedPerson,
  stampEvidenceToWanted,
} from './src/wantedManager.js';
import {
  getBlindSpotSessions,
  getBlindSpotSessionById,
  correlateCrossCameraSuspect,
  verifyBlindSpotLink,
} from './src/blindSpotManager.js';
import { socDebugLogger } from './src/debugLogger.js';

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

const processedNvidiaEvents = new Set();

function getCompletedNvidiaAnalysis(payload) {
  const analysis = payload?.nvidia_vlm_analysis ||
    payload?.detection?.nvidia_vlm_analysis ||
    payload?.vlm_analysis ||
    payload?.ai_analysis;
  if (!analysis) return null;

  const validSources = ['nvidia_nim_vlm', 'openrouter_vlm', 'local_vlm_engine', 'vlm_engine'];
  const source = String(analysis.source || '');
  const status = String(analysis.analysis_status || analysis.status || '');
  const isSourceValid = validSources.includes(source) || Boolean(analysis.evaluated_subjects) || source.endsWith('_vlm');
  const isStatusValid = ['completed', 'local_only', 'processed'].includes(status) || !status;

  if (!isSourceValid || !isStatusValid) {
    return null;
  }
  return analysis;
}

function isNvidiaAlertEligible(analysis) {
  if (!analysis) return false;
  const action = String(analysis.action_type || analysis.primary_action || '').trim().toUpperCase();
  const severity = String(analysis.severity || analysis.threat_level || '').trim().toUpperCase();
  const hasSuppression = Boolean(
    analysis.false_positive_suppressed ||
    analysis.anti_false_positive_audit?.false_positive_suppressed ||
    (Array.isArray(analysis.evaluated_subjects) && analysis.evaluated_subjects.some(subject => subject?.false_positive_suppressed))
  );
  const reasoning = String(
    analysis.reasoning ||
    analysis.description ||
    analysis.reasoning_summary ||
    (Array.isArray(analysis.evaluated_subjects) && analysis.evaluated_subjects[0]?.reasoning_summary) ||
    ''
  ).trim();
  return !hasSuppression && Boolean(action && reasoning) &&
    !['NORMAL', 'UNKNOWN'].includes(action) && ['HIGH', 'CRITICAL'].includes(severity);
}

function publishNvidiaVerifiedAlert(payload) {
  const analysis = getCompletedNvidiaAnalysis(payload);
  if (!isNvidiaAlertEligible(analysis)) return false;

  const action = String(analysis.action_type || analysis.primary_action || '').trim().toUpperCase();
  const severity = String(analysis.severity || analysis.threat_level || '').trim().toUpperCase();
  const reasoning = String(
    analysis.reasoning ||
    analysis.description ||
    analysis.reasoning_summary ||
    (Array.isArray(analysis.evaluated_subjects) && analysis.evaluated_subjects[0]?.reasoning_summary) ||
    ''
  ).trim();

  const cameraId = String(payload.camera_id || payload.cameraId || payload.camera?.camera_id || 'CAM_01');
  const eventId = String(
    payload.event_id ||
    `EVT-NVIDIA-${cameraId}-${payload.frame_index ?? analysis.frame_id ?? analysis.timestamp ?? Date.now()}`
  );
  if (processedNvidiaEvents.has(eventId)) return false;
  processedNvidiaEvents.add(eventId);
  if (processedNvidiaEvents.size > 5000) {
    processedNvidiaEvents.delete(processedNvidiaEvents.values().next().value);
  }

  const confidenceValue = Number(analysis.confidence);
  const confidence = Number.isFinite(confidenceValue)
    ? (confidenceValue > 1 ? confidenceValue / 100 : confidenceValue)
    : undefined;
  const cameraName = payload.camera_name || payload.camera?.name || `Camera ${cameraId}`;
  const provider = analysis.provider || (String(analysis.source || '').includes('openrouter') ? 'OpenRouter' : 'NVIDIA NIM');
  const alert = {
    hasAlert: true,
    type: action,
    severity,
    message: reasoning,
    confidence,
    timestamp: Date.now(),
    aiProvider: provider,
    model: analysis.model || null,
    nvidiaVlmAnalysis: analysis
  };

  registerOrUpdateCamera({ id: cameraId, name: cameraName });
  if (Array.isArray(payload.humans)) updateCameraBoundingBoxes(cameraId, payload.humans);
  setCameraAlert(cameraId, alert);

  const incident = addIncidentFromDetect({
    event_id: eventId,
    primary_action: action,
    severity,
    threat_score: analysis.threat_score,
    confidence,
    camera_id: cameraId,
    camera_name: cameraName,
    reasoning,
    vlmAnalysis: reasoning,
    nvidia_vlm_analysis: analysis,
    aiProvider: provider,
    subjects: payload.humans || analysis.actors || []
  });
  updateThreatScore(incident.threatScore);

  try {
    const logFile = path.join(LOGS_DIR, `incident_${Date.now()}_${cameraId}.json`);
    fs.writeFileSync(logFile, JSON.stringify(incident, null, 2), 'utf-8');
  } catch {
    // Incident remains available in memory if audit-log storage is unavailable.
  }

  broadcastWs({ type: 'INCIDENT_ALERT', incident, timestamp: Date.now() });
  broadcastWs({ type: 'TELEMETRY_AND_AI_TICK', cameras: getCameras(), timestamp: Date.now() });
  return true;
}

async function consumeAiInferenceEvents(signal) {
  const eventsUrl = `${AI_INFERENCE_URL}/api/v1/dashboard/events`;
  while (!signal.aborted) {
    try {
      const response = await fetch(eventsUrl, { signal, headers: { Accept: 'text/event-stream' } });
      if (!response.ok || !response.body) throw new Error(`AI event stream returned ${response.status}`);

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      while (!signal.aborted) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n');
        let boundary = buffer.indexOf('\n\n');
        while (boundary >= 0) {
          const block = buffer.slice(0, boundary);
          buffer = buffer.slice(boundary + 2);
          const data = block.split('\n')
            .filter(line => line.startsWith('data:'))
            .map(line => line.slice(5).trimStart())
            .join('\n');
          if (data) {
            try {
              const message = JSON.parse(data);
              if (message.type === 'incident' && message.payload) {
                publishNvidiaVerifiedAlert(message.payload);
              }
            } catch {
              // Ignore malformed SSE events and keep the camera pipeline running.
            }
          }
          boundary = buffer.indexOf('\n\n');
        }
      }
    } catch {
      if (signal.aborted) break;
    }
    if (!signal.aborted) await new Promise(resolve => setTimeout(resolve, 1500));
  }
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

    const nvidiaAnalysis = aiAnalysis?.nvidia_vlm_analysis;
    const detectedAction = String(nvidiaAnalysis?.action_type || primaryAction).toUpperCase();
    const alertCreated = aiAnalysis
      ? publishNvidiaVerifiedAlert({
          ...aiAnalysis,
          camera_id: cameraId,
          camera_name: cameraName || cam?.name,
          timestamp_ms: timestampMs
        })
      : false;

    // 3. Luôn cập nhật Bounding Box từ kết quả AI phát hiện đối tượng để bám vết liên tục trên Dashboard
    if (aiAnalysis?.humans && Array.isArray(aiAnalysis.humans)) {
      updateCameraBoundingBoxes(cameraId, aiAnalysis.humans);
    }

    // 4. Nếu AI phát hiện hành vi nguy cấp: Gắn nhãn aiAlert, cập nhật Bounding Box, đẩy Incident & Lưu Log
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
      threat_level: nvidiaAnalysis?.severity || aiAnalysis?.highest_threat || "LOW",
      alert_status: alertCreated ? "NVIDIA_VERIFIED" : (primaryAction === 'NORMAL' ? "NO_CANDIDATE" : "AWAITING_NVIDIA_VLM"),
      vlm_analysis_status: aiAnalysis?.vlm_analysis_status || nvidiaAnalysis?.analysis_status || "unavailable",
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

// 3.8 DANH SÁCH TRUY NÃ & ĐÓNG DẤU BẰNG CHỨNG (WANTED CRIMINALS & FORENSIC STAMPING)
app.get(['/api/v1/wanted', '/api/wanted'], (req, res) => {
  const list = getWantedList();
  res.json({ success: true, count: list.length, data: list });
});

app.get(['/api/v1/wanted/:id', '/api/wanted/:id'], (req, res) => {
  const person = getWantedPersonById(req.params.id);
  if (!person) {
    return res.status(404).json({ success: false, error: 'Wanted person not found' });
  }
  res.json({ success: true, data: person });
});

app.post(['/api/v1/wanted', '/api/wanted'], (req, res) => {
  try {
    const person = createWantedPerson(req.body);
    broadcastWs({ type: 'WANTED_CREATED', data: person });
    res.status(201).json({ success: true, data: person });
  } catch (err) {
    res.status(400).json({ success: false, error: err.message });
  }
});

app.put(['/api/v1/wanted/:id', '/api/wanted/:id'], (req, res) => {
  try {
    const updated = updateWantedPerson(req.params.id, req.body);
    if (!updated) {
      return res.status(404).json({ success: false, error: 'Wanted person not found' });
    }
    broadcastWs({ type: 'WANTED_UPDATED', data: updated });
    res.json({ success: true, data: updated });
  } catch (err) {
    res.status(400).json({ success: false, error: err.message });
  }
});

app.delete(['/api/v1/wanted/:id', '/api/wanted/:id'], (req, res) => {
  const ok = deleteWantedPerson(req.params.id);
  if (!ok) {
    return res.status(404).json({ success: false, error: 'Wanted person not found' });
  }
  broadcastWs({ type: 'WANTED_DELETED', id: req.params.id });
  res.json({ success: true, message: `Deleted wanted person ${req.params.id}` });
});

app.post(['/api/v1/wanted/:id/evidence', '/api/wanted/:id/evidence'], (req, res) => {
  try {
    const stamped = stampEvidenceToWanted(req.params.id, req.body);
    if (!stamped) {
      return res.status(404).json({ success: false, error: 'Wanted person not found' });
    }
    broadcastWs({ type: 'WANTED_EVIDENCE_STAMPED', data: stamped });
    res.json({ success: true, ...stamped });
  } catch (err) {
    res.status(400).json({ success: false, error: err.message });
  }
});

// 3.9 SUY LUẬN VÙNG MÙ ĐA CAMERA (MULTI-CAMERA BLIND-SPOT REASONING)
app.get(['/api/v1/blind-spot/sessions', '/api/blind-spot/sessions'], (req, res) => {
  const sessions = getBlindSpotSessions();
  res.json({ success: true, count: sessions.length, data: sessions });
});

app.post(['/api/v1/blind-spot/correlate', '/api/blind-spot/correlate'], (req, res) => {
  try {
    const session = correlateCrossCameraSuspect(req.body);
    broadcastWs({ type: 'BLIND_SPOT_CORRELATION', data: session });
    res.json({ success: true, data: session });
  } catch (err) {
    res.status(400).json({ success: false, error: err.message });
  }
});

app.post(['/api/v1/blind-spot/verify', '/api/blind-spot/verify'], (req, res) => {
  try {
    const { sessionId, decision, operatorId } = req.body || {};
    const session = verifyBlindSpotLink(sessionId, decision, operatorId);
    if (!session) {
      return res.status(404).json({ success: false, error: 'Blind spot session not found' });
    }
    broadcastWs({ type: 'BLIND_SPOT_VERIFIED', data: session });
    res.json({ success: true, data: session });
  } catch (err) {
    res.status(400).json({ success: false, error: err.message });
  }
});

// 3.10 CAMERA MANAGER: PING & CHUẨN ĐOÁN CAMERA
app.post(['/api/devices/cameras/:id/ping', '/api/v1/cameras/:id/ping'], (req, res) => {
  try {
    const diag = pingCamera(req.params.id);
    res.json({ success: true, data: diag });
  } catch (err) {
    res.status(404).json({ success: false, error: err.message });
  }
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

    // External webhook payloads cannot assert NVIDIA provenance. The trusted path
    // for completed analysis is the private AI server SSE bridge above.
    const incident = addIncidentFromDetect({
      ...payload,
      status: 'AI_VERIFICATION_PENDING',
      reasoning: '',
      vlmAnalysis: '',
      nvidia_vlm_analysis: null
    });

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

    // 4. This endpoint records untrusted candidates only. NVIDIA results arrive
    // through the AI server event bridge and are applied by publishNvidiaVerifiedAlert.

    // 6. Ghi log sự cố ra file audit log trên đĩa
    try {
      const logFile = path.join(LOGS_DIR, `webhook_${Date.now()}_${incident.id}.json`);
      fs.writeFileSync(logFile, JSON.stringify(incident, null, 2), 'utf-8');
    } catch {
      // bỏ qua lỗi disk
    }

    broadcastWs({
      type: 'TELEMETRY_AND_AI_TICK',
      cameras: getCameras(),
      timestamp: Date.now()
    });

    res.status(200).json({
      success: true,
      status: 'CANDIDATE_PENDING_NVIDIA_VERIFICATION',
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

const aiInferenceBridgeAbort = new AbortController();

process.on('SIGTERM', () => {
  aiInferenceBridgeAbort.abort();
  clearInterval(telemetryInterval);
  server.close();
});
process.on('SIGINT', () => {
  aiInferenceBridgeAbort.abort();
  clearInterval(telemetryInterval);
  server.close();
});

if (process.env.NODE_ENV !== 'test') {
  server.listen(PORT, () => {
    void consumeAiInferenceEvents(aiInferenceBridgeAbort.signal);
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
