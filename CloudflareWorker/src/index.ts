/**
 * Cloudflare Worker Main Entrypoint & Edge Gateway Router.
 * CYBERGUARD AI · URBAN SAFETY AI-SOC v2.1
 * 
 * Unifies:
 * 1. React Frontend SPA via Cloudflare Workers Static Assets (env.ASSETS)
 * 2. Native WebSocket live stream broker (/ws/live-stream)
 * 3. Real AI Detection Webhook Ingestion (/api/v1/ai/detection & /api/v1/webhook)
 * 4. Full REST backend APIs (Telemetry, Cameras, PTZ, Incidents, Evidence Playback)
 * 5. Operational HITL Verification Gate (CD-04 & CD-05)
 * 6. Workers AI Forensic Evaluator (DeepSeek / Llama 3.2 Vision)
 * 7. Cloudflare D1 SQL Incident Vault & Immutable Audit Logs
 */

import {
  Env,
  EvaluationRequestPayload,
  IncidentRecord,
  IHitlVerificationRequest,
  IAIRealDetectionPayload,
  IGenericIncidentPostPayload,
  IIncidentPostResponse
} from "./types";
import { WorkersAIEvaluator } from "./ai_evaluator";
import { D1IncidentVault } from "./db";
import { getTelemetryOverview, updateThreatScoreFromAi } from "./telemetry";
import { getCameras, handlePtzCommand, upsertCameraFromAiDetection } from "./camera_manager";
import {
  getRecentIncidents,
  getIncidentPlayback,
  createIncidentFromAiDetection,
  ingestGenericIncident
} from "./incident_manager";
import { processHitlVerification, getAuditLogs, recordIncidentAuditLog } from "./hitl_dispatcher";
import { handleWebSocketUpgrade, broadcastMessage } from "./websocket";

// Standard CORS headers for open edge communication
function corsHeaders(): HeadersInit {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Correlation-ID",
    "Content-Type": "application/json"
  };
}

function jsonResponse(data: any, status = 200): Response {
  return new Response(JSON.stringify(data, null, 2), {
    status,
    headers: corsHeaders()
  });
}

