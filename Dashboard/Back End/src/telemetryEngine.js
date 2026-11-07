/**
 * CYBERGUARD AI · SOC v2.1 — REAL-TIME TELEMETRY ENGINE
 * Tính toán động các chỉ số mạng và rủi ro thời gian thực
 */

let systemState = {
  baseLatency: 42,
  baseDownloadMbps: 9744.0,
  baseUploadMbps: 4824.2,
  activeNodes: 43,
  camerasOnline: 40,
  camerasTotal: 43,
  packetLossPercent: 0.00,
  nvrStoragePercent: 82,
  poeLoadWatts: 410,
  threatScore: 12,
  threatLevel: 'LOW',
  status: 'SAFE'
};

export function getTelemetryOverview(activeThreatCount = 4, criticalThreatCount = 1) {
  // Biến thiên tự nhiên nhẹ để tạo cảm giác hệ thống sống (live network jitter)
  const jitterLatency = Math.floor(systemState.baseLatency + (Math.random() * 4 - 2));
  const jitterDownload = parseFloat((systemState.baseDownloadMbps + (Math.random() * 30 - 15)).toFixed(1));
  const jitterUpload = parseFloat((systemState.baseUploadMbps + (Math.random() * 16 - 8)).toFixed(1));
  const jitterPoe = Math.floor(systemState.poeLoadWatts + (Math.random() * 6 - 3));

  // Tự động tính toán Threat Level dựa trên threatScore
  let calculatedLevel = 'LOW';
  let calculatedStatus = 'SAFE';

  if (systemState.threatScore > 75) {
    calculatedLevel = 'CRITICAL';
    calculatedStatus = 'SEVERE';
  } else if (systemState.threatScore > 50) {
    calculatedLevel = 'HIGH';
    calculatedStatus = 'ELEVATED';
  } else if (systemState.threatScore > 25) {
    calculatedLevel = 'MEDIUM';
    calculatedStatus = 'GUARDED';
  }

  return {
    threatLevel: calculatedLevel,
    threatScore: systemState.threatScore,
    status: calculatedStatus,
    timestampUtc: new Date().toISOString(),
    metrics: {
      latencyMs: Math.max(20, jitterLatency),
      downloadMbps: jitterDownload,
      uploadMbps: jitterUpload,
      activeNodes: systemState.activeNodes,
      camerasOnline: systemState.camerasOnline,
      camerasTotal: systemState.camerasTotal,
      packetLossPercent: systemState.packetLossPercent,
      openThreats: activeThreatCount,
      criticalThreats: criticalThreatCount,
      nvrStoragePercent: systemState.nvrStoragePercent,
      poeLoadWatts: jitterPoe
    }
  };
}

export function updateThreatScore(newScore) {
  systemState.threatScore = Math.max(0, Math.min(100, newScore));
}
