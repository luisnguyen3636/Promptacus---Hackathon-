// Test Suite: Cloudflare KV Incident Logging & DeepSeek Input/Output Tracing Pipeline

import {
  recordPostRequestLog,
  analyzeSingleLogWithIntegratedAI,
  getDeepSeekIncidentsResponse,
  writeToKv,
  readFromKv,
  getDeepSeekTrace
} from './src/deepseek_analyzer.ts';

async function runKvPipelineTests() {
  console.log('=== TEST SUITE: CLOUDFLARE KV INCIDENT PIPELINE & INPUT/OUTPUT TRACING ===\n');

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
  // 1. Test KV Core Read & Write Utilities
  // ---------------------------------------------------------------------------
  console.log('1. Testing KV Core Read & Write Functionality:');

  const mockKvEnv = {
    DEFAULT_AI_MODEL: "@cf/deepseek-ai/deepseek-v4.1-flash-1017",
    DEEPSEEK_MODEL: "deepseek-chat"
  };

  const testKey = "test:ping:key";
  const testVal = { status: "OK", timestamp: Date.now() };

  await writeToKv(mockKvEnv, testKey, testVal, 300);
  const retrievedVal = await readFromKv(mockKvEnv, testKey);

  assert(Boolean(retrievedVal), "Successfully wrote and read back from KV store");
  assert(retrievedVal && retrievedVal.status === "OK", "Retrieved KV value content matches written object");

  // ---------------------------------------------------------------------------
  // 2. Test Ingestion & Writing Input + Output to KV
  // ---------------------------------------------------------------------------
  console.log('\n2. Testing Storing Both Input & Output to KV for DeepSeek Processing:');

  const testEventId = `EVT_KV_TEST_${Date.now()}`;
  const samplePayload = {
    event_id: testEventId,
    timestamp: new Date().toISOString(),
    camera: {
      camera_id: "CAM_SOUTH_PERIMETER_09",
      name: "Vành Đai Phía Nam",
      address: "Đại lộ Nguyễn Văn Linh, Quận 7",
      latitude: 10.7302,
      longitude: 106.705
    },
    detection: {
      primary_action: "INTRUSION_LOITERING",
      threat_level: "HIGH",
      threat_score: 0.88,
      is_urgent: true,
      reasoning: "Phát hiện đối tượng leo rào vượt tường khu vực nhạy cảm",
      weapon: {
        is_weapon_detected: false,
        weapon_types: [],
        confidence: 0.0
      },
      subjects: [
        {
          track_id: 305,
          role: "suspect",
          confidence: 0.92,
          kinematics: {
            spine_angle: 34.0,
            right_elbow_angle: 145.0,
            right_arm_extension: 0.35,
            wrist_velocity: 320.0
          },
          keypoints: Array.from({ length: 17 }, (_, i) => ({ id: i, name: `kp_${i}`, x: 0.4, y: 0.6, confidence: 0.88 }))
        }
      ],
      full_image: {
        image_base64: "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD/test_kv_image...",
        sha256_hash: "abcd1234ef567890aabbccddeeff0011223344556677889900aabbccddeeff00"
      }
    }
  };

  const loggedReq = recordPostRequestLog(
    "/api/v1/ai/detection",
    "POST",
    "113.185.73.217",
    samplePayload
  );

  assert(Boolean(loggedReq.id), "Recorded POST log into buffer");

  // Execute in-process AI analysis with KV persistence
  const analyzedIncident = await analyzeSingleLogWithIntegratedAI(loggedReq, mockKvEnv);

  assert(Boolean(analyzedIncident), "DeepSeek in-process layer analyzed incident");
  assert(analyzedIncident.id === testEventId, "Incident ID correctly preserved");
  assert(analyzedIncident.operator_status === "AWAITING_OPERATOR_VERIFICATION", "Strictly enforces [CD-04] HITL Gate");

  // Verify KV Raw Incident
  const rawFromKv = await readFromKv(mockKvEnv, `raw_incident:${testEventId}`);
  assert(Boolean(rawFromKv), "Raw incident payload verified in KV under key raw_incident:<id>");

  // Verify KV DeepSeek Input
  const inputFromKv = await readFromKv(mockKvEnv, `deepseek:input:${testEventId}`);
  assert(Boolean(inputFromKv), "DeepSeek INPUT verified in KV under key deepseek:input:<id>");
  assert(inputFromKv && Boolean(inputFromKv.prompt), "DeepSeek Input contains prompt text");
  assert(inputFromKv && Boolean(inputFromKv.raw_payload), "DeepSeek Input contains raw payload");
  assert(inputFromKv && Boolean(inputFromKv.model_target), "DeepSeek Input specifies model_target");

  // Verify KV DeepSeek Output
  const outputFromKv = await readFromKv(mockKvEnv, `deepseek:output:${testEventId}`);
  assert(Boolean(outputFromKv), "DeepSeek OUTPUT verified in KV under key deepseek:output:<id>");
  assert(outputFromKv && Boolean(outputFromKv.parsed_json), "DeepSeek Output contains parsed JSON response");
  assert(outputFromKv && typeof outputFromKv.latency_ms === "number", "DeepSeek Output records execution latency in ms");
  assert(outputFromKv && Boolean(outputFromKv.model_used), "DeepSeek Output records model_used");

  // Verify KV Unified Debug Trace
  const traceFromKv = await getDeepSeekTrace(mockKvEnv, testEventId);
  assert(Boolean(traceFromKv), "Unified debug trace verified via getDeepSeekTrace()");
  assert(traceFromKv && Boolean(traceFromKv.input), "Trace contains complete Input snapshot");
  assert(traceFromKv && Boolean(traceFromKv.output), "Trace contains complete Output snapshot");
  assert(traceFromKv && (traceFromKv.status === "SUCCESS" || traceFromKv.status === "FALLBACK"), "Trace has status flag for troubleshooting");

  // ---------------------------------------------------------------------------
  // 3. Test Dashboard Sync & Cache Read
  // ---------------------------------------------------------------------------
  console.log('\n3. Testing Dashboard Sync from KV Cache:');

  const recentKvIncidents = await readFromKv(mockKvEnv, "kv_recent_incidents");
  assert(Array.isArray(recentKvIncidents), "kv_recent_incidents is an array in KV");
  assert(recentKvIncidents.length > 0, "kv_recent_incidents contains newly analyzed incident");
  assert(recentKvIncidents[0].id === testEventId, "First item in kv_recent_incidents matches latest event");

  const streamRes = await getDeepSeekIncidentsResponse(mockKvEnv, 120);
  assert(streamRes.success === true, "Response has success: true");
  assert(streamRes.incidents.some(i => i.id === testEventId), "Dashboard stream includes incident processed via KV");

  console.log('\nSample Unified Debug Trace stored in KV:');
  console.log(JSON.stringify({
    event_id: traceFromKv.event_id,
    timestamp: traceFromKv.timestamp,
    status: traceFromKv.status,
    input_sample: {
      model_target: traceFromKv.input.model_target,
      prompt_preview: traceFromKv.input.prompt.substring(0, 120) + "..."
    },
    output_sample: {
      model_used: traceFromKv.output.model_used,
      latency_ms: traceFromKv.output.latency_ms,
      parsed_json: traceFromKv.output.parsed_json
    }
  }, null, 2));

  console.log(`\n=== RESULTS: ${passed} PASSED, ${failed} FAILED ===\n`);
  if (failed > 0) {
    process.exit(1);
  }
}

runKvPipelineTests().catch((err) => {
  console.error("Test execution failed:", err);
  process.exit(1);
});
