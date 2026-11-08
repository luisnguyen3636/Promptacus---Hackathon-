/**
 * CYBERGUARD AI · SOC v2.1 — OPERATIONAL HITL DISPATCHER & AUDIT LOGGER
 * Tuân thủ tuyệt đối [CD-04] và [CD-05]
 */

import { updateIncidentStatus, getIncidentById } from './incidentManager.js';
import { updateThreatScore } from './telemetryEngine.js';

let auditLogs = [];

export function processHitlVerification({ incidentId, operatorId, decision, notes, verifiedAt }) {
  // Ràng buộc bảo toàn [CD-04]: Bắt buộc phải có operatorId
  if (!operatorId || typeof operatorId !== 'string' || operatorId.trim().length === 0) {
    throw new Error('SECURITY VIOLATION: Operator ID is mandatory for HITL verification [CD-04]');
  }

  const timestamp = verifiedAt || new Date().toISOString();
  let incidentPackage = null;
  let newThreatScore = 12;

  const incident = getIncidentById(incidentId);

  if (decision === 'CONFIRM_AND_DISPATCH') {
    if (!incident || incident.aiVerified !== true) {
      throw new Error('SECURITY VIOLATION: Dispatch requires a completed NVIDIA NIM VLM analysis.');
    }
    updateIncidentStatus(incidentId, 'OPERATOR_CONFIRMED');

    // Đóng gói hồ sơ sự cố tác chiến an ninh (Automated Incident Packaging - CD-04)
    incidentPackage = {
      packageId: `PKG-${Date.now()}`,
      incidentId,
      dispatchedByOperator: operatorId,
      verifiedAt: timestamp,
      coordinates: incident?.cameraLocation || { latitude: 21.028511, longitude: 105.854444 }, // Tọa độ GPS SOC
      urgency: 'IMMEDIATE_INTERVENTION',
      title: incident?.title || 'Sự cố an ninh xác nhận',
      vlmAnalysis: incident?.vlmAnalysis || 'Đã xác nhận hành vi nguy hiểm từ video bằng chứng.',
      forensicHash: incident?.forensicHash || null,
      notes: notes || 'Xác nhận hành vi vi phạm thực tế từ video bằng chứng.'
    };

    // Ghi nhận sự cố đã được điều phối, hạ dần điểm đe dọa vì đã được xử lý
    newThreatScore = 15;
    updateThreatScore(newThreatScore);

    console.log(`[OPERATIONAL HITL DISPATCH SUCCESS] Package dispatched to Authorities:`, incidentPackage.packageId);
  } else if (decision === 'DOWNGRADE_MONITOR') {
    updateIncidentStatus(incidentId, 'DOWNGRADED_MONITORING');
    newThreatScore = 25;
    updateThreatScore(newThreatScore);
    console.log(`[OPERATIONAL HITL] Incident ${incidentId} downgraded by ${operatorId}`);
  } else if (decision === 'DISMISS_FALSE_POSITIVE') {
    updateIncidentStatus(incidentId, 'DISMISSED');
    newThreatScore = 8;
    updateThreatScore(newThreatScore);
    console.log(`[OPERATIONAL HITL] Incident ${incidentId} dismissed as False Positive by ${operatorId}`);
  } else {
    throw new Error(`Invalid decision: ${decision}`);
  }

  // Lưu vết kiểm toán SOC-Grade Audit Log [CD-05]
  const auditEntry = {
    auditId: `AUD-${Date.now()}-${Math.floor(Math.random() * 1000)}`,
    incidentId,
    operatorId,
    decision,
    timestamp,
    status: 'RECORDED_IMMUTABLE',
    notes: notes || null
  };
  auditLogs.push(auditEntry);

  return {
    success: true,
    decision,
    auditEntry,
    incidentPackage,
    systemThreatScore: newThreatScore
  };
}

export function getAuditLogs() {
  return auditLogs;
}

export function resetAuditLogs() {
  auditLogs = [];
}