function errorResponse(message: string, status = 400): Response {
  return jsonResponse({ error: message, success: false }, status);
}

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);
    const path = url.pathname;
    const method = request.method;

    // -------------------------------------------------------------------------
    // 1. CORS Preflight
    // -------------------------------------------------------------------------
    if (method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders() });
    }

    // -------------------------------------------------------------------------
    // 2. WebSocket Upgrade Route (/ws/live-stream)
    // -------------------------------------------------------------------------
    if (
      (path === "/ws/live-stream" || path === "/ws") &&
      request.headers.get("Upgrade")?.toLowerCase() === "websocket"
    ) {
      return handleWebSocketUpgrade(request);
    }

    // -------------------------------------------------------------------------
    // 3. Edge Gateway Healthcheck (/api/v1/health)
    // -------------------------------------------------------------------------
    if (path === "/api/v1/health" && method === "GET") {
      return jsonResponse({
        status: "ONLINE",
        service: "Urban Safety AI-SOC Cloudflare Edge Gateway & Dashboard",
        environment: env.ENVIRONMENT || "production",
        workers_ai_ready: Boolean(env.AI),
        d1_database_ready: Boolean(env.DB),
        static_assets_ready: Boolean(env.ASSETS),
        timestamp: new Date().toISOString()
      });
    }

    // -------------------------------------------------------------------------
    // 4. REST API: Real AI Detection Ingestion Webhook (AI/Human -> Edge SOC)
    // Ingests authentic detections from YOLO11-Pose / WebhookDispatcher
    // -------------------------------------------------------------------------
    if (
      (path === "/api/v1/ai/detection" ||
        path === "/api/v1/ai/webhook" ||
        path === "/api/v1/webhook" ||
        path === "/api/v1/webhook/detection") &&
      method === "POST"
    ) {
      try {
        const payload = (await request.json()) as IAIRealDetectionPayload;

        if (!payload.event_id || !payload.camera || !payload.detection) {
          return errorResponse(
            "Invalid AI detection payload. Required: event_id, camera, detection.",
            422
          );
        }

        // 1. Upsert camera in dynamic fleet with normalized bounding boxes & snapshot
        const cameraDevice = upsertCameraFromAiDetection(
          payload.camera,
          payload.detection.subjects || [],
          payload.detection.full_image?.width || 640,
          payload.detection.full_image?.height || 480,
          payload.detection.full_image?.image_base64
        );

        // 2. Create and index the incident (status = PENDING_VERIFICATION)
        const incidentItem = createIncidentFromAiDetection(payload);

        // 3. Update global threat score dynamically from real AI threat score
        updateThreatScoreFromAi(payload.detection.threat_score);

        // 4. Persist to Cloudflare D1 SQL if available
        if (env.DB) {
          try {
            const vault = new D1IncidentVault(env);
            const primarySubject = payload.detection.subjects?.[0];

            await vault.insertIncident({
              id: payload.event_id,
              timestamp: payload.timestamp || new Date().toISOString(),
              camera_id: payload.camera.camera_id,
              location_name: payload.camera.address || payload.camera.name || "Default Camera Zone",
              latitude: Number(payload.camera.latitude || 0.0),
              longitude: Number(payload.camera.longitude || 0.0),
              engine_behavior: payload.detection.primary_action,
              engine_threat_score: Number(payload.detection.threat_score || 0.0),
              ai_severity_score_10: Math.round(Number(payload.detection.threat_score || 0.0) * 100) / 10,
              false_positive_prob: 0.04,
              is_false_positive: 0,
              threat_verdict: payload.detection.threat_level,
              subject_features: JSON.stringify(payload.detection.subjects || []),
              weapons_identified: JSON.stringify(payload.detection.weapon || {}),
              victim_assessment: JSON.stringify({ human_count: payload.audit?.human_count || 1 }),
              dispatch_recommendation: JSON.stringify({
                priority: payload.detection.is_urgent ? "IMMEDIATE_RESPONSE" : "ROUTINE",
                action: payload.detection.reasoning
              }),
              investigation_summary: payload.detection.reasoning,
              evidence_clip_url: null,
              snapshot_url: primarySubject?.crop_image_base64 || payload.detection.full_image?.image_base64 || null,
              operator_status: "AWAITING_OPERATOR_VERIFICATION" // Mandatory Operational HITL gate [CD-04]
            });

            await vault.logAudit(payload.event_id, "AI_DETECTION_INGESTED", "AI_PIPELINE", {
              camera_id: payload.camera.camera_id,
              primary_action: payload.detection.primary_action,
              threat_score: payload.detection.threat_score,
              sha256_hash: payload.detection.full_image?.sha256_hash
            });
          } catch (dbErr) {
            console.warn("[Worker] D1 persistence warning for AI detection:", dbErr);
          }
        }

        // 5. Broadcast real-time update to all connected WebSocket clients
        broadcastMessage({
          type: "TELEMETRY_AND_AI_TICK",
          cameras: getCameras(),
          timestamp: Date.now()
        });

        broadcastMessage({
          type: "NEW_INCIDENT",
          incident: incidentItem,
          timestamp: Date.now()
        });

        return jsonResponse(
          {
            success: true,
            event_id: payload.event_id,
            operator_status: "AWAITING_OPERATOR_VERIFICATION",
            camera: cameraDevice,
            incident: incidentItem,
            message: "Real AI detection successfully ingested and broadcasted to SOC"
          },
          201
        );
      } catch (err: any) {
        return errorResponse(`Failed to process AI detection: ${err?.message || err}`, 400);
      }
    }

    // -------------------------------------------------------------------------
    // 5. REST API: Dashboard & Telemetry (/api/soc/overview)
    // -------------------------------------------------------------------------
    if ((path === "/api/soc/overview" || path === "/api/v1/soc/overview") && method === "GET") {
      const incidents = getRecentIncidents();
      const activeThreats = incidents.filter(i => i.status === "PENDING_VERIFICATION").length;
      const criticalThreats = incidents.filter(i => i.severity === "CRITICAL" && i.status === "PENDING_VERIFICATION").length;
      const overview = getTelemetryOverview(activeThreats, criticalThreats);
      return jsonResponse(overview);
    }

    // -------------------------------------------------------------------------
    // 6. REST API: Camera Fleet & Live Tracking (/api/devices/cameras)
    // -------------------------------------------------------------------------
    if (path === "/api/devices/cameras" && method === "GET") {
      return jsonResponse(getCameras());
    }

    // -------------------------------------------------------------------------
    // 7. REST API: PTZ Camera Control (/api/cameras/:id/ptz)
    // -------------------------------------------------------------------------
    if (path.startsWith("/api/cameras/") && path.endsWith("/ptz") && method === "POST") {
      const cameraId = path.replace("/api/cameras/", "").replace("/ptz", "").trim();
      try {
        const body = (await request.json().catch(() => ({}))) as { action?: string; speed?: number };
        if (!body.action) {
          return errorResponse("Missing action in PTZ command payload.");
        }
        const result = handlePtzCommand(cameraId, body.action, body.speed || 1);
        return jsonResponse(result);
      } catch (err: any) {
        return errorResponse(err?.message || "PTZ command failed", 400);
      }
    }

    // -------------------------------------------------------------------------
    // 8. REST API: Post Incident & Immutable Log Recording (/api/incidents) [CD-05]
    // -------------------------------------------------------------------------
    if ((path === "/api/incidents" || path === "/api/v1/incidents") && method === "POST") {
      try {
        const body = (await request.json()) as Record<string, any>;
        if (!body || typeof body !== "object") {
          return errorResponse("Missing or invalid JSON body for incident payload", 400);
        }

        const clientIp =
          request.headers.get("cf-connecting-ip") ||
          request.headers.get("x-forwarded-for") ||
          "127.0.0.1";

        // If payload includes AI detection camera details, dynamically upsert camera fleet
        if (body.camera && body.detection) {
          upsertCameraFromAiDetection(
            body.camera,
            body.detection.subjects || [],
            body.detection.full_image?.width || 640,
            body.detection.full_image?.height || 480,
            body.detection.full_image?.image_base64
          );
        }

        // Ingest into incident vault (with mandatory PENDING_VERIFICATION state [CD-04])
        const incident = ingestGenericIncident(body, clientIp);

        // Update threat score if provided or based on severity
        if (body.detection?.threat_score !== undefined) {
          updateThreatScoreFromAi(Number(body.detection.threat_score));
        } else if (incident.severity === "CRITICAL") {
          updateThreatScoreFromAi(0.95);
        } else if (incident.severity === "HIGH") {
          updateThreatScoreFromAi(0.75);
        }

        // Record immutable audit log entry [CD-05]
        const auditResult = await recordIncidentAuditLog(
          incident.id,
          clientIp,
          "INCIDENT_REPORT_INGESTED",
          {
            title: incident.title,
            severity: incident.severity,
            cameraId: incident.cameraId,
            category: incident.category,
            details: body
          },
          env
        );

        // Broadcast real-time event to connected SOC operators
        broadcastMessage({
          type: "NEW_INCIDENT",
          incident,
          timestamp: Date.now()
        });

        const responsePayload: IIncidentPostResponse = {
          success: true,
          message: "Incident received and logged successfully",
          log_id: auditResult.auditId,
          incident_id: incident.id,
          timestamp: auditResult.timestamp,
          status: "RECORDED_AS_LOG",
          operator_status: "AWAITING_OPERATOR_VERIFICATION",
          audit: {
            action: "INCIDENT_REPORT_INGESTED",
            actor: clientIp,
            storage: "D1_AUDIT_LOG_AND_MEMORY"
          },
          incident
        };

        return jsonResponse(responsePayload, 201);
      } catch (err: any) {
        return errorResponse(err?.message || "Failed to log incident", 400);
      }
    }

    // -------------------------------------------------------------------------
    // 9. REST API: Recent Incidents (/api/incidents/recent)
    // -------------------------------------------------------------------------
    if (path === "/api/incidents/recent" && method === "GET") {
      return jsonResponse(getRecentIncidents());
    }

    // -------------------------------------------------------------------------
    // 9. REST API: Rolling Buffer Playback (/api/incidents/:id/playback)
    // -------------------------------------------------------------------------
    if (path.startsWith("/api/incidents/") && path.endsWith("/playback") && method === "GET") {
      const incidentId = path.replace("/api/incidents/", "").replace("/playback", "").trim();
      const playback = getIncidentPlayback(incidentId);
      if (!playback) {
        return errorResponse(`Incident '${incidentId}' not found in playback buffer`, 404);
      }
      return jsonResponse(playback);
    }

    // -------------------------------------------------------------------------
    // 10. REST API: Operational HITL Verification Gate (/api/incidents/:id/verify)
    // Mandatory Human Operator Verification [CD-04] & Immutable Traceability [CD-05]
    // -------------------------------------------------------------------------
    if (
      (path.startsWith("/api/incidents/") || path.startsWith("/api/v1/incidents/")) &&
      path.endsWith("/verify") &&
      method === "POST"
    ) {
      const incidentId = path
        .replace("/api/v1/incidents/", "")
        .replace("/api/incidents/", "")
        .replace("/verify", "")
        .trim();

      try {
        const body = (await request.json()) as IHitlVerificationRequest;
        const result = await processHitlVerification(
          {
            incidentId,
            operatorId: body.operatorId,
            decision: body.decision,
            notes: body.notes,
            verifiedAt: body.verifiedAt
          },
          env
        );

        // Broadcast updated state to all connected operators
        broadcastMessage({
          type: "TELEMETRY_AND_AI_TICK",
          cameras: getCameras(),
          timestamp: Date.now()
        });

        return jsonResponse(result);
      } catch (err: any) {
        return errorResponse(err?.message || "Operational HITL verification failed", 400);
      }
    }

    // -------------------------------------------------------------------------
    // 11. REST API: SOC Immutable Audit Logs (/api/soc/audit-logs) [CD-05]
    // -------------------------------------------------------------------------
    if (path === "/api/soc/audit-logs" && method === "GET") {
      const logs = await getAuditLogs(env);
      return jsonResponse(logs);
    }

    // -------------------------------------------------------------------------
    // 12. REST API: Workers AI Evaluation & Local Ingestion (/api/v1/engine/evaluate)
    // -------------------------------------------------------------------------
    if (path === "/api/v1/engine/evaluate" && method === "POST") {
      const payload = (await request.json()) as EvaluationRequestPayload;

      if (!payload.camera_id || !payload.engine_behavior || payload.telemetry === undefined) {
        return errorResponse("Missing required fields (camera_id, engine_behavior, telemetry).");
      }

      const incidentId = payload.incident_id || `INC_${Date.now()}_${Math.random().toString(36).substring(2, 8).toUpperCase()}`;
      const aiEvaluator = new WorkersAIEvaluator(env);
      const vault = new D1IncidentVault(env);

      // Run Workers AI Forensic Evaluation
      const evaluation = await aiEvaluator.evaluate(payload);

      // Prepare D1 record
      const incidentRecord: IncidentRecord = {
        id: incidentId,
        timestamp: payload.timestamp || new Date().toISOString(),
        camera_id: payload.camera_id,
        location_name: payload.location_name || "Unspecified Location",
        latitude: Number(payload.latitude || 0.0),
        longitude: Number(payload.longitude || 0.0),
        engine_behavior: payload.engine_behavior,
        engine_threat_score: Number(payload.engine_threat_score || 0.0),
        ai_severity_score_10: evaluation.severity_score_10,
        false_positive_prob: evaluation.false_positive_probability,
        is_false_positive: evaluation.is_false_positive ? 1 : 0,
        threat_verdict: evaluation.threat_verdict,
        subject_features: JSON.stringify(evaluation.subject_features),
        weapons_identified: JSON.stringify(evaluation.weapons_identified),
        victim_assessment: JSON.stringify(evaluation.victim_assessment),
        dispatch_recommendation: JSON.stringify(evaluation.dispatch_recommendation),
        investigation_summary: evaluation.investigation_summary,
        evidence_clip_url: payload.evidence_clip_url || null,
        snapshot_url: payload.snapshot_url || null,
        operator_status: "AWAITING_OPERATOR_VERIFICATION" // Mandatory Operational HITL gate
      };

      // Persist to Cloudflare D1
      if (env.DB) {
        await vault.insertIncident(incidentRecord);
      }

      return jsonResponse({
        success: true,
        incident_id: incidentId,
        operator_status: "AWAITING_OPERATOR_VERIFICATION",
        evaluation,
        persisted_to_d1: Boolean(env.DB),
        timestamp: new Date().toISOString()
      }, 201);
    }

    // -------------------------------------------------------------------------
    // 13. REST API: D1 Incidents Query (/api/v1/incidents)
    // -------------------------------------------------------------------------
    if (path === "/api/v1/incidents" && method === "GET") {
      const cameraId = url.searchParams.get("camera_id") || undefined;
      const status = url.searchParams.get("status") || undefined;
      const minSeverity = url.searchParams.has("min_severity") ? Number(url.searchParams.get("min_severity")) : undefined;
      const limit = Number(url.searchParams.get("limit") || 20);
      const offset = Number(url.searchParams.get("offset") || 0);

      if (!env.DB) {
        return jsonResponse({ incidents: getRecentIncidents(), count: getRecentIncidents().length, note: "Memory buffer" });
      }

      const vault = new D1IncidentVault(env);
      const incidents = await vault.getIncidents({
        camera_id: cameraId,
        operator_status: status,
        min_severity: minSeverity,
        limit,
        offset
      });

      const formatted = incidents.map(inc => ({
        ...inc,
        is_false_positive: Boolean(inc.is_false_positive),
        subject_features: JSON.parse(inc.subject_features || "{}"),
        weapons_identified: JSON.parse(inc.weapons_identified || "{}"),
        victim_assessment: JSON.parse(inc.victim_assessment || "{}"),
        dispatch_recommendation: JSON.parse(inc.dispatch_recommendation || "{}")
      }));

      return jsonResponse({
        incidents: formatted,
        count: formatted.length,
        limit,
        offset
      });
    }

    // -------------------------------------------------------------------------
    // 14. REST API: D1 Incident Detail (/api/v1/incidents/:id)
    // -------------------------------------------------------------------------
    if (path.startsWith("/api/v1/incidents/") && !path.endsWith("/verify") && method === "GET") {
      const id = path.replace("/api/v1/incidents/", "").trim();
      if (!env.DB) {
        const found = getRecentIncidents().find(i => i.id === id);
        if (found) return jsonResponse(found);
        return errorResponse("Incident record not found", 404);
      }

      const vault = new D1IncidentVault(env);
      const incident = await vault.getIncidentById(id);
      if (!incident) {
        return errorResponse("Incident record not found", 404);
      }

      return jsonResponse({
        ...incident,
        is_false_positive: Boolean(incident.is_false_positive),
        subject_features: JSON.parse(incident.subject_features || "{}"),
        weapons_identified: JSON.parse(incident.weapons_identified || "{}"),
        victim_assessment: JSON.parse(incident.victim_assessment || "{}"),
        dispatch_recommendation: JSON.parse(incident.dispatch_recommendation || "{}")
      });
    }

    // -------------------------------------------------------------------------
    // 15. Static Assets Fallback (Cloudflare Workers Static Assets)
    // Delivers the compiled React Dashboard SPA (HTML, CSS, JS, Assets)
    // -------------------------------------------------------------------------
    if (env.ASSETS) {
      return await env.ASSETS.fetch(request);
    }

    // If neither an API route nor assets binding matched
    return errorResponse(`Route '${method} ${path}' not found on Urban Safety SOC Edge Worker.`, 404);
  }
};
