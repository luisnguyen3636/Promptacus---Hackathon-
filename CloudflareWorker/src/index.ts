/**
 * Cloudflare Worker Main Entrypoint & Edge Gateway Router.
 * CYBERGUARD SOC — PURE DISPLAY & KV STORAGE GATEWAY
 *
 * Unifies:
 * 1. React Frontend SPA via Cloudflare Workers Static Assets (env.ASSETS)
 * 2. Native WebSocket live stream broker (/ws/live-stream)
 * 3. Server JSON Ingestion into Cloudflare KV (/api/incidents, /api/v1/webhook, /api/v1/ai/detection, /api/ingest)
 * 4. Full REST backend APIs reading real data from Cloudflare KV (Overview, Cameras, PTZ, Incidents, Playback)
 * 5. Operational HITL Verification Gate (CD-04 & CD-05)
 * 6. Operator Authentication (/api/auth/login, /api/auth/logout, /api/auth/me)
 * 7. Persistent SOC Settings in Cloudflare KV (/api/settings)
 */

import type {
  Env,
  IHitlVerificationRequest,
  IServerIngestPayload,
  ISocSettings,
  IOperatorSession
} from "./types.ts";
import { D1IncidentVault } from "./db.ts";
import { getTelemetryOverview, updateThreatScoreFromAi } from "./telemetry.ts";
import {
  getCameras,
  loadCamerasFromKv,
  upsertCameraFromServerPayload,
  handlePtzCommand,
  removeCameraById
} from "./camera_manager.ts";
import {
  getRecentIncidents,
  loadIncidentsFromKv,
  getIncidentPlayback,
  ingestServerPayloadToKv
} from "./incident_manager.ts";
import { processHitlVerification, getAuditLogs, recordIncidentAuditLog } from "./hitl_dispatcher.ts";
import { handleWebSocketUpgrade, broadcastMessage } from "./websocket.ts";
import { isIpWhitelisted, isOriginWhitelisted, getCorsHeaders } from "./security.ts";

// In-memory fallback stores (synchronized with Cloudflare KV)
const sessionStore = new Map<string, IOperatorSession>();

let currentSettings: ISocSettings = {
  operatorId: "OP-VN-SOC-804",
  operatorName: "Trưởng Ca Trực SOC",
  shiftRotation: "Ca 1 · 06:00 - 14:00 UTC",
  liveStreamUrl: "https://means-brick-determined-send.trycloudflare.com/api/v1/cameras/LAPTOP_01/stream",
  criticalThreshold: 75,
  preBufferSeconds: 10,
  postBufferSeconds: 10,
  dispatchWebhook: "https://soc-dispatch.police.gov.vn/api/v1/alert",
  autoSirenOnCritical: true,
  updatedAt: new Date().toISOString()
};

async function loadSettingsFromKv(env: Env): Promise<ISocSettings> {
  if (env.LIVE_CAMERA_STREAM_URL && !currentSettings.liveStreamUrl) {
    currentSettings.liveStreamUrl = env.LIVE_CAMERA_STREAM_URL;
  }
  if (env.INCIDENT_CACHE) {
    try {
      const raw = await env.INCIDENT_CACHE.get("kv_settings");
      if (raw) {
        const parsed = JSON.parse(raw) as Partial<ISocSettings>;
        currentSettings = { ...currentSettings, ...parsed };
      }
    } catch (err) {
      console.warn("[Worker] Failed to read kv_settings:", err);
    }
  }
  return currentSettings;
}

