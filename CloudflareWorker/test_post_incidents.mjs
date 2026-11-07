// Verification test for POST /api/incidents and immutable audit log recording

const BASE_URL = 'http://127.0.0.1:8787';

async function waitForServer(retries = 15, delayMs = 1000) {
  for (let i = 0; i < retries; i++) {
    try {
      const res = await fetch(`${BASE_URL}/api/soc/overview`);
      if (res.ok) return true;
    } catch (e) {
      // wait
    }
    await new Promise(r => setTimeout(r, delayMs));
  }
  throw new Error('Server did not start up in time');
}

async function testPostIncidents() {
  console.log('=== TEST SUITE: POST /api/incidents LOG RECORDING ===\n');

  console.log('Waiting for local Cloudflare Worker to be ready...');
  await waitForServer();
  console.log('Worker is online!\n');

  // Test Case 1: Generic Incident Post
  console.log('1. Testing POST /api/incidents with Generic Alert Payload...');
  const genericPayload = {
    incident_id: `INC_TEST_${Date.now()}`,
    title: "Phát hiện đối tượng leo rào đột nhập",
    severity: "HIGH",
    camera_id: "CAM_PERIMETER_NORTH",
    zone_id: "ZONE_PERIMETER",
    location_name: "Hàng Rào Phía Bắc",
    description: "Phát hiện chuyển động và dáng người bất thường tiếp cận hàng rào lúc nửa đêm",
    evidence_url: "https://example.com/evidence/snapshot_north_fence.jpg"
  };

  const res1 = await fetch(`${BASE_URL}/api/incidents`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(genericPayload)
  });

  console.log('   Response Status:', res1.status);
  const data1 = await res1.json();
  console.log('   Response Body:', JSON.stringify(data1, null, 2));

  if (res1.status !== 201) {
    throw new Error(`Expected HTTP 201, got ${res1.status}`);
  }
  if (!data1.success || data1.status !== 'RECORDED_AS_LOG') {
    throw new Error('Failed to record incident as log');
  }
  if (data1.operator_status !== 'AWAITING_OPERATOR_VERIFICATION') {
    throw new Error('Violated CD-04: Incident must require operator verification');
  }
  if (!data1.log_id || !data1.incident_id) {
    throw new Error('Missing log_id or incident_id in response');
  }

  // Test Case 2: Verify Log exists in Audit Trail
  console.log('\n2. Verifying Immutable Log in GET /api/soc/audit-logs ...');
  const resAudit = await fetch(`${BASE_URL}/api/soc/audit-logs`);
  const logs = await resAudit.json();
  console.log(`   Fetched ${logs.length} audit log(s)`);

  const matchingLog = logs.find(l => l.incident_id === genericPayload.incident_id || l.incidentId === genericPayload.incident_id);
  if (!matchingLog) {
    throw new Error(`Audit log for incident ${genericPayload.incident_id} not found in audit logs!`);
  }
  console.log('   Matched Audit Log Entry:', matchingLog);

  // Test Case 3: Verify Incident Vault reflects PENDING_VERIFICATION state
  console.log('\n3. Verifying Incident in GET /api/incidents/recent ...');
  const resIncidents = await fetch(`${BASE_URL}/api/incidents/recent`);
  const incidents = await resIncidents.json();
  const foundIncident = incidents.find(i => i.id === genericPayload.incident_id);
  if (!foundIncident) {
    throw new Error(`Incident ${genericPayload.incident_id} not found in recent incidents!`);
  }
  console.log('   Matched Incident Entry:', {
    id: foundIncident.id,
    title: foundIncident.title,
    severity: foundIncident.severity,
    status: foundIncident.status,
    vlmAnalysis: foundIncident.vlmAnalysis
  });
  if (foundIncident.status !== 'PENDING_VERIFICATION') {
    throw new Error(`Expected status PENDING_VERIFICATION, got ${foundIncident.status}`);
  }

  // Test Case 4: Test with real AI Detection Payload
  console.log('\n4. Testing POST /api/incidents with AI Detection Payload...');
  const aiPayload = {
    event_id: `EVT_POST_INC_${Date.now()}`,
    timestamp: new Date().toISOString(),
    camera: {
      camera_id: "CAM_SOUTH_GATE",
      name: "Cổng Nam",
      zone_id: "ZONE_SOUTH",
      address: "123 Đường Nam Kỳ Khởi Nghĩa",
      latitude: 10.77,
      longitude: 106.70
    },
    detection: {
      primary_action: "VIOLENT_CLASH",
      threat_level: "HIGH",
      threat_score: 0.88,
      reasoning: "Phát hiện ẩu đả có nguy cơ gây thương tích",
      weapon: { is_weapon_detected: false, weapon_types: [], confidence: 0, description: "" },
      subjects: [],
      full_image: { format: "jpeg", width: 640, height: 480, image_base64: "data:image/jpeg;base64,123", sha256_hash: "abc", image_size_bytes: 100 }
    }
  };

  const res2 = await fetch(`${BASE_URL}/api/incidents`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(aiPayload)
  });
  console.log('   Status Code:', res2.status);
  const data2 = await res2.json();
  console.log('   AI Detection Ingested via /api/incidents:', {
    success: data2.success,
    log_id: data2.log_id,
    incident_id: data2.incident_id,
    status: data2.status
  });

  if (res2.status !== 201 || !data2.success) {
    throw new Error('Failed to ingest AI detection via /api/incidents');
  }

  console.log('\n=== ALL POST /api/incidents TESTS PASSED! ===\n');
}

testPostIncidents().catch(err => {
  console.error('\n❌ TEST FAILED:', err);
  process.exit(1);
});
