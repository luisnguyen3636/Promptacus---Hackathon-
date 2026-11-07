// Test Suite: Integrated AI Layer, Pluggable DeepSeek API Key, and Standard SOC Audit Logs

import {
  recordPostRequestLog,
  getPostLogsInWindow,
  analyzeSingleLogWithIntegratedAI,
  analyzeWindowWithDeepSeek,
  getDeepSeekIncidentsResponse,
  getStandardSocAuditLogs,
  callDeepSeekDirectApi
} from './src/deepseek_analyzer.ts';

async function runIntegratedAILayerTests() {
  console.log('=== TEST SUITE: INTEGRATED AI LAYER & STANDARD SOC AUDIT LOGS ===\n');

  let passed = 0;
  let failed = 0;

  function assert(condition, message) {
    if (condition) {
      console.log(`  [PASS] ${message}`);
      passed++;
    } else {
      console.error(`  [FAIL] ${message}`);
      failed++;
    }
  }

  // ---------------------------------------------------------------------------
  // 1. Test POST Request Ingestion & Automatic In-Process AI Layer
  // ---------------------------------------------------------------------------
  console.log('1. Testing In-Process Automatic AI Layer Triggering:');

  const samplePayload = {
    event_id: `EVT_AUTO_AI_${Date.now()}`,
    timestamp: new Date().toISOString(),
    camera: {
      camera_id: "CAM_WEST_GATE_04",
      name: "Cổng Phía Tây",
      address: "456 Đường Lê Lợi, Phường Bến Thành, Quận 1",
      latitude: 10.7725,
      longitude: 106.698
    },
    detection: {
      primary_action: "WEAPON_THREAT",
      threat_level: "CRITICAL",
      threat_score: 0.94,
      is_urgent: true,
      reasoning: "Phát hiện đối tượng rút vũ khí ngắn và thủ thế cận chiến",
      weapon: {
        is_weapon_detected: true,
        weapon_types: ["FIREARM_TACTICAL"],
        confidence: 0.96
      },
      subjects: [
        {
          track_id: 102,
          role: "suspect",
          confidence: 0.95,
          kinematics: {
            spine_angle: 12.5,
            right_elbow_angle: 172.0,
            right_arm_extension: 0.42,
            wrist_velocity: 480.0
          },
          keypoints: Array.from({ length: 17 }, (_, i) => ({ id: i, name: `kp_${i}`, x: 0.5, y: 0.5, confidence: 0.9 }))
        }
      ],
      full_image: {
        image_base64: "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP...",
        sha256_hash: "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
      }
    }
  };

  const recordedLog = recordPostRequestLog(
    "/api/v1/ai/detection",
    "POST",
    "127.0.0.1",
    samplePayload
  );

  assert(Boolean(recordedLog.id), "Recorded POST log generated valid unique Log ID");
  assert(recordedLog.hasImage === true, "Identified Base64 visual evidence inside POST request");
  assert(recordedLog.threatScore === 0.94, "Extracted accurate threat score 0.94 from payload");

  // Run in-process AI analysis directly (the automated layer)
  const mockEnv = {
    DEFAULT_AI_MODEL: "@cf/deepseek-ai/deepseek-v4.1-flash-1017",
    DEEPSEEK_MODEL: "deepseek-chat"
  };

  const analyzedItem = await analyzeSingleLogWithIntegratedAI(recordedLog, mockEnv);

  assert(Boolean(analyzedItem), "In-process AI layer returned analyzed incident item");
  assert(analyzedItem.id === samplePayload.event_id, "Analyzed item matches incoming event ID");
  assert(analyzedItem.severity === "CRITICAL", "Correctly classified severity as CRITICAL");
  assert(analyzedItem.operator_status === "AWAITING_OPERATOR_VERIFICATION", "Strictly enforced [CD-04] HITL Gate");

  // ---------------------------------------------------------------------------
  // 2. Test Standard SOC Audit Log Generation & Structure
  // ---------------------------------------------------------------------------
  console.log('\n2. Testing Standard SOC Structured Audit Logging:');

  assert(Boolean(analyzedItem.soc_audit_log), "Analyzed incident contains soc_audit_log");
  const socLog = analyzedItem.soc_audit_log;
  assert(socLog.source === "AI_INTEGRATED_LAYER", "SOC log source is AI_INTEGRATED_LAYER");
  assert(socLog.log_level === "CRITICAL", "SOC log level is CRITICAL");
  assert(socLog.event_id === samplePayload.event_id, "SOC log links correctly to event_id");
  assert(typeof socLog.latency_ms === "number" && socLog.latency_ms >= 0, "SOC log records execution latency in ms");
  assert(Boolean(socLog.object_description.kinematics_summary), "SOC log includes kinematic posture details");

  const allSocLogs = getStandardSocAuditLogs();
  assert(allSocLogs.length > 0, "Standard SOC audit logs repository is populated");
  assert(allSocLogs[0].log_id.startsWith("SOC_LOG_"), "Standard SOC log has compliant ID prefix");

  // ---------------------------------------------------------------------------
  // 3. Test Pluggable Direct DeepSeek API Caller
  // ---------------------------------------------------------------------------
  console.log('\n3. Testing Pluggable DeepSeek Direct API Function:');

  // Verify callDeepSeekDirectApi handles simulated or invalid key gracefully
  const apiCallResult = await callDeepSeekDirectApi(
    "Test prompt for SOC",
    "dummy_test_api_key_12345",
    "deepseek-chat",
    "http://127.0.0.1:9999/dummy-endpoint"
  );

  assert(apiCallResult.success === false, "Handles offline / unreachable direct API without crashing (graceful failover)");
  assert(typeof apiCallResult.latencyMs === "number", "Direct API client tracks call latency");

  // ---------------------------------------------------------------------------
  // 4. Test GET /api/get-incidents & /api/get-incident JSON Response
  // ---------------------------------------------------------------------------
  console.log('\n4. Testing GET /api/get-incidents & /api/get-incident Output:');

  const streamResponse = await getDeepSeekIncidentsResponse(mockEnv, 120);

  assert(streamResponse.success === true, "Response has success: true");
  assert(streamResponse.window_seconds === 120, "Response window_seconds matches 120s sliding window");
  assert(Array.isArray(streamResponse.incidents), "Response contains incidents array parsed from AI");
  assert(streamResponse.count >= 1, "Response contains at least 1 analyzed incident");
  assert(Boolean(streamResponse.provider), `Response includes active AI provider: ${streamResponse.provider}`);
  assert(Boolean(streamResponse.model), `Response includes model name: ${streamResponse.model}`);

  const sampleIncident = streamResponse.incidents[0];
  assert(Boolean(sampleIncident.object_description), "Incident contains parsed object_description");
  assert(Boolean(sampleIncident.timeline), "Incident contains forensic evidence timeline");
  assert(Boolean(sampleIncident.deepseek_analysis), "Incident contains deepseek_analysis summary");

  console.log('\nSample JSON output returned by GET /api/get-incidents:');
  console.log(JSON.stringify({
    success: streamResponse.success,
    count: streamResponse.count,
    provider: streamResponse.provider,
    model: streamResponse.model,
    sample_incident: {
      id: sampleIncident.id,
      severity: sampleIncident.severity,
      object_description: sampleIncident.object_description,
      deepseek_analysis: sampleIncident.deepseek_analysis,
      timeline: sampleIncident.timeline,
      soc_audit_log: sampleIncident.soc_audit_log
    }
  }, null, 2));

  console.log(`\n=== RESULTS: ${passed} PASSED, ${failed} FAILED ===\n`);
  if (failed > 0) {
    process.exit(1);
  }
}

runIntegratedAILayerTests().catch((err) => {
  console.error("Test execution failed:", err);
  process.exit(1);
});
