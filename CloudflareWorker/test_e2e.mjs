// E2E Verification test for AI Ingestion and Operational HITL

const BASE_URL = 'http://127.0.0.1:8787';

const sampleAiPayload = {
  "event_id": "EVT_20261107_171500_LAPTOP_TEST",
  "timestamp": "2026-11-07T17:15:00.123+07:00",
  "timestamp_ms": 1794046500123,
  "camera": {
    "camera_id": "LAPTOP_TEST",
    "name": "Laptop Test (test)",
    "zone_id": "ZONE_PORT_EAST",
    "address": "Cổng Phía Đông - Tòa Nhà Trung Tâm",
    "latitude": 10.776889,
    "longitude": 106.700806
  },
  "detection": {
    "primary_action": "WEAPON_THREAT",
    "threat_level": "CRITICAL",
    "threat_score": 0.96,
    "is_urgent": true,
    "reasoning": "Direct one-handed weapon pointing posture (right arm fully extended at 168°)",
    "weapon": {
      "is_weapon_detected": true,
      "weapon_types": [
        "FIREARM_TACTICAL_STANCE"
      ],
      "confidence": 0.94,
      "description": "Tactical weapon isosceles triangle posture"
    },
    "subjects": [
      {
        "track_id": 5,
        "role": "suspect",
        "behavior": "WEAPON_THREAT",
        "threat_level": "CRITICAL",
        "threat_score": 0.96,
        "confidence": 0.945,
        "bbox": [120, 80, 320, 460],
        "bbox_geometry": {
          "width": 200,
          "height": 380,
          "aspect_ratio": 1.9,
          "area": 76000
        },
        "dwell_time_seconds": 4.5,
        "speed": 0.05,
        "velocity_vector": [0.02, -0.01],
        "kinematics": {
          "spine_angle": 12.5,
          "aspect_ratio": 1.9,
          "left_elbow_angle": 85.0,
          "right_elbow_angle": 168.0,
          "left_arm_extension": 0.15,
          "right_arm_extension": 0.38,
          "wrist_distance": 0.18,
          "wrist_velocity": 450.0
        },
        "keypoints": [
          {"id": 0, "name": "nose", "x": 220.5, "y": 110.2, "confidence": 0.98},
          {"id": 1, "name": "left_eye", "x": 215.0, "y": 105.0, "confidence": 0.95},
          {"id": 2, "name": "right_eye", "x": 226.0, "y": 105.0, "confidence": 0.96},
          {"id": 3, "name": "left_ear", "x": 205.0, "y": 112.0, "confidence": 0.91},
          {"id": 4, "name": "right_ear", "x": 235.0, "y": 112.0, "confidence": 0.92},
          {"id": 5, "name": "left_shoulder", "x": 185.0, "y": 155.0, "confidence": 0.94},
          {"id": 6, "name": "right_shoulder", "x": 255.0, "y": 155.0, "confidence": 0.95},
          {"id": 7, "name": "left_elbow", "x": 170.0, "y": 210.0, "confidence": 0.89},
          {"id": 8, "name": "right_elbow", "x": 275.0, "y": 195.0, "confidence": 0.93},
          {"id": 9, "name": "left_wrist", "x": 190.0, "y": 240.0, "confidence": 0.88},
          {"id": 10, "name": "right_wrist", "x": 305.0, "y": 190.0, "confidence": 0.92},
          {"id": 11, "name": "left_hip", "x": 195.0, "y": 290.0, "confidence": 0.87},
          {"id": 12, "name": "right_hip", "x": 245.0, "y": 290.0, "confidence": 0.88},
          {"id": 13, "name": "left_knee", "x": 190.0, "y": 380.0, "confidence": 0.85},
          {"id": 14, "name": "right_knee", "x": 250.0, "y": 380.0, "confidence": 0.86},
          {"id": 15, "name": "left_ankle", "x": 190.0, "y": 455.0, "confidence": 0.82},
          {"id": 16, "name": "right_ankle", "x": 250.0, "y": 455.0, "confidence": 0.83}
        ],
        "crop_image_base64": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAAAAAAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA=",
        "crop_image_sha256": "c8f5e1a2b3c4d5e6f708192a3b4c5d6e7f8091a2b3c4d5e6f708192a3b4c5d6e",
        "crop_image_size_bytes": 18450
      }
    ],
    "full_image": {
      "format": "jpeg",
      "width": 640,
      "height": 480,
      "image_base64": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAAAAAAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA=",
      "sha256_hash": "f655d7b9cff20563124588c651cf3e17b67aa0c627f0811d99709b8c7f2c2111",
      "image_size_bytes": 42100
    },
    "audio": {
      "screaming_detected": false,
      "gunshot_detected": false,
      "decibel_peak": 45.2
    }
  },
  "audit": {
    "verification_status": "AI_AUTO_DETECTED_PENDING_SOC_CONFIRMATION",
    "human_count": 1,
    "pipeline_version": "2.0.0"
  }
};

