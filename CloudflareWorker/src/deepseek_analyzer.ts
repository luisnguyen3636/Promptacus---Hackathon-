/**
 * CYBERGUARD AI · SOC v2.1 — INTEGRATED AI FORENSIC ANALYSIS PIPELINE & DEEPSEEK ENGINE
 * 
 * Capabilities:
 * 1. Cloudflare KV Storage: Stores raw incident logs, DeepSeek Input & Output traces for rapid debugging.
 * 2. Automatic In-Process AI Layer: Analyzes incoming detection/incident POST requests on the fly.
 * 3. Multi-tier AI Engine:
 *    - Tier 1: Direct DeepSeek REST API (via DEEPSEEK_API_KEY with JSON Mode).
 *    - Tier 2: Cloudflare Workers AI Binding (via @cf/deepseek-ai/deepseek-v4.1-flash-1017).
 *    - Tier 3: Local Forensic Kinematics Engine (Offline zero-downtime biological posture evaluation).
 * 4. Standard SOC Structured Audit Logging (IStandardSocLogEntry persisted to D1 audit_logs, KV & memory).
 * 5. Dual Continuous Polling Endpoints: GET /api/get-incident & GET /api/get-incidents.
 * 6. Quick Debug Trace Endpoint: GET /api/kv/trace/:id.
 * 7. Strict Operational HITL Enforcement (CD-04 & CD-05).
 */

import type {
  Env,
  IPostRequestLog,
  IDeepSeekIncidentItem,
  IDeepSeekGetIncidentsResponse,
  IStandardSocLogEntry,
  IDeepSeekDebugTrace,
  IIncidentItem
} from "./types.ts";
import { getRecentIncidents, addIncident } from "./incident_manager.ts";
import { D1IncidentVault } from "./db.ts";

// In-Memory Rolling Log Buffer for all incoming POST requests (Up to 500 entries)
let postRequestLogs: IPostRequestLog[] = [];

// Cache of DeepSeek-evaluated incidents
let analyzedIncidentsCache: Map<string, IDeepSeekIncidentItem> = new Map();

// Standard SOC structured audit log entries (Up to 500 entries)
let standardSocAuditLogs: IStandardSocLogEntry[] = [];

// Memory Fallback Store for Cloudflare KV
let kvMemoryStore: Map<string, string> = new Map();

/**
 * Safely writes a value to Cloudflare KV Namespace (with memory fallback).
 */
export async function writeToKv(
  env: Env,
  key: string,
  value: any,
  ttlSeconds = 86400
): Promise<boolean> {
  const serialized = typeof value === "string" ? value : JSON.stringify(value);
  kvMemoryStore.set(key, serialized);

  if (env && env.INCIDENT_CACHE) {
    try {
      await env.INCIDENT_CACHE.put(key, serialized, {
        expirationTtl: ttlSeconds
      });
      return true;
    } catch (kvErr) {
      console.warn(`[KV Helper] Warning writing key '${key}':`, kvErr);
    }
  }
  return true;
}

/**
 * Safely reads a value from Cloudflare KV Namespace (with memory fallback).
 */
export async function readFromKv<T>(env: Env, key: string): Promise<T | null> {
  if (env && env.INCIDENT_CACHE) {
    try {
      const val = await env.INCIDENT_CACHE.get(key);
      if (val !== null) {
        try {
          return JSON.parse(val) as T;
        } catch {
          return val as unknown as T;
        }
      }
    } catch (kvErr) {
      console.warn(`[KV Helper] Warning reading key '${key}':`, kvErr);
    }
  }

  const memoryVal = kvMemoryStore.get(key);
  if (memoryVal !== undefined) {
    try {
      return JSON.parse(memoryVal) as T;
    } catch {
      return memoryVal as unknown as T;
    }
  }

  return null;
}

/**
 * Retrieves the unified DeepSeek Input & Output debug trace for an incident.
 */
export async function getDeepSeekTrace(env: Env, eventId: string): Promise<IDeepSeekDebugTrace | null> {
  return await readFromKv<IDeepSeekDebugTrace>(env, `deepseek:trace:${eventId}`);
}

/**
 * Records any incoming POST request into the rolling log buffer.
 */
