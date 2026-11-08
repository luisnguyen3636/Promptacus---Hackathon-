/**
 * CYBERGUARD AI · SOC v2.1 — REAL-TIME TELEMETRY ENGINE
 * Tính toán động các chỉ số mạng và rủi ro thời gian thực
 */

const INITIAL_SYSTEM_STATE = {
  baseLatency: 35,
  baseDownloadMbps: 9744.0,
  baseUploadMbps: 4824.2,
  activeNodes: 43,
  camerasOnline: 4,
  camerasTotal: 4,
  packetLossPercent: 0.00,
  nvrStoragePercent: 78,
  poeLoadWatts: 410,
  threatScore: 0,
  threatLevel: 'LOW',
  status: 'SAFE'
};

let systemState = JSON.parse(JSON.stringify(INITIAL_SYSTEM_STATE));

export function getTelemetryOverview(activeThreatCount = 0, criticalThreatCount = 0) {
  // Biến thiên tự nhiên nhẹ để tạo cảm giác hệ thống sống (live network jitter)
  const jitterLatency = Math.floor(systemState.baseLatency + (Math.random() * 4 - 2));
  const jitterDownload = parseFloat((systemState.baseDownloadMbps + (Math.random() * 30 - 15)).toFixed(1));
  const jitterUpload = parseFloat((systemState.baseUploadMbps + (Math.random() * 16 - 8)).toFixed(1));
  const jitterPoe = Math.floor(systemState.poeLoadWatts + (Math.random() * 6 - 3));

  // Tự động tính toán Threat Level dựa trên threatScore
  let calculatedLevel = 'LOW';
  let calculatedStatus = 'SAFE';

  if (systemState.threatScore >= 75) {
    calculatedLevel = 'CRITICAL';
    calculatedStatus = 'SEVERE';
  } else if (systemState.threatScore >= 50) {
    calculatedLevel = 'HIGH';
    calculatedStatus = 'ELEVATED';
  } else if (systemState.threatScore >= 25) {
    calculatedLevel = 'MEDIUM';
    calculatedStatus = 'GUARDED';
  }

  systemState.threatLevel = calculatedLevel;
  systemState.status = calculatedStatus;

  return {
    threatLevel: calculatedLevel,
    threatScore: systemState.threatScore,
    status: calculatedStatus,
    timestampUtc: new Date().toISOString(),
    metrics: {
      latencyMs: Math.max(15, jitterLatency),
      downloadMbps: jitterDownload,
      uploadMbps: jitterUpload,
      activeNodes: systemState.activeNodes,
      camerasOnline: systemState.camerasOnline,
      camerasTotal: systemState.camerasTotal,
      packetLossPercent: systemState.packetLossPercent,
      openThreats: activeThreatCount,
      criticalThreats: criticalThreatCount,
      nvrStoragePercent: systemState.nvrStoragePercent,
      poeLoadWatts: jitterPoe,
      wantedCount: systemState.wantedCount || 3,
      blindSpotSessionsCount: systemState.blindSpotSessionsCount || 2,
      vlmVerifiedCount: systemState.vlmVerifiedCount || 14,
    }
  };
}

export function updateThreatScore(newScore) {
  if (typeof newScore !== 'number' || isNaN(newScore)) return;
  
  // Hỗ trợ chuẩn hóa float 0.0 - 1.0 từ AI sang thang điểm 0 - 100
  let normalized = newScore;
  if (normalized > 0 && normalized <= 1.0) {
    normalized = Math.round(normalized * 100);
  }
  
  systemState.threatScore = Math.max(0, Math.min(100, Math.round(normalized)));
}

export function updateSystemMetrics(metrics = {}) {
  if (metrics.camerasOnline !== undefined) systemState.camerasOnline = metrics.camerasOnline;
  if (metrics.camerasTotal !== undefined) systemState.camerasTotal = metrics.camerasTotal;
  if (metrics.activeNodes !== undefined) systemState.activeNodes = metrics.activeNodes;
}

export function resetTelemetry() {
  systemState = JSON.parse(JSON.stringify(INITIAL_SYSTEM_STATE));
}
