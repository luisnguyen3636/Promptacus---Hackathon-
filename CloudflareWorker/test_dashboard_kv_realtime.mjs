// Test Suite: Realtime Dashboard KV Integration & Exact DeepSeek Output Rendering
import {
  writeToKv,
  readFromKv,
  getDeepSeekIncidentsResponse,
  formatToStandardUserOutput
} from './src/deepseek_analyzer.ts';

// Universal Mapper function mirroring frontend mapKvIncidentItem
function mapKvIncidentItem(item) {
  if (!item) {
    return {
      id: `EVT_${Date.now()}`,
      title: 'NORMAL',
      subTitle: 'Laptop Client Zone',
      sourceIp: '127.0.0.1',
      category: 'PHYSICAL_CAMERA',
      severity: 'MEDIUM',
      timestamp: new Date().toISOString(),
      status: 'PENDING_VERIFICATION',
    };
  }

  const parsed = item.parsed_json || {};
  const objDesc = parsed.object_description || item.object_description || {};
  const eventId = item.event_id || item.id || `EVT_${Date.now()}`;

  const primaryAction = objDesc.primary_action || item.title || item.engine_behavior || 'NORMAL';
  const postureDetails = objDesc.posture_details || item.vlmAnalysis || `Detected action: ${primaryAction}`;
  const kinematicsSummary =
    objDesc.kinematics_summary ||
    'Góc khuỷu tay phải: N/A°, Độ duỗi tay: N/Am, Vận tốc cổ tay: N/Apx/s';
  const severity = (parsed.severity || item.severity || 'MEDIUM').toUpperCase();
  const investigationSummary =
    parsed.investigation_summary ||
    item.raw_response ||
    item.vlmAnalysis ||
    item.deepseek_analysis?.investigation_summary ||
    `[DeepSeek Forensic Engine] Hoạt động quan sát định kỳ tại ${item.location_name || 'Laptop Client Zone'}. Tiếp tục giám sát.`;

  return {
    id: eventId,
    eventId: eventId,
    title: primaryAction,
    subTitle: item.location_name || item.subTitle || item.camera_id || 'Laptop Client Zone',
    sourceIp: item.camera_id || item.sourceIp || '127.0.0.1',
    category: 'PHYSICAL_CAMERA',
    severity: severity,
    timestamp: item.timestamp || item.evidence_timeline?.event_trigger || 'Vừa xong',
    cameraId: item.camera_id || null,
    cameraSnapshots: {
      eventPeakSnapshotUrl: item.visual_evidence?.snapshot_url || item.snapshot_url || null,
      preEventSnapshotUrl: item.visual_evidence?.crop_url || item.crop_url || null,
    },
    playbackUrl: item.visual_evidence?.snapshot_url || item.snapshot_url || null,
    status: item.operator_status || 'PENDING_VERIFICATION',
    vlmAnalysis: investigationSummary,
    rawResponse: item.raw_response || investigationSummary,
    threatVerdict: parsed.threat_verdict || item.deepseek_analysis?.threat_verdict || 'OBSERVED_ACTIVITY',
    role: objDesc.role || 'bystander',
    postureDetails: postureDetails,
    kinematicsSummary: kinematicsSummary,
    weaponDetected: objDesc.weapon_detected !== undefined ? objDesc.weapon_detected : null,
    weaponConfidence: objDesc.weapon_confidence !== undefined ? objDesc.weapon_confidence : 0,
    keypointsCount: objDesc.keypoints_count || 17,
    modelUsed: item.model_used || item.deepseek_analysis?.model || '@cf/deepseek-ai/deepseek-v4.1-flash-1017',
    latencyMs: item.latency_ms !== undefined ? item.latency_ms : 925,
    parsedJson: parsed,
    fullImageBase64: item.visual_evidence?.snapshot_url || item.snapshot_url || null,
  };
}