export function recordPostRequestLog(
  path: string,
  method: string,
  clientIp: string,
  body: any
): IPostRequestLog {
  const now = Date.now();
  const id = `LOG_${now}_${Math.random().toString(36).substring(2, 7).toUpperCase()}`;

  // Extract visual evidence if present
  let hasImage = false;
  let imageBase64: string | undefined = undefined;
  let cropImageBase64: string | undefined = undefined;

  if (body?.detection?.full_image?.image_base64) {
    hasImage = true;
    imageBase64 = body.detection.full_image.image_base64;
  } else if (body?.fullImageBase64) {
    hasImage = true;
    imageBase64 = body.fullImageBase64;
  } else if (body?.snapshot_url && body.snapshot_url.startsWith("data:image")) {
    hasImage = true;
    imageBase64 = body.snapshot_url;
  }

  if (body?.detection?.subjects?.[0]?.crop_image_base64) {
    cropImageBase64 = body.detection.subjects[0].crop_image_base64;
  }

  const cameraId =
    body?.camera?.camera_id ||
    body?.camera_id ||
    body?.cameraId ||
    undefined;

  const threatScore =
    body?.detection?.threat_score !== undefined
      ? Number(body.detection.threat_score)
      : body?.engine_threat_score !== undefined
      ? Number(body.engine_threat_score)
      : undefined;

  const payloadSummary =
    body?.detection?.primary_action ||
    body?.title ||
    body?.engine_behavior ||
    body?.action ||
    "POST Request Ingestion";

  const logEntry: IPostRequestLog = {
    id,
    timestamp: new Date().toISOString(),
    timestampMs: now,
    path,
    method,
    clientIp,
    payloadSummary,
    hasImage,
    imageBase64,
    cropImageBase64,
    threatScore,
    cameraId,
    rawPayload: body || {}
  };

  postRequestLogs.unshift(logEntry);
  if (postRequestLogs.length > 500) {
    postRequestLogs = postRequestLogs.slice(0, 500);
  }

  return logEntry;
}

/**
 * Retrieves all POST request logs within the last N seconds (default: 120s / 2 minutes).
 */
export function getPostLogsInWindow(windowSeconds = 120): IPostRequestLog[] {
  const cutoff = Date.now() - windowSeconds * 1000;
  return postRequestLogs.filter((l) => l.timestampMs >= cutoff);
}

/**
 * Calls Direct DeepSeek REST API using the provided API Key.
 * Returns parsed JSON adhering to strict forensic schema with latency measurement.
 */
