/**
 * CYBERGUARD AI · SOC v2.1 — BACKEND CORE SERVER (PORT 8000)
 * Cung cấp REST APIs & Live WebSocket Stream thực tế
 */

import http from 'http';
import express from 'express';
import cors from 'cors';
import { WebSocketServer } from 'ws';

import { getTelemetryOverview } from './src/telemetryEngine.js';
import { getCameras, handlePtzCommand } from './src/cameraManager.js';
import { getRecentIncidents, getIncidentPlayback } from './src/incidentManager.js';
import { processHitlVerification, getAuditLogs } from './src/hitlDispatcher.js';

const app = express();
const PORT = process.env.PORT || 8000;

app.use(cors());
app.use(express.json());

// 1. API Dashboard & Telemetry
app.get('/api/soc/overview', (req, res) => {
  const incidents = getRecentIncidents();
  const activeThreats = incidents.filter(i => i.status === 'PENDING_VERIFICATION').length;
  const criticalThreats = incidents.filter(i => i.severity === 'CRITICAL' && i.status === 'PENDING_VERIFICATION').length;
  
  const overview = getTelemetryOverview(activeThreats, criticalThreats);
  res.json(overview);
});

// 2. API Danh sách Camera & AI Stream
app.get('/api/devices/cameras', (req, res) => {
  res.json(getCameras());
});

// 3. API Điều khiển Camera PTZ
app.post('/api/cameras/:id/ptz', (req, res) => {
  try {
    const { action, speed } = req.body;
    const result = handlePtzCommand(req.params.id, action, speed);
    res.json(result);
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

// 4. API Incident Feed & Recent Threats
app.get('/api/incidents/recent', (req, res) => {
  res.json(getRecentIncidents());
});

// 5. API Bằng chứng Playback từ Rolling Buffer
app.get('/api/incidents/:id/playback', (req, res) => {
  const evidence = getIncidentPlayback(req.params.id);
  if (!evidence) {
    return res.status(404).json({ error: 'Incident not found' });
  }
  res.json(evidence);
});

// 6. API Chốt chặn Xác thực Operational HITL (CD-04)
app.post('/api/incidents/:id/verify', (req, res) => {
  try {
    const { operatorId, decision, notes, verifiedAt } = req.body;
    const result = processHitlVerification({
      incidentId: req.params.id,
      operatorId,
      decision,
      notes,
      verifiedAt
    });
    res.json(result);
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

// 7. API Audit Log Kiểm toán
app.get('/api/soc/audit-logs', (req, res) => {
  res.json(getAuditLogs());
});

// Tạo máy chủ HTTP kết hợp WebSocket
const server = http.createServer(app);
const wss = new WebSocketServer({ server, path: '/ws/live-stream' });

wss.on('connection', (ws) => {
  console.log('[WS] Client connected to live SOC stream');

  // Gửi heartbeat ngay khi client kết nối
  ws.send(JSON.stringify({
    type: 'CONNECTED',
    serverTime: new Date().toISOString()
  }));

  // Vòng lặp bắn Bounding Box & Telemetry định kỳ
  const interval = setInterval(() => {
    if (ws.readyState === ws.OPEN) {
      ws.send(JSON.stringify({
        type: 'TELEMETRY_AND_AI_TICK',
        cameras: getCameras(),
        timestamp: Date.now()
      }));
    }
  }, 200);

  ws.on('close', () => {
    clearInterval(interval);
    console.log('[WS] Client disconnected');
  });
});

server.listen(PORT, () => {
  console.log(`====================================================`);
  console.log(` CYBERGUARD AI · SOC v2.1 BACKEND RUNNING ON :${PORT}`);
  console.log(` REST: http://localhost:${PORT}/api/soc/overview`);
  console.log(` WS:   ws://localhost:${PORT}/ws/live-stream`);
  console.log(`====================================================`);
});
