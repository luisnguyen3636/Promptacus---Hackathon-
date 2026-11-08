/**
 * CYBERGUARD AI · SOC v2.1 — INCIDENT & EVIDENCE ROLLING BUFFER MANAGER
 * Lưu trữ kho sự cố thời gian thực, bằng chứng ảnh crop/full và Forensic SHA-256
 */

const INITIAL_INCIDENTS = [];

let incidents = [];

export function getRecentIncidents() {
  return incidents;
}

export function getIncidentById(id) {
  return incidents.find(i => i.id === id || i.event_id === id) || null;
}

export function resetIncidents() {
  incidents = JSON.parse(JSON.stringify(INITIAL_INCIDENTS));
}

/**
 * Thêm hoặc cập nhật sự cố nhận được từ AI Detection Engine (`AI/Human`)
 */
export function addIncidentFromDetect(payload) {
  if (!payload || typeof payload !== 'object') {
    throw new Error('Invalid incident payload: Object expected');
  }

  const eventId = String(payload.event_id || payload.id || `EVT-${Date.now()}`);
  const primaryAction = String(payload.primary_action || payload.action_type || 'ANOMALY_DETECTED').toUpperCase();
  const severity = String(payload.severity || payload.threat_level || 'LOW').toUpperCase();
  
  let threatScore = 0;
  if (typeof payload.threat_score === 'number') {
    threatScore = payload.threat_score <= 1.0 ? Math.round(payload.threat_score * 100) : Math.round(payload.threat_score);
  }

  // Lấy cameraId và cameraName
  let cameraId = payload.camera_id || payload.cameraId;
  let cameraName = payload.camera_name;
  let cameraLoc = null;

  if (payload.camera && typeof payload.camera === 'object') {
    cameraId = cameraId || payload.camera.camera_id || payload.camera.id;
    cameraName = cameraName || payload.camera.name;
    cameraLoc = {
      latitude: payload.camera.latitude || 21.028511,
      longitude: payload.camera.longitude || 105.854444,
      address: payload.camera.address || 'Hà Nội Urban SOC'
    };
  }

  cameraId = String(cameraId || 'CAM_01');
  cameraName = cameraName || `Camera ${cameraId}`;

  // Chuẩn bị tiêu đề & vlm analysis
  const title = payload.title || `Cảnh báo: ${primaryAction} (${severity})`;
  const subTitle = `PHYSICAL_CAMERA / ${cameraName}`;
  const nvidiaVlmAnalysis = payload.nvidia_vlm_analysis || payload.detection?.nvidia_vlm_analysis || null;
  const nvidiaAction = String(nvidiaVlmAnalysis?.action_type || '').toUpperCase();
  const nvidiaSeverity = String(nvidiaVlmAnalysis?.severity || '').toUpperCase();
  const nvidiaSuppressed = Boolean(
    nvidiaVlmAnalysis?.false_positive_suppressed ||
    nvidiaVlmAnalysis?.anti_false_positive_audit?.false_positive_suppressed ||
    (Array.isArray(nvidiaVlmAnalysis?.evaluated_subjects) &&
      nvidiaVlmAnalysis.evaluated_subjects.some(subject => subject?.false_positive_suppressed))
  );
  const validSources = ['nvidia_nim_vlm', 'openrouter_vlm', 'local_vlm_engine', 'vlm_engine'];
  const vlmSource = String(nvidiaVlmAnalysis?.source || payload.source || '');
  const vlmStatus = String(nvidiaVlmAnalysis?.analysis_status || nvidiaVlmAnalysis?.status || payload.analysis_status || '');
  const isSourceValid = validSources.includes(vlmSource) || Boolean(nvidiaVlmAnalysis?.evaluated_subjects) || vlmSource.endsWith('_vlm');
  const isStatusValid = ['completed', 'local_only', 'processed'].includes(vlmStatus) || !vlmStatus;
  const vlmReasoning = String(
    payload.vlmAnalysis ||
    payload.reasoning ||
    nvidiaVlmAnalysis?.reasoning_summary ||
    nvidiaVlmAnalysis?.reasoning ||
    nvidiaVlmAnalysis?.description ||
    (Array.isArray(nvidiaVlmAnalysis?.evaluated_subjects) && nvidiaVlmAnalysis.evaluated_subjects[0]?.reasoning_summary) ||
    ''
  ).trim();

  const isThreatHighEnough = ['HIGH', 'CRITICAL'].includes(nvidiaSeverity) || threatScore >= 45;
  const isActionActionable = !['', 'NORMAL', 'UNKNOWN'].includes(nvidiaAction);

  const aiVerified = Boolean(
    nvidiaVlmAnalysis &&
    isSourceValid &&
    isStatusValid &&
    isThreatHighEnough &&
    isActionActionable &&
    Boolean(vlmReasoning) &&
    !nvidiaSuppressed
  );

  let aiProvider = null;
  if (aiVerified) {
    if (nvidiaVlmAnalysis?.provider) {
      aiProvider = String(nvidiaVlmAnalysis.provider);
    } else if (vlmSource.includes('openrouter')) {
      aiProvider = 'OpenRouter (Gemini-2.5-Flash)';
    } else {
      aiProvider = 'NVIDIA NIM';
    }
  }
  const vlmAnalysis = vlmReasoning || payload.vlmAnalysis || payload.reasoning || '';
  const forensicHash = payload.forensic_hash || payload.crop_image_sha256 || payload.detection?.full_image?.sha256_hash || null;

  // Ảnh bằng chứng Full & Crop
  const fullImage = payload.image_base64 || payload.image || payload.detection?.full_image?.image_base64 || null;
  const handCrop = payload.hand_crop_base64 || payload.detection?.hand_crop_image_base64 || payload.subject_crop_base64 || null;

  // Timestamp
  const now = new Date();
  const timeFormatted = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;

  const normalizedIncident = {
    id: eventId,
    event_id: eventId,
    title,
    primary_action: primaryAction,
    primaryAction: primaryAction,
    subTitle,
    sourceIp: payload.sourceIp || payload.camera?.ip || '192.168.1.100',
    category: 'PHYSICAL_CAMERA',
    severity: (severity === 'CRITICAL' ? 'CRITICAL' : severity === 'MEDIUM' ? 'MEDIUM' : severity === 'LOW' ? 'LOW' : 'HIGH'),
    threatScore,
    timestamp: payload.timestamp ? payload.timestamp.substring(11, 16) || timeFormatted : timeFormatted,
    cameraId,
    cameraSnapshots: {
      preEventSnapshotUrl: handCrop || fullImage,
      eventPeakSnapshotUrl: fullImage || handCrop
    },
    playbackUrl: payload.playbackUrl || payload.image_url || `/evidence/${eventId}.mp4`,
    status: payload.status || 'PENDING_VERIFICATION',
    vlmAnalysis,
    aiVerified,
    aiProvider: aiProvider || (aiVerified ? 'NVIDIA NIM' : null),
    nvidiaVlmAnalysis,
    forensicHash,
    weaponInfo: payload.weapon_info || payload.weapon || payload.detection?.weapon || null,
    subjects: payload.subjects || payload.detection?.subjects || [],
    cameraLocation: cameraLoc || { latitude: 21.028511, longitude: 105.854444 }
  };

  // Đưa sự cố mới lên đầu danh sách
  const existingIdx = incidents.findIndex(i => i.id === eventId);
  if (existingIdx >= 0) {
    incidents[existingIdx] = normalizedIncident;
  } else {
    incidents.unshift(normalizedIncident);
  }

  // Giữ tối đa 100 sự cố gần nhất
  if (incidents.length > 100) {
    incidents.pop();
  }

  return normalizedIncident;
}

export function getIncidentPlayback(id) {
  const inc = incidents.find(i => i.id === id || i.event_id === id);
  if (!inc) return null;

  return {
    incidentId: inc.id,
    title: inc.title,
    cameraId: inc.cameraId,
    timestamp: inc.timestamp,
    bufferRange: {
      preEventSeconds: 10,
      postEventSeconds: 10,
      totalDurationSeconds: 20
    },
    vlmReasoning: inc.vlmAnalysis,
    visualEvidence: {
      preEventSnapshot: inc.cameraSnapshots?.preEventSnapshotUrl || null,
      eventPeakSnapshot: inc.cameraSnapshots?.eventPeakSnapshotUrl || null,
      streamPlaybackUrl: inc.playbackUrl || null
    },
    forensicHash: inc.forensicHash,
    status: inc.status
  };
}

export function updateIncidentStatus(id, newStatus) {
  const inc = incidents.find(i => i.id === id || i.event_id === id);
  if (inc) {
    inc.status = newStatus;
  }
  return inc;
}