async function runTests() {
  console.log('=== STARTING E2E VERIFICATION SUITE ===\n');

  // Test 1: Check initial overview (should have 0 threats or default state)
  console.log('1. Checking GET /api/soc/overview ...');
  const resOverviewInitial = await fetch(`${BASE_URL}/api/soc/overview`);
  const dataOverviewInitial = await resOverviewInitial.json();
  console.log('   Initial Overview:', JSON.stringify(dataOverviewInitial));

  // Test 2: Ingest AI Detection
  console.log('\n2. Posting AI detection to POST /api/v1/ai/detection ...');
  const resIngest = await fetch(`${BASE_URL}/api/v1/ai/detection`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(sampleAiPayload)
  });
  console.log('   Status Code:', resIngest.status);
  const dataIngest = await resIngest.json();
  console.log('   Ingest Response:', JSON.stringify(dataIngest, null, 2));

  if (resIngest.status !== 201) {
    throw new Error(`Ingest failed with status ${resIngest.status}`);
  }
  if (dataIngest.operator_status !== 'AWAITING_OPERATOR_VERIFICATION') {
    throw new Error(`Invalid operator_status: ${dataIngest.operator_status}`);
  }

  // Test 3: Check Cameras List
  console.log('\n3. Checking GET /api/devices/cameras ...');
  const resCameras = await fetch(`${BASE_URL}/api/devices/cameras`);
  const dataCameras = await resCameras.json();
  console.log(`   Found ${dataCameras.length} camera(s) registered`);
  const registeredCam = dataCameras.find(c => c.id === 'LAPTOP_TEST');
  if (!registeredCam) {
    throw new Error('Camera LAPTOP_TEST was not upserted into dynamic camera fleet!');
  }
  console.log('   Registered Camera Info:', {
    id: registeredCam.id,
    name: registeredCam.name,
    zoneId: registeredCam.zoneId,
    status: registeredCam.status,
    activeTracksCount: registeredCam.boundingBoxes?.length,
    hasSnapshot: registeredCam.lastSnapshotBase64 ? true : false,
    boundingBoxesCount: registeredCam.boundingBoxes?.length
  });

  // Test 4: Check Recent Incidents
  console.log('\n4. Checking GET /api/incidents/recent ...');
  const resIncidents = await fetch(`${BASE_URL}/api/incidents/recent`);
  const dataIncidents = await resIncidents.json();
  console.log(`   Found ${dataIncidents.length} incident(s)`);
  const createdIncident = dataIncidents.find(i => i.id === 'EVT_20261107_171500_LAPTOP_TEST');
  if (!createdIncident) {
    throw new Error('Incident EVT_20261107_171500_LAPTOP_TEST not found in recent list!');
  }
  console.log('   Incident Details:', {
    id: createdIncident.id,
    title: createdIncident.title,
    severity: createdIncident.severity,
    status: createdIncident.status,
    vlmAnalysis: createdIncident.vlmAnalysis,
    hasSnapshot: !!createdIncident.fullImageBase64,
    hasCropImage: !!createdIncident.subjects?.[0]?.crop_image_base64
  });

  // Test 5: Check SOC Overview (Dynamic Threat Scoring)
  console.log('\n5. Checking GET /api/soc/overview after detection ...');
  const resOverviewAfter = await fetch(`${BASE_URL}/api/soc/overview`);
  const dataOverviewAfter = await resOverviewAfter.json();
  console.log('   Updated SOC Overview:', {
    threatScore: dataOverviewAfter.threatScore,
    threatLevel: dataOverviewAfter.threatLevel,
    openThreats: dataOverviewAfter.metrics?.openThreats,
    criticalThreats: dataOverviewAfter.metrics?.criticalThreats
  });
  if (dataOverviewAfter.threatLevel !== 'CRITICAL') {
    throw new Error(`Expected threatLevel CRITICAL, got ${dataOverviewAfter.threatLevel}`);
  }

  // Test 6: Operational HITL Verification (Operator Confirm and Dispatch)
  console.log('\n6. Testing Operational HITL via POST /api/incidents/EVT_20261107_171500_LAPTOP_TEST/verify ...');
  const resVerify = await fetch(`${BASE_URL}/api/incidents/EVT_20261107_171500_LAPTOP_TEST/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      decision: 'CONFIRM_AND_DISPATCH',
      operatorId: 'OPERATOR_SOC_CHIEF_01',
      notes: 'Confirmed tactical weapon threat at East Gate. Dispatching Rapid Response Team.'
    })
  });
  console.log('   Status Code:', resVerify.status);
  const dataVerify = await resVerify.json();
  console.log('   HITL Verify Response:', JSON.stringify(dataVerify, null, 2));

  if (resVerify.status !== 200 || !dataVerify.success) {
    throw new Error('HITL verification failed!');
  }
  if (!dataVerify.incidentPackage) {
    throw new Error('No incidentPackage generated upon operator confirmation!');
  }
  console.log('   Dispatch Package Summary:', {
    incidentId: dataVerify.incidentPackage.incidentId,
    timestamp: dataVerify.incidentPackage.timestamp,
    camera: dataVerify.incidentPackage.camera,
    threatAssessment: dataVerify.incidentPackage.threatAssessment,
    dispatchStatus: dataVerify.incidentPackage.dispatchStatus,
    evidenceImages: {
      hasAnnotatedSnapshot: !!dataVerify.incidentPackage.visualEvidence.annotatedSnapshot,
      hasSubjectCrop: !!dataVerify.incidentPackage.visualEvidence.subjectCrop
    }
  });

  // Test 7: Verify Audit Trail
  console.log('\n7. Checking GET /api/soc/audit-logs ...');
  const resAudit = await fetch(`${BASE_URL}/api/soc/audit-logs`);
  const dataAudit = await resAudit.json();
  console.log(`   Found ${dataAudit.length} audit log entries:`);
  dataAudit.forEach((log, idx) => {
    console.log(`   [Log ${idx+1}] Action: ${log.action} | Actor: ${log.actor} | Target: ${log.targetId} | Time: ${log.timestamp}`);
  });

  console.log('\n=== ALL E2E VERIFICATION TESTS PASSED SUCCESSFULLY! ===\n');
}

runTests().catch(err => {
  console.error('\n❌ E2E VERIFICATION TEST FAILED:', err);
  process.exit(1);
});