async function saveSettingsToKv(settings: Partial<ISocSettings>, env: Env): Promise<ISocSettings> {
  currentSettings = {
    ...currentSettings,
    ...settings,
    updatedAt: new Date().toISOString()
  };
  if (env.INCIDENT_CACHE) {
    try {
      await env.INCIDENT_CACHE.put("kv_settings", JSON.stringify(currentSettings));
    } catch (err) {
      console.warn("[Worker] Failed to write kv_settings:", err);
    }
  }
  return currentSettings;
}

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);
    const path = url.pathname;
    const method = request.method;

    const cors = getCorsHeaders(request, env.ALLOWED_ORIGINS);

    const jsonResponse = (data: any, status = 200): Response => {
      return new Response(JSON.stringify(data, null, 2), {
        status,
        headers: {
          ...cors,
          "Content-Type": "application/json"
        }
      });
    };

    const errorResponse = (message: string, status = 400): Response => {
      return jsonResponse({ error: message, success: false }, status);
    };

    // -------------------------------------------------------------------------
    // 1. CORS Preflight & Origin Whitelist Gate
    // -------------------------------------------------------------------------
    if (method === "OPTIONS") {
      const origin = request.headers.get("Origin");
      if (origin && !isOriginWhitelisted(origin, env.ALLOWED_ORIGINS)) {
        return new Response(
          JSON.stringify({ error: "CORS_ORIGIN_NOT_ALLOWED", origin, success: false }),
          { status: 403, headers: { "Content-Type": "application/json" } }
        );
      }
      return new Response(null, { status: 204, headers: cors });
    }

    const clientIp =
      request.headers.get("cf-connecting-ip") ||
      request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ||
      "127.0.0.1";

    // -------------------------------------------------------------------------
    // 1.1 Client IP Whitelist Enforcement Gate [CD-05]
    // -------------------------------------------------------------------------
    const enforceIpWhitelist = env.ENFORCE_IP_WHITELIST === "true";
    if (path.startsWith("/api") && enforceIpWhitelist) {
      if (!isIpWhitelisted(clientIp, env.ALLOWED_IPS)) {
        ctx.waitUntil(
          recordIncidentAuditLog(
            "SECURITY_EVENT",
            clientIp,
            "SECURITY_IP_BLOCKED",
            { ip: clientIp, path, method, userAgent: request.headers.get("user-agent") },
            env
          )
        );
        return errorResponse("ACCESS_DENIED_IP_NOT_WHITELISTED", 403);
      }
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
        service: "Urban Safety SOC Pure Display & KV Gateway",
        environment: env.ENVIRONMENT || "production",
        kv_ready: Boolean(env.INCIDENT_CACHE),
        d1_database_ready: Boolean(env.DB),
        static_assets_ready: Boolean(env.ASSETS),
        timestamp: new Date().toISOString()
      });
    }

    // -------------------------------------------------------------------------
    // 4. Authentication Endpoints (/api/auth/login, /api/auth/logout, /api/auth/me)
    // -------------------------------------------------------------------------
    if (path === "/api/auth/login" && method === "POST") {
      try {
        const body = (await request.json().catch(() => ({}))) as {
          operatorId?: string;
          password?: string;
          accessCode?: string;
          operatorName?: string;
          shift?: string;
        };

        const operatorId = (body.operatorId || "").trim();
        const password = (body.password || body.accessCode || "").trim();

        if (!operatorId || !password) {
          return errorResponse("Vui lòng nhập đầy đủ Mã Vận hành viên (Operator ID) và Mật khẩu.", 401);
        }

        if (password.length < 4) {
          return errorResponse("Mật khẩu không hợp lệ (tối thiểu 4 ký tự).", 401);
        }

        const token = `soc_tok_${Date.now()}_${Math.random().toString(36).substring(2, 10)}`;
        const session: IOperatorSession = {
          token,
          operatorId,
          operatorName: body.operatorName?.trim() || `Operator ${operatorId}`,
          role: "SOC_DUTY_OPERATOR",
          shift: body.shift?.trim() || "Ca Trực Tác Chiến (Active)",
          loggedInAt: new Date().toISOString()
        };

        sessionStore.set(token, session);
        if (env.INCIDENT_CACHE) {
          await env.INCIDENT_CACHE.put(`kv_session:${token}`, JSON.stringify(session), {
            expirationTtl: 86400
          });
        }

        // Also update default operatorId in settings
        await saveSettingsToKv({ operatorId, operatorName: session.operatorName }, env);

        await recordIncidentAuditLog(
          "AUTH_SESSION",
          operatorId,
          "OPERATOR_LOGIN_SUCCESS",
          { ip: clientIp, operatorName: session.operatorName, shift: session.shift },
          env
        );

        return jsonResponse({
          success: true,
          session
        });
      } catch (err: any) {
        return errorResponse(err?.message || "Authentication failed", 400);
      }
    }

    if (path === "/api/auth/me" && method === "GET") {
      const authHeader = request.headers.get("Authorization") || "";
      const token = authHeader.replace(/^Bearer\s+/i, "").trim();
      if (!token) {
        return errorResponse("No session token provided", 401);
      }

      let session = sessionStore.get(token);
      if (!session && env.INCIDENT_CACHE) {
        const raw = await env.INCIDENT_CACHE.get(`kv_session:${token}`);
        if (raw) {
          session = JSON.parse(raw) as IOperatorSession;
          sessionStore.set(token, session);
        }
      }

      if (!session) {
        return errorResponse("Session expired or invalid", 401);
      }

      return jsonResponse({
        authenticated: true,
        session
      });
    }

    if (path === "/api/auth/logout" && method === "POST") {
      const authHeader = request.headers.get("Authorization") || "";
      const token = authHeader.replace(/^Bearer\s+/i, "").trim();
      if (token) {
        sessionStore.delete(token);
        if (env.INCIDENT_CACHE) {
          await env.INCIDENT_CACHE.delete(`kv_session:${token}`);
        }
      }
      return jsonResponse({ success: true, message: "Logged out" });
    }

    // -------------------------------------------------------------------------
    // 5. SOC Platform Settings Endpoints (/api/settings) — Persisted in KV
    // -------------------------------------------------------------------------
    if ((path === "/api/settings" || path === "/api/v1/settings") && method === "GET") {
      const settings = await loadSettingsFromKv(env);
      return jsonResponse({
        success: true,
        data: settings,
        settings,
        ...settings
      });
    }

    if ((path === "/api/settings" || path === "/api/v1/settings") && method === "POST") {
      try {
        const body = (await request.json().catch(() => ({}))) as Partial<ISocSettings>;
        const updated = await saveSettingsToKv(body, env);
        await recordIncidentAuditLog(
          "SYSTEM_SETTINGS",
          updated.operatorId || clientIp,
          "SETTINGS_UPDATED",
          updated,
          env
        );
        return jsonResponse({
          success: true,
          data: updated,
          settings: updated,
          ...updated
        });
      } catch (err: any) {
        return errorResponse(err?.message || "Failed to save settings", 400);
      }
    }

    // -------------------------------------------------------------------------
    // 6. SERVER JSON CONTINUOUS INGESTION -> CLOUDFLARE KV
    // Supports all ingestion endpoints without running any AI on the Worker
    // -------------------------------------------------------------------------
    if (
      (path === "/api/incidents" ||
        path === "/api/v1/incidents" ||
        path === "/api/v1/ai/detection" ||
        path === "/api/v1/ai/webhook" ||
        path === "/api/v1/webhook" ||
        path === "/api/v1/webhook/detection" ||
        path === "/api/v1/ingest" ||
        path === "/api/ingest" ||
        path === "/api/webhook" ||
        path === "/api/update") &&
      method === "POST"
    ) {
      try {
        const rawBody = await request.json();
        const payloads: IServerIngestPayload[] = Array.isArray(rawBody) ? rawBody : [rawBody];

        if (payloads.length === 0 || !payloads[0] || typeof payloads[0] !== "object") {
          return errorResponse("Invalid JSON payload", 400);
        }

        let lastIncident: any = null;
        let lastCamera: any = null;

        for (const payload of payloads) {
          // 1. Upsert camera device in KV ("kv_cameras") with real telemetry & bounding boxes
          lastCamera = await upsertCameraFromServerPayload(payload, env, clientIp);

          // 2. Store incident in KV ("kv_recent_incidents" & "incident:<id>") with PENDING_VERIFICATION
          lastIncident = await ingestServerPayloadToKv(payload, env, clientIp);

          // 3. Update global threat score from payload's threat_score
          const scoreVal =
            payload.threat_score !== undefined
              ? Number(payload.threat_score)
              : payload.nvidia_vlm_analysis?.threat_score !== undefined
              ? Number(payload.nvidia_vlm_analysis.threat_score)
              : lastIncident.threatScore ?? 0;
          updateThreatScoreFromAi(scoreVal);

          // 4. Record immutable audit log
          await recordIncidentAuditLog(
            lastIncident.id,
            clientIp,
            "SERVER_JSON_INGESTED_TO_KV",
            {
              camera_id: lastIncident.cameraId,
              location: lastIncident.location,
              action_type: lastIncident.actionType,
              severity: lastIncident.severity,
              threat_score: lastIncident.threatScore,
              frame_index: lastIncident.frameIndex
            },
            env
          );

          // 5. Also persist to D1 if bound
          if (env.DB) {
            try {
              const vault = new D1IncidentVault(env);
              await vault.insertIncident({
                id: lastIncident.id,
                timestamp: lastIncident.timestamp,
                camera_id: lastIncident.cameraId || "LAPTOP_01",
                location_name: lastIncident.location || "Khu Vực Giám Sát",
                latitude: 0,
                longitude: 0,
                engine_behavior: lastIncident.actionType || lastIncident.title,
                engine_threat_score: Number(lastIncident.threatScore || 0),
                ai_severity_score_10: Math.round(Number(lastIncident.threatScore || 0) * 100) / 10,
                false_positive_prob: 0,
                is_false_positive: 0,
                threat_verdict: lastIncident.severity,
                subject_features: JSON.stringify(lastIncident.actors || []),
                weapons_identified: JSON.stringify(lastIncident.visualCues || {}),
                victim_assessment: JSON.stringify({ human_count: lastIncident.humanCount || 0 }),
                dispatch_recommendation: JSON.stringify({
                  recommended_action: lastIncident.recommendedAction,
                  is_urgent: lastIncident.isUrgent
                }),
                investigation_summary: lastIncident.description || lastIncident.reasoning || "",
                evidence_clip_url: null,
                snapshot_url: lastIncident.fullImageBase64 || null,
                operator_status: "AWAITING_OPERATOR_VERIFICATION"
              });
            } catch (dbErr) {
              console.warn("[Worker] D1 insert warning:", dbErr);
            }
          }
        }

        // 6. Broadcast real-time update to all connected WebSocket clients
        broadcastMessage({
          type: "TELEMETRY_AND_AI_TICK",
          cameras: getCameras(),
          timestamp: Date.now()
        });

        if (lastIncident) {
          broadcastMessage({
            type: "NEW_INCIDENT",
            incident: lastIncident,
            timestamp: Date.now()
          });
        }

        return jsonResponse(
          {
            success: true,
            status: "STORED_IN_KV",
            operator_status: "AWAITING_OPERATOR_VERIFICATION",
            incident_id: lastIncident?.id,
            camera: lastCamera,
            incident: lastIncident,
            timestamp: new Date().toISOString()
          },
          201
        );
      } catch (err: any) {
        return errorResponse(`Failed to ingest server JSON: ${err?.message || err}`, 400);
      }
    }

    // -------------------------------------------------------------------------
    // 7. REST API: Dashboard & Telemetry (/api/soc/overview)
    // -------------------------------------------------------------------------
    if ((path === "/api/soc/overview" || path === "/api/v1/soc/overview") && method === "GET") {
      await loadCamerasFromKv(env);
      const incidents = await loadIncidentsFromKv(env);
      const activeThreats = incidents.filter((i) => i.status === "PENDING_VERIFICATION").length;
      const criticalThreats = incidents.filter(
        (i) => i.severity === "CRITICAL" && i.status === "PENDING_VERIFICATION"
      ).length;
      const overview = getTelemetryOverview(activeThreats, criticalThreats);
      return jsonResponse(overview);
    }

    // -------------------------------------------------------------------------
    // 8. REST API: Real Camera Fleet from KV (/api/devices/cameras, /api/cameras)
    // -------------------------------------------------------------------------
    if ((path === "/api/devices/cameras" || path === "/api/cameras") && method === "GET") {
      const cameras = await loadCamerasFromKv(env);
      return jsonResponse(cameras);
    }

    if (
      (path.startsWith("/api/devices/cameras/") || path.startsWith("/api/cameras/")) &&
      !path.endsWith("/ptz") &&
      !path.endsWith("/stream") &&
      method === "DELETE"
    ) {
      const cameraId = path
        .replace("/api/devices/cameras/", "")
        .replace("/api/cameras/", "")
        .trim();
      const removed = await removeCameraById(cameraId, env);
      return jsonResponse({ success: removed, cameraId });
    }

    // -------------------------------------------------------------------------
    // 8.1. REST API: Live Camera Video Stream Proxy (/api/v1/cameras/:id/stream & /api/cameras/:id/stream)
    // -------------------------------------------------------------------------
    if (
      (path.startsWith("/api/v1/cameras/") || path.startsWith("/api/cameras/")) &&
      path.endsWith("/stream") &&
      method === "GET"
    ) {
      const cameraId = path
        .replace("/api/v1/cameras/", "")
        .replace("/api/cameras/", "")
        .replace("/stream", "")
        .trim();

      const settings = await loadSettingsFromKv(env);
      const defaultUrl = "https://means-brick-determined-send.trycloudflare.com/api/v1/cameras/LAPTOP_01/stream";
      const targetStreamUrl = settings.liveStreamUrl || env.LIVE_CAMERA_STREAM_URL || defaultUrl;

      try {
        const streamResponse = await fetch(targetStreamUrl, {
          headers: {
            "User-Agent": "UrbanSafetySOC-Worker-Proxy/2.1",
            Accept: "*/*"
          }
        });

        if (!streamResponse.ok || !streamResponse.body) {
          return new Response(
            JSON.stringify({
              error: "CAMERA_STREAM_UNAVAILABLE",
              cameraId,
              targetStreamUrl,
              status: streamResponse.status,
              message: "Target camera stream unreachable or offline."
            }),
            {
              status: 502,
              headers: {
                ...cors,
                "Content-Type": "application/json"
              }
            }
          );
        }

        const contentType =
          streamResponse.headers.get("content-type") || "multipart/x-mixed-replace; boundary=frame";
        return new Response(streamResponse.body, {
          status: 200,
          headers: {
            ...cors,
            "Content-Type": contentType,
            "Cache-Control": "no-cache, no-store, must-revalidate",
            Connection: "keep-alive",
            "X-Stream-Source": targetStreamUrl
          }
        });
      } catch (err: any) {
        return new Response(
          JSON.stringify({
            error: "CAMERA_STREAM_FETCH_ERROR",
            cameraId,
            targetStreamUrl,
            message: err?.message || String(err)
          }),
          {
            status: 503,
            headers: {
              ...cors,
              "Content-Type": "application/json"
            }
          }
        );
      }
    }

    // -------------------------------------------------------------------------
    // 9. REST API: PTZ Camera Control (/api/cameras/:id/ptz)
    // -------------------------------------------------------------------------
    if (
      (path.startsWith("/api/cameras/") || path.startsWith("/api/devices/cameras/")) &&
      path.endsWith("/ptz") &&
      method === "POST"
    ) {
      const cameraId = path
        .replace("/api/devices/cameras/", "")
        .replace("/api/cameras/", "")
        .replace("/ptz", "")
        .trim();
      try {
        const body = (await request.json().catch(() => ({}))) as { action?: string; speed?: number };
        if (!body.action) {
          return errorResponse("Missing action in PTZ command payload.");
        }
        const result = await handlePtzCommand(cameraId, body.action, body.speed || 1, env);
        return jsonResponse(result);
      } catch (err: any) {
        return errorResponse(err?.message || "PTZ command failed", 400);
      }
    }

    // -------------------------------------------------------------------------
    // 10. REST API: Fetch Stored Incidents from KV (/api/get-incident, /api/incidents/recent, /api/incidents)
    // -------------------------------------------------------------------------
    if (
      (path === "/api/get-incident" ||
        path === "/api/get-incidents" ||
        path === "/api/v1/get-incident" ||
        path === "/api/v1/get-incidents" ||
        path === "/api/incidents/get-incident" ||
        path === "/api/incidents/get-incidents" ||
        path === "/api/incidents/recent" ||
        path === "/api/incidents" ||
        path === "/api/v1/incidents/recent" ||
        path === "/api/v1/incidents") &&
      method === "GET"
    ) {
      const incidents = await loadIncidentsFromKv(env);
      const isSingle =
        url.searchParams.get("format") === "single" || url.searchParams.get("latest") === "true";
      if (isSingle) {
        return jsonResponse(incidents[0] || null);
      }
      if (path.includes("get-incident")) {
        return jsonResponse({
          success: true,
          count: incidents.length,
          timestamp: new Date().toISOString(),
          incidents
        });
      }
      return jsonResponse(incidents);
    }

    // -------------------------------------------------------------------------
    // 11. REST API: Rolling Buffer Playback (/api/incidents/:id/playback)
    // -------------------------------------------------------------------------
    if (
      (path.startsWith("/api/incidents/") || path.startsWith("/api/v1/incidents/")) &&
      path.endsWith("/playback") &&
      method === "GET"
    ) {
      await loadIncidentsFromKv(env);
      const incidentId = path
        .replace("/api/v1/incidents/", "")
        .replace("/api/incidents/", "")
        .replace("/playback", "")
        .trim();
      const playback = getIncidentPlayback(incidentId);
      if (!playback) {
        return errorResponse(`Incident '${incidentId}' not found in playback buffer`, 404);
      }
      return jsonResponse(playback);
    }

    // -------------------------------------------------------------------------
    // 11.1. REST API: Serve Forensic Images from KV (/api/v1/incidents/:id/image.jpg, hand_crop.jpg, subject_crop.jpg)
    // -------------------------------------------------------------------------
    if (
      (path.startsWith("/api/v1/incidents/") || path.startsWith("/api/incidents/")) &&
      (path.endsWith("/image.jpg") || path.endsWith("/hand_crop.jpg") || path.endsWith("/subject_crop.jpg")) &&
      method === "GET"
    ) {
      const incidents = await loadIncidentsFromKv(env);
      const cleanPath = path.replace("/api/v1/incidents/", "").replace("/api/incidents/", "");
      const parts = cleanPath.split("/");
      const incidentId = parts[0];
      const fileType = parts[1];
      const inc = incidents.find((i) => i.id === incidentId || i.eventId === incidentId);
      if (!inc) {
        return errorResponse(`Incident '${incidentId}' not found in KV`, 404);
      }

      const rawB64 =
        fileType === "hand_crop.jpg"
          ? inc.handCropBase64 || inc.subjectCropBase64 || inc.fullImageBase64
          : fileType === "subject_crop.jpg"
          ? inc.subjectCropBase64 || inc.fullImageBase64
          : inc.fullImageBase64 || inc.subjectCropBase64;

      if (!rawB64) {
        return errorResponse(`Image '${fileType}' not available for incident '${incidentId}'`, 404);
      }

      const stripped = rawB64.replace(/^data:image\/\w+;base64,/, "");
      try {
        const binaryStr = atob(stripped);
        const bytes = new Uint8Array(binaryStr.length);
        for (let i = 0; i < binaryStr.length; i++) {
          bytes[i] = binaryStr.charCodeAt(i);
        }
        return new Response(bytes, {
          status: 200,
          headers: {
            ...cors,
            "Content-Type": "image/jpeg",
            "Cache-Control": "public, max-age=3600"
          }
        });
      } catch {
        return errorResponse("Invalid base64 image data in KV", 500);
      }
    }

    // -------------------------------------------------------------------------
    // 12. REST API: Operational HITL Verification Gate (/api/incidents/:id/verify)
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
    // 13. REST API: SOC Immutable Audit Logs (/api/soc/audit-logs & /api/soc/logs) [CD-05]
    // -------------------------------------------------------------------------
    if ((path === "/api/soc/audit-logs" || path === "/api/soc/logs") && method === "GET") {
      const logs = await getAuditLogs(env);
      return jsonResponse(logs);
    }

    // -------------------------------------------------------------------------
    // 14. Static Assets Fallback (Cloudflare Workers Static Assets)
    // -------------------------------------------------------------------------
    if (env.ASSETS) {
      return await env.ASSETS.fetch(request);
    }

    return errorResponse(`Route '${method} ${path}' not found on Urban Safety SOC Edge Worker.`, 404);
  }
};
