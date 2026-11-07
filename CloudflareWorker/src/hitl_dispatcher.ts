/**
 * CYBERGUARD AI · SOC v2.1 — OPERATIONAL HITL DISPATCHER & AUDIT LOGGER (EDGE NATIVE)
 * Enforces dual Human-in-the-Loop directives [CD-04] and immutable SOC traceability [CD-05].
 */

import { updateIncidentStatus, getRecentIncidents } from "./incident_manager.ts";
import { updateThreatScore } from "./telemetry.ts";
import { D1IncidentVault } from "./db.ts";
import type { IHitlVerificationRequest, IHitlVerificationResponse, IIncidentDispatchPackage, Env } from "./types.ts";

let memoryAuditLogs: Array<{
  auditId: string;
  incidentId: string;
  operatorId?: string;
  actor?: string;
  decision?: string;
  action?: string;
  timestamp: string;
  status: string;
  details?: any;
}> = [];

export async function recordIncidentAuditLog(
  incidentId: string,
  actor: string,
  action: string,
  details: Record<string, any>,
  env?: Env
): Promise<{ auditId: string; timestamp: string }> {
  const auditId = `AUD-${Date.now()}`;
  const timestamp = new Date().toISOString();

  // In-memory audit entry
  const memEntry = {
    auditId,
    incidentId,
    operatorId: actor,
    actor,
    decision: action,
    action,
    timestamp,
    status: "RECORDED_IMMUTABLE",
    details
  };
  memoryAuditLogs.unshift(memEntry);

  // Sync to Cloudflare D1 audit_logs
  if (env && env.DB) {
    try {
      await env.DB.prepare(
        `INSERT INTO audit_logs (incident_id, action, actor, details, created_at)
         VALUES (?, ?, ?, ?, ?)`
      )
        .bind(
          incidentId,
          action,
          actor,
          typeof details === "string" ? details : JSON.stringify(details),
          timestamp
        )
        .run();
    } catch (e) {
      console.warn("[HITL Dispatcher] D1 recordIncidentAuditLog insert warning:", e);
    }
  }

  return { auditId, timestamp };
}

export async function processHitlVerification(
  req: IHitlVerificationRequest & { incidentId: string },
  env?: Env
): Promise<IHitlVerificationResponse> {
  const { incidentId, operatorId, decision, notes, verifiedAt } = req;

  // Security Gate [CD-04]: Operator ID is mandatory
  if (!operatorId || typeof operatorId !== "string" || !operatorId.trim()) {
    throw new Error("SECURITY VIOLATION: Operator ID is mandatory for HITL verification [CD-04]");
  }

  const timestamp = verifiedAt || new Date().toISOString();
  let incidentPackage: IIncidentDispatchPackage | null = null;
  let newThreatScore = 0;

  if (decision === "CONFIRM_AND_DISPATCH") {
    await updateIncidentStatus(incidentId, "OPERATOR_CONFIRMED", env);

    const targetIncident = getRecentIncidents().find((i) => i.id === incidentId);
    const rawDet = targetIncident?.rawDetection;

    // Automated Tactical Incident Packaging for authorities [CD-04 / Section 3.4]
    incidentPackage = {
      packageId: `PKG-${Date.now()}`,
      incidentId,
      dispatchedByOperator: operatorId,
      verifiedAt: timestamp,
      camera: {
        id: targetIncident?.cameraId || rawDet?.camera_id || rawDet?.camera?.camera_id || "UNKNOWN_CAMERA",
        name: targetIncident?.location || rawDet?.location || rawDet?.camera?.name || "Giám sát camera",
        zoneId: rawDet?.camera?.zone_id || "ZONE_SOC",
        address: targetIncident?.location || rawDet?.location || rawDet?.camera?.address || "Hiện trường vụ việc"
      },
      coordinates: {
        latitude: rawDet?.camera?.latitude || 0,
        longitude: rawDet?.camera?.longitude || 0
      },
      threatAssessment: {
        severity: targetIncident?.severity || "HIGH",
        threatScore: targetIncident?.threatScore || rawDet?.threat_score || rawDet?.detection?.threat_score || 0.94,
        reasoning: targetIncident?.reasoning || targetIncident?.vlmAnalysis || "Phát hiện mối đe dọa bất thường"
      },
      visualEvidence: {
        annotatedSnapshot: targetIncident?.cameraSnapshots?.eventPeakSnapshotUrl || targetIncident?.fullImageBase64 || null,
        subjectCrop: targetIncident?.subjects?.[0]?.crop_image_base64 || null,
        evidenceClipUrl: targetIncident?.playbackUrl || null
      },
      dispatchStatus: "DISPATCHED_TO_EMERGENCY_AUTHORITIES",
      urgency: "IMMEDIATE_INTERVENTION",
      notes: notes || "Xác nhận sự cố thực tế từ dữ liệu giám sát."
    };

    const remainingPending = getRecentIncidents().filter((i) => i.status === "PENDING_VERIFICATION");
    newThreatScore = remainingPending.length > 0 ? Math.round((remainingPending[0].threatScore || 0.5) * 100) : 0;
    updateThreatScore(newThreatScore);
  } else if (decision === "DOWNGRADE_MONITOR") {
    await updateIncidentStatus(incidentId, "DOWNGRADED_MONITORING", env);
    const remainingPending = getRecentIncidents().filter((i) => i.status === "PENDING_VERIFICATION");
    newThreatScore = remainingPending.length > 0 ? Math.round((remainingPending[0].threatScore || 0.25) * 100) : 0;
    updateThreatScore(newThreatScore);
  } else if (decision === "DISMISS_FALSE_POSITIVE") {
    await updateIncidentStatus(incidentId, "DISMISSED", env);
    const remainingPending = getRecentIncidents().filter((i) => i.status === "PENDING_VERIFICATION");
    newThreatScore = remainingPending.length > 0 ? Math.round((remainingPending[0].threatScore || 0) * 100) : 0;
    updateThreatScore(newThreatScore);
  } else {
    throw new Error(`Invalid decision: ${decision}`);
  }

  // Immutable Audit Log Record [CD-05]
  const auditEntry = {
    auditId: `AUD-${Date.now()}`,
    incidentId,
    operatorId,
    decision,
    timestamp,
    status: "RECORDED_IMMUTABLE"
  };
  memoryAuditLogs.push(auditEntry);

  // Sync to Cloudflare D1 if available
  if (env && env.DB) {
    try {
      const vault = new D1IncidentVault(env);
      await vault.updateOperatorVerification(incidentId, {
        action: decision,
        operator_id: operatorId,
        operator_notes: notes
      });
    } catch (e) {
      console.warn("[HITL Dispatcher] D1 audit sync warning:", e);
    }
  }

  return {
    success: true,
    decision,
    auditEntry,
    incidentPackage,
    systemThreatScore: newThreatScore
  };
}

export async function getAuditLogs(env?: Env): Promise<any[]> {
  if (env && env.DB) {
    try {
      const { results } = await env.DB.prepare(
        "SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 50"
      ).all();
      if (results && results.length > 0) {
        return results;
      }
    } catch (e) {
      console.warn("[HITL Dispatcher] D1 getAuditLogs warning:", e);
    }
  }
  return memoryAuditLogs;
}
