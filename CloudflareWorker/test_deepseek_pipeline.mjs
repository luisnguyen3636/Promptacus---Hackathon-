// Test Suite: DeepSeek 2-Minute Incident Analysis Pipeline & /api/get-incident

import {
  recordPostRequestLog,
  getPostLogsInWindow,
  analyzeWindowWithDeepSeek,
  getDeepSeekIncidentsResponse
} from './src/deepseek_analyzer.ts';

async function runDeepSeekPipelineTests() {
  console.log('=== TEST SUITE: DEEPSEEK 2-MINUTE INCIDENT ANALYSIS & /api/get-incident ===\n');

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
  // 1. Test POST Request Logging
  // ---------------------------------------------------------------------------
  console.log('1. Testing POST Request Logging:');

  const samplePayload = {
    event_id: `EVT_TEST_DEEPSEEK_${Date.now()}`,
    timestamp: new Date().toISOString(),
    camera: {
      camera_id: "CAM_EAST_GATE_01",
      name: "Cổng Phía Đông",
      address: "123 Đường Nam Kỳ Khởi Nghĩa, Quận 1",
      latitude: 10.776889,
      longitude: 106.700806
    },
    detection: {
      primary_action: "WEAPON_THREAT",
      threat_level: "CRITICAL",
      threat_score: 0.96,
      reasoning: "Tư thế thủ vũ khí nguy hiểm góc duỗi tay 168 độ",
      weapon: {
        is_weapon_detected: true,
        weapon_types: ["FIREARM_TACTICAL_STANCE"],
        confidence: 0.94,
        description: "Tactical weapon stance"
      },
      subjects: [
        {
          track_id: 101,
          role: "suspect",
          behavior: "WEAPON_THREAT",
          threat_level: "CRITICAL",
          confidence: 0.95,
          kinematics: {
            right_elbow_angle: 168.0,
            right_arm_extension: 0.38,
            wrist_velocity: 450.0
          },
          keypoints: [
            { id: 0, name: "nose", x: 220, y: 110, confidence: 0.98 },
            { id: 10, name: "right_wrist", x: 305, y: 190, confidence: 0.92 }
          ],
          crop_image_base64: "data:image/jpeg;base64,samplecrop123"
        }
      ],
      full_image: {
        image_base64: "data:image/jpeg;base64,samplefullimage456",
        sha256_hash: "hash_test_sha256_abcdef",
        width: 640,
        height: 480
      }
    }
  };

  const loggedEntry = recordPostRequestLog(
    "/api/v1/ai/detection",
    "POST",
    "113.185.73.217",
    samplePayload
  );

  assert(loggedEntry && loggedEntry.id.startsWith("LOG_"), "Successfully generated Log ID");
  assert(loggedEntry.hasImage === true, "Detected and extracted imageBase64 from POST payload");
  assert(loggedEntry.threatScore === 0.96, "Extracted threat score 0.96");
  assert(loggedEntry.cameraId === "CAM_EAST_GATE_01", "Extracted camera ID CAM_EAST_GATE_01");

  // ---------------------------------------------------------------------------
  // 2. Test 2-Minute Window Filtering
  // ---------------------------------------------------------------------------
  console.log('\n2. Testing 2-Minute Sliding Window Filter:');

  const windowLogs = getPostLogsInWindow(120);
  assert(windowLogs.length >= 1, `Found ${windowLogs.length} log(s) in the 2-minute window`);
  assert(windowLogs[0].id === loggedEntry.id, "Most recent log matches recorded entry");

  // ---------------------------------------------------------------------------
  // 3. Test DeepSeek Forensic Analysis
  // ---------------------------------------------------------------------------
  console.log('\n3. Testing DeepSeek Analysis Engine:');

  const mockEnv = {
    DEFAULT_AI_MODEL: "@cf/deepseek-ai/deepseek-v4.1-flash-1017",
    ENVIRONMENT: "test"
  };

  const analyzedIncidents = await analyzeWindowWithDeepSeek(mockEnv, 120);
  assert(analyzedIncidents.length >= 1, `DeepSeek analyzed ${analyzedIncidents.length} incident(s)`);

  const incident = analyzedIncidents.find(i => i.id === samplePayload.event_id);
  assert(!!incident, "Found matching analyzed incident by event_id");
  assert(incident.severity === "CRITICAL", "Correctly evaluated severity as CRITICAL");
  assert(incident.deepseek_analysis.model === "@cf/deepseek-ai/deepseek-v4.1-flash-1017", "Used default DeepSeek model");
  assert(typeof incident.deepseek_analysis.investigation_summary === "string", "Generated forensic investigation summary");
  assert(incident.object_description.weapon_detected === "FIREARM_TACTICAL_STANCE", "Detected firearm weapon in object description");
  assert(incident.evidence_timeline.duration_seconds === 20, "Evidence timeline duration is 20 seconds");
  assert(incident.visual_evidence.snapshot_url === samplePayload.detection.full_image.image_base64, "Snapshot URL preserved");
  assert(incident.visual_evidence.sha256_hash === "hash_test_sha256_abcdef", "SHA-256 hash verified");
  assert(incident.operator_status === "AWAITING_OPERATOR_VERIFICATION", "Complies with CD-04 Operational HITL Gate");

  // ---------------------------------------------------------------------------
  // 4. Test GET /api/get-incident JSON Generator
  // ---------------------------------------------------------------------------
  console.log('\n4. Testing GET /api/get-incident Response Generator:');

  const apiResponse = await getDeepSeekIncidentsResponse(mockEnv, 120);
  assert(apiResponse.success === true, "Response has success: true");
  assert(apiResponse.window_seconds === 120, "Response window_seconds is 120");
  assert(Array.isArray(apiResponse.incidents), "Response contains incidents array");
  assert(apiResponse.count >= 1, `Response has count ${apiResponse.count}`);

  console.log('\nSample JSON output from /api/get-incident:');
  console.log(JSON.stringify({
    success: apiResponse.success,
    count: apiResponse.count,
    window_seconds: apiResponse.window_seconds,
    sample_incident: {
      id: incident.id,
      severity: incident.severity,
      object_description: incident.object_description,
      deepseek_analysis: incident.deepseek_analysis,
      timeline: incident.evidence_timeline
    }
  }, null, 2));

  console.log(`\n=== RESULTS: ${passed} PASSED, ${failed} FAILED ===\n`);
  if (failed > 0) {
    process.exit(1);
  }
}

runDeepSeekPipelineTests().catch((err) => {
  console.error("Test failed with error:", err);
  process.exit(1);
});