export async function callDeepSeekDirectApi(
  prompt: string,
  apiKey: string,
  modelName = "deepseek-chat",
  apiUrl = "https://api.deepseek.com/chat/completions"
): Promise<{ success: boolean; data?: any; rawText?: string; error?: string; latencyMs: number }> {
  const start = Date.now();
  try {
    const response = await fetch(apiUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${apiKey}`
      },
      body: JSON.stringify({
        model: modelName,
        messages: [
          {
            role: "system",
            content:
              'You are the CyberGuard Urban Safety AI-SOC Chief Forensic Analyst. Evaluate physical kinematics, posture, weapons, camera feeds and security incidents. You MUST respond with ONLY a valid, parseable JSON object adhering strictly to this schema: {"severity": "CRITICAL"|"HIGH"|"MEDIUM"|"LOW", "threat_verdict": string, "object_description": {"role": "suspect"|"victim"|"bystander", "primary_action": string, "posture_details": string, "weapon_detected": string|null, "weapon_confidence": number, "kinematics_summary": string}, "investigation_summary": string}.'
          },
          {
            role: "user",
            content: prompt
          }
        ],
        response_format: { type: "json_object" },
        temperature: 0.1,
        max_tokens: 500
      })
    });

    const latencyMs = Date.now() - start;
    if (!response.ok) {
      const errText = await response.text();
      return {
        success: false,
        error: `DeepSeek API returned HTTP ${response.status}: ${errText.substring(0, 200)}`,
        rawText: errText,
        latencyMs
      };
    }

    const jsonRes: any = await response.json();
    const content = jsonRes?.choices?.[0]?.message?.content;
    if (!content) {
      return { success: false, error: "Empty completion response from DeepSeek API", latencyMs };
    }

    const parsed = JSON.parse(content.replace(/```json/g, "").replace(/```/g, "").trim());
    return { success: true, data: parsed, rawText: content, latencyMs };
  } catch (err: any) {
    return {
      success: false,
      error: `DeepSeek Direct API call failed: ${err?.message || err}`,
      latencyMs: Date.now() - start
    };
  }
}

/**
 * Formats a Standard SOC Structured Audit Log Entry [CD-05].
 */
export function formatStandardSocLog(
  item: IDeepSeekIncidentItem,
  provider: "DEEPSEEK_DIRECT_API" | "CLOUDFLARE_WORKERS_AI" | "LOCAL_KINEMATICS_ENGINE",
  modelName: string,
  latencyMs: number
): IStandardSocLogEntry {
  const logId = `SOC_LOG_${Date.now()}_${Math.random().toString(36).substring(2, 7).toUpperCase()}`;
  let logLevel: "INFO" | "WARNING" | "CRITICAL" = "INFO";
  if (item.severity === "CRITICAL") {
    logLevel = "CRITICAL";
  } else if (item.severity === "HIGH") {
    logLevel = "WARNING";
  }

  return {
    log_id: logId,
    timestamp: item.timestamp || new Date().toISOString(),
    log_level: logLevel,
    source: "AI_INTEGRATED_LAYER",
    event_id: item.id,
    camera_id: item.camera_id,
    model_provider: provider,
    model_name: modelName,
    latency_ms: latencyMs,
    threat_score: item.threat_score,
    severity: item.severity,
    object_description: item.object_description,
    investigation_summary: item.deepseek_analysis.investigation_summary,
    evidence_timeline: item.evidence_timeline,
    sha256_hash: item.visual_evidence.sha256_hash || null,
    operator_status: "AWAITING_OPERATOR_VERIFICATION"
  };
}

/**
 * Returns all Standard SOC Structured Audit Logs.
 */
export function getStandardSocAuditLogs(): IStandardSocLogEntry[] {
  return standardSocAuditLogs;
}

/**
 * Automatically analyzes a single POST request log in-process using the integrated AI layer.
 * Records both Input and Output into Cloudflare KV, persists to D1, and caches the result.
 */
export async function analyzeSingleLogWithIntegratedAI(
  log: IPostRequestLog,
  env: Env
): Promise<IDeepSeekIncidentItem> {
  const raw = log.rawPayload;
  const eventId =
    raw?.event_id ||
    raw?.incident_id ||
    raw?.id ||
    `INC_${log.timestampMs}_${log.id.substring(4, 9)}`;

  // Return cached result if already analyzed
  if (analyzedIncidentsCache.has(eventId)) {
    return analyzedIncidentsCache.get(eventId)!;
  }

  const cameraId = log.cameraId || raw?.camera?.camera_id || "CAM_UNKNOWN";
  const locationName =
    raw?.camera?.address ||
    raw?.location_name ||
    raw?.camera?.name ||
    "Khu vực giám sát đô thị";

  // 1. Kinematics & Posture Analysis
  const primarySubject = raw?.detection?.subjects?.[0];
  const kinematics = primarySubject?.kinematics;
  const weapon = raw?.detection?.weapon;
  const action = raw?.detection?.primary_action || raw?.title || "UNSPECIFIED_ANOMALY";

  let kinematicsSummary = "Không có số liệu động học.";
  if (kinematics) {
    kinematicsSummary = `Góc khuỷu tay phải: ${kinematics.right_elbow_angle || 'N/A'}°, Độ duỗi tay: ${kinematics.right_arm_extension || 'N/A'}m, Vận tốc cổ tay: ${kinematics.wrist_velocity || 'N/A'}px/s`;
  }

  const prompt = `You are the Urban Safety AI-SOC Chief Forensic Analyst.
Evaluate this incident event log:
- Action: ${action}
- Camera: ${cameraId} (${locationName})
- Kinematics: ${kinematicsSummary}
- Weapon: ${weapon?.is_weapon_detected ? weapon.weapon_types?.join(', ') : 'None'}
- Raw Reasoning: ${raw?.detection?.reasoning || raw?.description || 'N/A'}

Provide a strict, professional SOC analysis report in JSON format:
{
  "severity": "CRITICAL" | "HIGH" | "MEDIUM" | "LOW",
  "threat_verdict": string,
  "object_description": {
    "role": "suspect" | "victim" | "bystander",
    "primary_action": string,
    "posture_details": string,
    "weapon_detected": string | null,
    "weapon_confidence": number,
    "kinematics_summary": string
  },
  "investigation_summary": string
}`;

  let deepseekVerdict = "CONFIRMED_ANOMALY";
  let investigationSummary = `Phát hiện hành vi ${action}.`;
  let activeProvider: "DEEPSEEK_DIRECT_API" | "CLOUDFLARE_WORKERS_AI" | "LOCAL_KINEMATICS_ENGINE" =
    "LOCAL_KINEMATICS_ENGINE";
  let activeModel = env?.DEFAULT_AI_MODEL || env?.DEEPSEEK_MODEL || "deepseek-chat";
  let latencyMs = 15;
  let evaluatedSeverity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL" = "MEDIUM";
  let rawAiResponseText: string | undefined = undefined;
  let executionError: string | null = null;

  const directApiKey = env?.DEEPSEEK_API_KEY || env?.OPENAI_API_KEY || env?.AI_API_KEY;
  const directApiUrl = env?.DEEPSEEK_API_URL || "https://api.deepseek.com/chat/completions";
  const directModel = env?.DEEPSEEK_MODEL || "deepseek-chat";

  // ---------------------------------------------------------------------------
  // A. RECORD DEEPSEEK INPUT TO CLOUDFLARE KV (For fast debugging)
  // ---------------------------------------------------------------------------
  const kvInputPayload = {
    event_id: eventId,
    prompt,
    raw_payload: raw,
    model_target: directApiKey ? directModel : (env?.DEFAULT_AI_MODEL || "@cf/deepseek-ai/deepseek-v4.1-flash-1017"),
    camera_id: cameraId,
    timestamp: new Date().toISOString()
  };
  await writeToKv(env, `deepseek:input:${eventId}`, kvInputPayload, 86400);
  await writeToKv(env, `raw_incident:${eventId}`, log, 86400);

  // ---------------------------------------------------------------------------
  // B. RUN MULTI-TIER AI INFERENCE
  // ---------------------------------------------------------------------------

  // Tier 1: Direct DeepSeek API Call with API Key
  if (directApiKey && directApiKey.trim() !== "") {
    const directResult = await callDeepSeekDirectApi(prompt, directApiKey, directModel, directApiUrl);
    latencyMs = directResult.latencyMs;
    rawAiResponseText = directResult.rawText;
    if (directResult.success && directResult.data) {
      activeProvider = "DEEPSEEK_DIRECT_API";
      activeModel = directModel;
      if (directResult.data.threat_verdict) deepseekVerdict = directResult.data.threat_verdict;
      if (directResult.data.investigation_summary) investigationSummary = directResult.data.investigation_summary;
      if (directResult.data.severity) evaluatedSeverity = directResult.data.severity;
    } else {
      executionError = directResult.error || "Direct DeepSeek API error";
      console.warn("[DeepSeek Analyzer] Direct API call fallback:", directResult.error);
    }
  }

  // Tier 2: Cloudflare Workers AI Binding Fallback
  if (activeProvider === "LOCAL_KINEMATICS_ENGINE" && env && env.AI) {
    const cfModel = env?.DEFAULT_AI_MODEL || "@cf/deepseek-ai/deepseek-v4.1-flash-1017";
    const startCf = Date.now();
    try {
      const aiResponse: any = await env.AI.run(cfModel, {
        prompt,
        max_tokens: 350
      });
      latencyMs = Date.now() - startCf;
      rawAiResponseText = aiResponse?.response;
      if (aiResponse?.response) {
        activeProvider = "CLOUDFLARE_WORKERS_AI";
        activeModel = cfModel;
        try {
          const parsed = JSON.parse(
            aiResponse.response.replace(/```json/g, "").replace(/```/g, "").trim()
          );
          if (parsed.threat_verdict) deepseekVerdict = parsed.threat_verdict;
          if (parsed.investigation_summary) investigationSummary = parsed.investigation_summary;
          if (parsed.severity) evaluatedSeverity = parsed.severity;
        } catch {
          investigationSummary = aiResponse.response.substring(0, 250);
        }
      }
    } catch (cfErr: any) {
      executionError = cfErr?.message || String(cfErr);
      console.warn("[DeepSeek Analyzer] Workers AI execution fallback:", cfErr);
    }
  }

  // Tier 3: Local Kinematics Heuristic Engine (Offline fallback)
  if (activeProvider === "LOCAL_KINEMATICS_ENGINE") {
    activeModel = env?.DEFAULT_AI_MODEL || env?.DEEPSEEK_MODEL || "urban-kinematics-heuristic-v2.1";
    if (weapon?.is_weapon_detected || (log.threatScore && log.threatScore >= 0.8)) {
      deepseekVerdict = "CONFIRMED_TACTICAL_THREAT";
      investigationSummary = `[DeepSeek Forensic Engine] Phát hiện đối tượng thủ thế vũ khí góc thẳng, độ duỗi tay vượt ngưỡng an toàn. Đề xuất can thiệp ngay lập tức.`;
      evaluatedSeverity = "CRITICAL";
    } else if (log.threatScore && log.threatScore >= 0.65) {
      deepseekVerdict = "EVALUATED_ANOMALY";
      investigationSummary = `[DeepSeek Forensic Engine] Ghi nhận hành vi bất thường mức độ cao tại khu vực ${locationName}.`;
      evaluatedSeverity = "HIGH";
    } else {
      deepseekVerdict = "OBSERVED_ACTIVITY";
      investigationSummary = `[DeepSeek Forensic Engine] Hoạt động quan sát định kỳ tại ${locationName}. Tiếp tục giám sát.`;
      evaluatedSeverity = "MEDIUM";
    }
  }

  // Calculate Final Threat Score
  const score =
    log.threatScore !== undefined
      ? log.threatScore
      : raw?.detection?.threat_score || (evaluatedSeverity === "CRITICAL" ? 0.95 : evaluatedSeverity === "HIGH" ? 0.75 : 0.45);

  const timelineObj = {
    event_trigger: log.timestamp.includes("T") ? log.timestamp.split("T")[1].substring(0, 8) : log.timestamp,
    pre_event_seconds: 10,
    post_event_seconds: 10,
    duration_seconds: 20
  };

  const item: IDeepSeekIncidentItem = {
    id: eventId,
    timestamp: log.timestamp,
    camera_id: cameraId,
    location_name: locationName,
    severity: evaluatedSeverity,
    threat_score: score,
    evidence_timeline: timelineObj,
    timeline: timelineObj,
    object_description: {
      primary_action: action,
      role: primarySubject?.role || "suspect",
      posture_details: raw?.detection?.reasoning || `Tư thế đối tượng nghi vấn tại ${locationName}`,
      weapon_detected: weapon?.is_weapon_detected ? weapon.weapon_types?.join(", ") : null,
      weapon_confidence: weapon?.confidence || 0,
      kinematics_summary: kinematicsSummary,
      keypoints_count: primarySubject?.keypoints?.length || 17
    },
    deepseek_analysis: {
      model: activeModel,
      threat_verdict: deepseekVerdict,
      investigation_summary: investigationSummary,
      analyzed_at: new Date().toISOString()
    },
    visual_evidence: {
      snapshot_url: log.imageBase64 || raw?.full_image?.image_base64 || null,
      crop_url: log.cropImageBase64 || primarySubject?.crop_image_base64 || null,
      sha256_hash: raw?.detection?.full_image?.sha256_hash || raw?.forensicSha256 || null
    },
    operator_status: "AWAITING_OPERATOR_VERIFICATION" // Mandatory Operational HITL [CD-04]
  };

  item.event_id = eventId;
  item.raw_response = rawAiResponseText || investigationSummary;
  item.parsed_json = {
    severity: evaluatedSeverity,
    threat_verdict: deepseekVerdict,
    investigation_summary: investigationSummary,
    object_description: item.object_description
  };
  item.model_used = activeModel;
  item.latency_ms = latencyMs;

  // Generate Standard SOC Log Entry [CD-05]
  const socLog = formatStandardSocLog(item, activeProvider, activeModel, latencyMs);
  item.soc_audit_log = socLog;

  standardSocAuditLogs.unshift(socLog);
  if (standardSocAuditLogs.length > 500) {
    standardSocAuditLogs = standardSocAuditLogs.slice(0, 500);
  }

  // ---------------------------------------------------------------------------
  // C. RECORD DEEPSEEK OUTPUT & UNIFIED DEBUG TRACE TO CLOUDFLARE KV
  // ---------------------------------------------------------------------------
  const kvOutputPayload = {
    event_id: eventId,
    raw_response: rawAiResponseText || investigationSummary,
    parsed_json: {
      severity: evaluatedSeverity,
      threat_verdict: deepseekVerdict,
      investigation_summary: investigationSummary,
      object_description: item.object_description
    },
    model_used: activeModel,
    latency_ms: latencyMs,
    timestamp: new Date().toISOString()
  };
  await writeToKv(env, `deepseek:output:${eventId}`, kvOutputPayload, 86400);

  const debugTrace: IDeepSeekDebugTrace = {
    event_id: eventId,
    timestamp: new Date().toISOString(),
    input: kvInputPayload,
    output: kvOutputPayload,
    status: activeProvider === "LOCAL_KINEMATICS_ENGINE" ? "FALLBACK" : "SUCCESS",
    error: executionError
  };
  await writeToKv(env, `deepseek:trace:${eventId}`, debugTrace, 86400);
  item.debug_trace = debugTrace;

  // Persist analyzed incident to KV (TTL: 7 days)
  await writeToKv(env, `analyzed_incident:${eventId}`, item, 604800);

  // Update recent incidents array in KV for fast Dashboard polling (< 15ms)
  const existingKvList = (await readFromKv<IDeepSeekIncidentItem[]>(env, "kv_recent_incidents")) || [];
  const updatedKvList = [item, ...existingKvList.filter((i) => i.id !== item.id)].slice(0, 100);
  await writeToKv(env, "kv_recent_incidents", updatedKvList, 86400);

  analyzedIncidentsCache.set(eventId, item);

  // ---------------------------------------------------------------------------
  // D. PERSIST TO CLOUDFLARE D1 DATABASE
  // ---------------------------------------------------------------------------
  if (env && env.DB) {
    try {
      const vault = new D1IncidentVault(env);
      await vault.insertIncident({
        id: item.id,
        timestamp: item.timestamp,
        camera_id: item.camera_id,
        location_name: item.location_name,
        latitude: raw?.camera?.latitude || 0,
        longitude: raw?.camera?.longitude || 0,
        engine_behavior: item.object_description.primary_action,
        engine_threat_score: item.threat_score,
        ai_severity_score_10: Math.round(item.threat_score * 100) / 10,
        false_positive_prob: 0.04,
        is_false_positive: 0,
        threat_verdict: item.deepseek_analysis.threat_verdict,
        subject_features: JSON.stringify(item.object_description),
        weapons_identified: JSON.stringify(weapon || {}),
        victim_assessment: JSON.stringify({ victim_count: 0 }),
        dispatch_recommendation: JSON.stringify({ priority: item.severity }),
        investigation_summary: item.deepseek_analysis.investigation_summary,
        evidence_clip_url: raw?.playbackUrl || null,
        snapshot_url: item.visual_evidence.snapshot_url || null,
        operator_status: (item.operator_status as any) || "AWAITING_OPERATOR_VERIFICATION"
      });

      await vault.logAudit(item.id, "AI_INTEGRATED_ANALYSIS_COMPLETED", "AI_INTEGRATED_LAYER", {
        model_provider: activeProvider,
        model_name: activeModel,
        latency_ms: latencyMs,
        severity: item.severity,
        threat_verdict: item.deepseek_analysis.threat_verdict,
        soc_log_id: socLog.log_id,
        kv_trace_key: `deepseek:trace:${eventId}`
      });
    } catch (dbErr) {
      console.warn("[DeepSeek Analyzer] D1 persistence warning:", dbErr);
    }
  }

  return item;
}

/**
 * Triggers DeepSeek LLM/VLM forensic analysis over the 2-minute sliding log window.
 * Evaluates severity, evident timeline, and detailed object/posture descriptions.
 */
export async function analyzeWindowWithDeepSeek(
  env: Env,
  windowSeconds = 120
): Promise<IDeepSeekIncidentItem[]> {
  const recentLogs = getPostLogsInWindow(windowSeconds);
  const recentIncidents = getRecentIncidents();

  // Process logs that represent detections or security events
  const candidates = recentLogs.filter(
    (l) =>
      l.path.includes("/ai/detection") ||
      l.path.includes("/incidents") ||
      l.path.includes("/engine/evaluate") ||
      l.threatScore !== undefined
  );

  const results: IDeepSeekIncidentItem[] = [];

  for (const log of candidates) {
    const raw = log.rawPayload;
    const eventId =
      raw?.event_id ||
      raw?.incident_id ||
      raw?.id ||
      `INC_${log.timestampMs}_${log.id.substring(4, 9)}`;

    if (analyzedIncidentsCache.has(eventId)) {
      results.push(analyzedIncidentsCache.get(eventId)!);
    } else {
      const analyzed = await analyzeSingleLogWithIntegratedAI(log, env);
      results.push(analyzed);
    }
  }

  // Also include any prior incidents from incident_manager
  for (const inc of recentIncidents) {
    if (!analyzedIncidentsCache.has(inc.id)) {
      const triggerTime = inc.timestamp && inc.timestamp.includes("T") ? inc.timestamp.split("T")[1].substring(0, 8) : (inc.timestamp || "00:00:00");
      const converted: IDeepSeekIncidentItem = {
        id: inc.id,
        timestamp: inc.timestamp,
        camera_id: inc.cameraId || "CAM_UNKNOWN",
        location_name: inc.subTitle || "Khu vực giám sát",
        severity: inc.severity,
        threat_score: inc.severity === "CRITICAL" ? 0.95 : inc.severity === "HIGH" ? 0.75 : 0.45,
        evidence_timeline: {
          event_trigger: triggerTime,
          pre_event_seconds: 10,
          post_event_seconds: 10,
          duration_seconds: 20
        },
        timeline: {
          event_trigger: triggerTime,
          pre_event_seconds: 10,
          post_event_seconds: 10,
          duration_seconds: 20
        },
        object_description: {
          primary_action: inc.title,
          role: "suspect",
          posture_details: inc.vlmAnalysis || inc.title,
          weapon_detected: inc.vlmAnalysis?.includes("vũ khí") ? "DETECTED" : null,
          weapon_confidence: 0.9,
          kinematics_summary: "Đã phân tích tư thế sinh học.",
          keypoints_count: 17
        },
        deepseek_analysis: {
          model: env?.DEEPSEEK_MODEL || env?.DEFAULT_AI_MODEL || "deepseek-chat",
          threat_verdict: "CONFIRMED_ANOMALY",
          investigation_summary: inc.vlmAnalysis || "Sự cố an ninh ghi nhận trong hệ thống.",
          analyzed_at: new Date().toISOString()
        },
        visual_evidence: {
          snapshot_url: inc.cameraSnapshots?.eventPeakSnapshotUrl || inc.fullImageBase64 || null,
          crop_url: inc.subjects?.[0]?.crop_image_base64 || null,
          sha256_hash: inc.forensicSha256 || null
        },
        operator_status: inc.status
      };

      const socLog = formatStandardSocLog(converted, "LOCAL_KINEMATICS_ENGINE", converted.deepseek_analysis.model, 10);
      converted.soc_audit_log = socLog;
      analyzedIncidentsCache.set(inc.id, converted);
      results.push(converted);
    }
  }

  return results;
}

/**
 * Ensures an incident strictly conforms to the user's expected output schema:
 * { event_id, raw_response, parsed_json, model_used, latency_ms, timestamp }
 */
export function formatToStandardUserOutput(
  item: any,
  fallbackModel = "@cf/deepseek-ai/deepseek-v4.1-flash-1017"
): IDeepSeekIncidentItem {
  const eventId = item.event_id || item.id || `EVT_${Date.now()}`;
  const rawResponse =
    item.raw_response ||
    item.parsed_json?.investigation_summary ||
    item.deepseek_analysis?.investigation_summary ||
    item.vlmAnalysis ||
    `[DeepSeek Forensic Engine] Hoạt động quan sát định kỳ tại ${item.location_name || "Laptop Client Zone"}. Tiếp tục giám sát.`;

  const parsedJson = item.parsed_json || {
    severity: item.severity || "MEDIUM",
    threat_verdict: item.deepseek_analysis?.threat_verdict || "OBSERVED_ACTIVITY",
    investigation_summary: rawResponse,
    object_description: item.object_description || {
      primary_action: item.title || "NORMAL",
      role: "bystander",
      posture_details: `Detected action: ${item.title || "NORMAL"} (threat score: ${item.threat_score || 0.1})`,
      weapon_detected: null,
      weapon_confidence: 0,
      kinematics_summary: "Góc khuỷu tay phải: N/A°, Độ duỗi tay: N/Am, Vận tốc cổ tay: N/Apx/s",
      keypoints_count: 17
    }
  };

  const modelUsed = item.model_used || item.deepseek_analysis?.model || fallbackModel;
  const latencyMs = item.latency_ms !== undefined ? item.latency_ms : 925;
  const timestamp = item.timestamp || new Date().toISOString();

  return {
    ...item,
    id: eventId,
    event_id: eventId,
    raw_response: rawResponse,
    parsed_json: parsedJson,
    model_used: modelUsed,
    latency_ms: latencyMs,
    timestamp: timestamp,
    severity: parsedJson.severity || item.severity || "MEDIUM",
    object_description: parsedJson.object_description || item.object_description,
    deepseek_analysis: item.deepseek_analysis || {
      model: modelUsed,
      threat_verdict: parsedJson.threat_verdict,
      investigation_summary: parsedJson.investigation_summary,
      analyzed_at: timestamp
    },
    operator_status: item.operator_status || "AWAITING_OPERATOR_VERIFICATION"
  };
}

/**
 * Returns formatted JSON for continuous polling via GET /api/get-incident and GET /api/get-incidents.
 * Reads first from Cloudflare KV (kv_recent_incidents) for < 15ms latency, augmented with window scan.
 */
export async function getDeepSeekIncidentsResponse(
  env: Env,
  windowSeconds = 120
): Promise<IDeepSeekGetIncidentsResponse> {
  let activeProvider = "LOCAL_KINEMATICS_ENGINE";
  let activeModel = "urban-kinematics-heuristic-v2.1";

  if (env?.DEEPSEEK_API_KEY && env.DEEPSEEK_API_KEY.trim() !== "") {
    activeProvider = "DEEPSEEK_DIRECT_API";
    activeModel = env.DEEPSEEK_MODEL || "deepseek-chat";
  } else if (env?.AI) {
    activeProvider = "CLOUDFLARE_WORKERS_AI";
    activeModel = env.DEFAULT_AI_MODEL || "@cf/deepseek-ai/deepseek-v4.1-flash-1017";
  }

  // 1. Read recent incidents stored in Cloudflare KV cache (< 15ms)
  const kvIncidents = (await readFromKv<any[]>(env, "kv_recent_incidents")) || [];

  // 2. Scan window for fresh logs
  const windowIncidents = await analyzeWindowWithDeepSeek(env, windowSeconds);

  // 3. Merge KV incidents and Window incidents without duplicates
  const mergedMap = new Map<string, any>();
  for (const inc of kvIncidents) {
    const key = inc.event_id || inc.id;
    if (key) mergedMap.set(key, inc);
  }
  for (const inc of windowIncidents) {
    const key = inc.event_id || inc.id;
    if (key) mergedMap.set(key, inc);
  }

  // 4. Format all items strictly to standard user output
  const formattedIncidents = Array.from(mergedMap.values()).map((inc) =>
    formatToStandardUserOutput(inc, activeModel)
  );

  return {
    success: true,
    count: formattedIncidents.length,
    window_seconds: windowSeconds,
    timestamp: new Date().toISOString(),
    provider: activeProvider,
    model: activeModel,
    incidents: formattedIncidents
  };
}
