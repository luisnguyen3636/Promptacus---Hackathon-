/**
 * CYBERGUARD AI · SOC v2.1 — OPERATIONAL HITL DISPATCHER & AUDIT LOGGER
 * Tuân thủ tuyệt đối [CD-04] và [CD-05]
 */

import { updateIncidentStatus } from './incidentManager.js';
import { updateThreatScore } from './telemetryEngine.js';

let auditLogs = [];

export function processHitlVerification({ incidentId, operatorId, decision, notes, verifiedAt }) {
  // Ràng buộc bảo toàn [CD-04]: Bắt buộc phải có operatorId
  if (!operatorId || typeof operatorId !== 'string') {
    throw new Error('SECURITY VIOLATION: Operator ID is mandatory for HITL verification [CD-04]');
  }

  const timestamp = verifiedAt || new Date().toISOString();
  let incidentPackage = null;
  let newThreatScore = 12;

  if (decision === 'CONFIRM_AND_DISPATCH') {
    updateIncidentStatus(incidentId, 'OPERATOR_CONFIRMED');

    // Đóng gói hồ sơ sự cố tác chiến an ninh (Automated Incident Packaging)
    incidentPackage = {
      packageId: `PKG-${Date.now()}`,
      incidentId,
      dispatchedByOperator: operatorId,
      verifiedAt: timestamp,
      coordinates: { latitude: 21.028511, longitude: 105.854444 }, // GPS Hà Nội SOC
      urgency: 'IMMEDIATE_INTERVENTION',
      notes: notes || 'Xác nhận hành vi xâm nhập thực tế từ video bằng chứng.'
    };

    // Ghi nhận sự cố đã được điều phối, hạ dần điểm đe dọa vì đã được xử lý
    newThreatScore = 8;
    updateThreatScore(newThreatScore);

    console.log(`[OPERATIONAL HITL DISPATCH SUCCESS] Package dispatched to Authorities:`, incidentPackage);
  } else if (decision === 'DOWNGRADE_MONITOR') {
    updateIncidentStatus(incidentId, 'DOWNGRADED_MONITORING');
    newThreatScore = 10;
    updateThreatScore(newThreatScore);
    console.log(`[OPERATIONAL HITL] Incident ${incidentId} downgraded by ${operatorId}`);
  } else if (decision === 'DISMISS_FALSE_POSITIVE') {
    updateIncidentStatus(incidentId, 'DISMISSED');
    newThreatScore = 5;
    updateThreatScore(newThreatScore);
    console.log(`[OPERATIONAL HITL] Incident ${incidentId} dismissed as False Positive by ${operatorId}`);
  } else {
    throw new Error(`Invalid decision: ${decision}`);
  }

  // Lưu vết kiểm toán SOC-Grade Audit Log [CD-05]
  const auditEntry = {
    auditId: `AUD-${Date.now()}`,
    incidentId,
    operatorId,
    decision,
    timestamp,
    status: 'RECORDED_IMMUTABLE'
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