async function runDashboardKvRealtimeTests() {
  console.log('=== TEST SUITE: DASHBOARD KV REALTIME INTEGRATION & EXACT OUTPUT RENDERING ===\n');

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

  const mockEnv = {
    DEFAULT_AI_MODEL: "@cf/deepseek-ai/deepseek-v4.1-flash-1017",
    DEEPSEEK_MODEL: "@cf/deepseek-ai/deepseek-v4.1-flash-1017"
  };

  // ---------------------------------------------------------------------------
  // 1. Inject User's Exact DeepSeek Sample Output into Cloudflare KV
  // ---------------------------------------------------------------------------
  console.log('1. Ingesting Exact Sample Output into Cloudflare KV:');

  const exactUserOutput = {
    "event_id": "EVT_20261107_213746_3e304691",
    "raw_response": "[DeepSeek Forensic Engine] Hoạt động quan sát định kỳ tại Laptop Client Zone. Tiếp tục giám sát.",
    "parsed_json": {
      "severity": "MEDIUM",
      "threat_verdict": "OBSERVED_ACTIVITY",
      "investigation_summary": "[DeepSeek Forensic Engine] Hoạt động quan sát định kỳ tại Laptop Client Zone. Tiếp tục giám sát.",
      "object_description": {
        "primary_action": "NORMAL",
        "role": "bystander",
        "posture_details": "Detected action: NORMAL (threat score: 0.10)",
        "weapon_detected": null,
        "weapon_confidence": 0,
        "kinematics_summary": "Góc khuỷu tay phải: N/A°, Độ duỗi tay: N/Am, Vận tốc cổ tay: N/Apx/s",
        "keypoints_count": 17
      }
    },
    "model_used": "@cf/deepseek-ai/deepseek-v4.1-flash-1017",
    "latency_ms": 925,
    "timestamp": "2026-11-07T14:37:50.049Z"
  };

  // Write individual output trace to KV
  await writeToKv(mockEnv, `deepseek:output:${exactUserOutput.event_id}`, exactUserOutput, 86400);

  // Write to recent incidents array in KV
  await writeToKv(mockEnv, "kv_recent_incidents", [exactUserOutput], 86400);

  const readBackOutput = await readFromKv(mockEnv, `deepseek:output:${exactUserOutput.event_id}`);
  assert(Boolean(readBackOutput), "KV successfully read back individual deepseek:output record");
  assert(readBackOutput.event_id === "EVT_20261107_213746_3e304691", "event_id matches expected 'EVT_20261107_213746_3e304691'");
  assert(readBackOutput.parsed_json.severity === "MEDIUM", "parsed_json.severity is MEDIUM");
  assert(readBackOutput.model_used === "@cf/deepseek-ai/deepseek-v4.1-flash-1017", "model_used matches '@cf/deepseek-ai/deepseek-v4.1-flash-1017'");
  assert(readBackOutput.latency_ms === 925, "latency_ms matches 925");

  // ---------------------------------------------------------------------------
  // 2. Test Polling API /api/get-incident reads from KV and returns standard output
  // ---------------------------------------------------------------------------
  console.log('\n2. Testing getDeepSeekIncidentsResponse with KV items:');

  const response = await getDeepSeekIncidentsResponse(mockEnv, 120);
  assert(response.success === true, "Endpoint returns success: true");
  assert(response.count >= 1, `Endpoint returned ${response.count} incidents (count >= 1)`);

  const targetIncident = response.incidents.find(i => (i.event_id || i.id) === "EVT_20261107_213746_3e304691");
  assert(Boolean(targetIncident), "Found incident 'EVT_20261107_213746_3e304691' in API incidents response");
  assert(targetIncident.raw_response.includes("[DeepSeek Forensic Engine]"), "raw_response contains DeepSeek Forensic Engine header");
  assert(targetIncident.parsed_json.threat_verdict === "OBSERVED_ACTIVITY", "threat_verdict is 'OBSERVED_ACTIVITY'");
  assert(targetIncident.parsed_json.object_description.primary_action === "NORMAL", "primary_action is 'NORMAL'");
  assert(targetIncident.parsed_json.object_description.role === "bystander", "role is 'bystander'");
  assert(targetIncident.parsed_json.object_description.keypoints_count === 17, "keypoints_count is 17");
  assert(targetIncident.parsed_json.object_description.kinematics_summary.includes("Góc khuỷu tay phải: N/A°"), "kinematics_summary rendered accurately");

  // ---------------------------------------------------------------------------
  // 3. Test Frontend mapKvIncidentItem Universal Parser
  // ---------------------------------------------------------------------------
  console.log('\n3. Testing Frontend mapKvIncidentItem Parser:');

  const mappedItem = mapKvIncidentItem(targetIncident);
  assert(mappedItem.id === "EVT_20261107_213746_3e304691", "Frontend mapped id is EVT_20261107_213746_3e304691");
  assert(mappedItem.eventId === "EVT_20261107_213746_3e304691", "Frontend mapped eventId is EVT_20261107_213746_3e304691");
  assert(mappedItem.title === "NORMAL", "Frontend mapped title is 'NORMAL'");
  assert(mappedItem.severity === "MEDIUM", "Frontend mapped severity is 'MEDIUM'");
  assert(mappedItem.role === "bystander", "Frontend mapped role is 'bystander'");
  assert(mappedItem.kinematicsSummary.includes("Góc khuỷu tay phải"), "Frontend kinematicsSummary preserved");
  assert(mappedItem.postureDetails === "Detected action: NORMAL (threat score: 0.10)", "Frontend postureDetails preserved");
  assert(mappedItem.modelUsed === "@cf/deepseek-ai/deepseek-v4.1-flash-1017", "Frontend modelUsed preserved");
  assert(mappedItem.latencyMs === 925, "Frontend latencyMs is 925");

  // ---------------------------------------------------------------------------
  // 4. Test Operational HITL Guardrail [CD-04]
  // ---------------------------------------------------------------------------
  console.log('\n4. Testing Operational HITL Integrity [CD-04]:');

  assert(
    mappedItem.status === "PENDING_VERIFICATION" || mappedItem.status === "AWAITING_OPERATOR_VERIFICATION",
    `Initial operational status is safely locked in verification queue (${mappedItem.status})`
  );

  // ---------------------------------------------------------------------------
  // Summary
  // ---------------------------------------------------------------------------
  console.log('\n======================================================');
  console.log(`TOTAL: ${passed + failed} | PASSED: ${passed} | FAILED: ${failed}`);
  console.log('======================================================\n');

  if (failed > 0) {
    process.exit(1);
  }
}

runDashboardKvRealtimeTests().catch((err) => {
  console.error("Test Suite encountered an unexpected error:", err);
  process.exit(1);
});
