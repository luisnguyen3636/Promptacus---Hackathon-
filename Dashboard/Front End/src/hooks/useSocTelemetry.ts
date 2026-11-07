import { useState, useEffect, useCallback } from 'react';
import { ISocOverview, ICameraDevice, IIncidentItem, IServerActor } from '../types/soc.ts';
import { MOCK_OVERVIEW, MOCK_CAMERAS, MOCK_INCIDENTS } from '../data/mockData.ts';

/**
 * Universal Mapper for Server JSON Logs & Cloudflare KV Incident Objects
 * Maps structured fields from the server's JSON log without any frame/image processing.
 */
export function mapKvIncidentItem(item: any): IIncidentItem {
  if (!item) {
    return {
      id: `EVT_${Date.now()}`,
      title: 'UNKNOWN',
      subTitle: '',
      sourceIp: '127.0.0.1',
      category: 'PHYSICAL_CAMERA',
      severity: 'LOW',
      timestamp: new Date().toISOString(),
      status: 'PENDING_VERIFICATION',
    };
  }

  const raw = item.rawDetection || item;
  const vlm = item.nvidiaVlmAnalysis || item.nvidia_vlm_analysis || raw.nvidia_vlm_analysis;
  const det = item.detection || raw.detection;
  const val = item.actionValidation || item.action_validation || raw.action_validation;
  const camMeta = item.cameraMeta || item.camera || raw.camera;
  const auditInfo = item.auditInfo || item.audit || raw.audit;
  const audioInfo = item.audioInfo || det?.audio;
  const weaponInfo = item.weaponInfo || item.weapon_info || raw.weapon_info || det?.weapon;
  const subjects = item.subjects || det?.subjects || [];

  const cameraId =
    item.cameraId ||
    item.camera_id ||
    camMeta?.camera_id ||
    vlm?.camera_id ||
    raw.camera_id ||
    'LAPTOP_01';

  const cameraName =
    item.cameraName ||
    item.camera_name ||
    raw.camera_name ||
    camMeta?.name ||
    cameraId;

  const location =
    item.location ||
    camMeta?.address ||
    raw.location ||
    vlm?.location ||
    item.subTitle ||
    cameraName;

  const primaryAction =
    item.primaryAction ||
    item.primary_action ||
    raw.primary_action ||
    det?.primary_action ||
    val?.detected_action ||
    item.actionType ||
    item.action_type ||
    vlm?.action_type ||
    'OBSERVED_EVENT';

  const valReasoning = val?.reasoning;
  const rawReasoning = item.reasoning || raw.reasoning || det?.reasoning || vlm?.reasoning;

  const description =
    item.description ||
    raw.description ||
    valReasoning ||
    weaponInfo?.description ||
    vlm?.description ||
    rawReasoning ||
    item.title ||
    primaryAction;

  const reasoning = rawReasoning || valReasoning || description;
  const vlmAnalysis =
    item.vlmAnalysis ||
    raw.vlmAnalysis ||
    (valReasoning && rawReasoning && valReasoning !== rawReasoning
      ? `${valReasoning} | ${rawReasoning}`
      : valReasoning || rawReasoning || description);

  const rawSeverity = String(
    item.severity ||
      raw.severity ||
      item.threatLevel ||
      raw.threat_level ||
      det?.threat_level ||
      val?.severity ||
      vlm?.severity ||
      'MEDIUM'
  ).toUpperCase();

  const severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' =
    ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].includes(rawSeverity)
      ? (rawSeverity as any)
      : 'MEDIUM';

  const threatScore =
    item.threatScore !== undefined
      ? Number(item.threatScore)
      : item.threat_score !== undefined
      ? Number(item.threat_score)
      : det?.threat_score !== undefined
      ? Number(det.threat_score)
      : val?.threat_score !== undefined
      ? Number(val.threat_score)
      : vlm?.threat_score !== undefined
      ? Number(vlm.threat_score)
      : undefined;

  const confidence =
    item.confidence !== undefined
      ? Number(item.confidence)
      : weaponInfo?.confidence !== undefined
      ? Number(weaponInfo.confidence)
      : subjects[0]?.confidence !== undefined
      ? Number(subjects[0].confidence)
      : vlm?.confidence !== undefined
      ? Number(vlm.confidence)
      : undefined;

  const isUrgent =
    item.isUrgent !== undefined
      ? Boolean(item.isUrgent)
      : item.is_urgent !== undefined
      ? Boolean(item.is_urgent)
      : det?.is_urgent !== undefined
      ? Boolean(det.is_urgent)
      : vlm?.is_urgent !== undefined
      ? Boolean(vlm.is_urgent)
      : severity === 'CRITICAL';

  const actionConfirmed = Boolean(
    item.actionConfirmed ??
      item.action_confirmed ??
      raw.action_confirmed ??
      det?.action_confirmed ??
      auditInfo?.action_confirmed ??
      val?.is_valid
  );

  const aiVerified = Boolean(
    item.aiVerified ??
      item.ai_verified ??
      raw.ai_verified ??
      det?.ai_verified ??
      auditInfo?.ai_verified ??
      val?.is_valid
  );

  const recommendedAction =
    item.recommendedAction ||
    item.recommended_action ||
    vlm?.recommended_action ||
    (isUrgent ? 'DISPATCH_SECURITY' : 'MONITOR');

  const rawActors = Array.isArray(item.actors)
    ? item.actors
    : Array.isArray(raw.actors)
    ? raw.actors
    : Array.isArray(vlm?.actors)
    ? vlm.actors
    : [];

  const actors: IServerActor[] =
    rawActors.length > 0
      ? rawActors.map((a: any, idx: number) => ({
          id: a?.id ?? a?.track_id ?? idx + 1,
          role: String(a?.role || 'suspect'),
          action: String(a?.action || a?.behavior || primaryAction || 'OBSERVED'),
          posture: String(a?.posture || weaponInfo?.description || ''),
          interacting_with: a?.interacting_with ?? null,
          bbox: Array.isArray(a?.bbox) ? a.bbox : undefined,
        }))
      : subjects.map((sub: any, idx: number) => {
          const kin = sub?.kinematics;
          const postureStr = kin
            ? `Spine: ${kin.spine_angle ?? 0}°, L-Elbow: ${kin.left_elbow_angle ?? 0}°, R-Elbow: ${kin.right_elbow_angle ?? 0}°, L-ArmExt: ${kin.left_arm_extension ?? 0}, R-ArmExt: ${kin.right_arm_extension ?? 0} (Speed: ${sub?.speed ?? 0})`
            : weaponInfo?.description || `Behavior: ${sub?.behavior || primaryAction}`;
          return {
            id: sub?.track_id ?? sub?.id ?? idx + 1,
            role: String(sub?.role || 'suspect'),
            action: String(sub?.behavior || sub?.action || primaryAction),
            posture: String(postureStr),
            bbox: Array.isArray(sub?.bbox) ? sub.bbox : undefined,
          };
        });

  const visualCues =
    item.visualCues ||
    item.visual_cues ||
    raw.visual_cues ||
    vlm?.visual_cues || {
      weapons_visible: Boolean(
        weaponInfo?.is_weapon_detected ||
          primaryAction.includes('WEAPON') ||
          (weaponInfo?.weapon_types && weaponInfo.weapon_types.length > 0)
      ),
      physical_contact: Boolean(
        primaryAction.includes('FIGHT') || primaryAction.includes('ASSAULT')
      ),
      fallen_person: Boolean(primaryAction.includes('FALL')),
    };

  const measuredFps =
    item.measuredFps !== undefined
      ? Number(item.measuredFps)
      : item.measured_fps !== undefined
      ? Number(item.measured_fps)
      : undefined;

  const frameIndex =
    item.frameIndex !== undefined
      ? Number(item.frameIndex)
      : auditInfo?.frame_index !== undefined
      ? Number(auditInfo.frame_index)
      : item.frame_index !== undefined
      ? Number(item.frame_index)
      : undefined;

  const humanCount =
    item.humanCount !== undefined
      ? Number(item.humanCount)
      : auditInfo?.human_count !== undefined
      ? Number(auditInfo.human_count)
      : item.human_count !== undefined
      ? Number(item.human_count)
      : subjects.length > 0
      ? subjects.length
      : actors.length;

  const eventId =
    item.id ||
    item.eventId ||
    item.event_id ||
    raw.event_id ||
    `EVT_${cameraId}_${frameIndex ?? Date.now()}`;

  const forensicSha256 =
    item.forensicSha256 ||
    item.forensic_hash ||
    raw.forensic_hash ||
    subjects[0]?.crop_image_sha256;

  const firstKin = subjects[0]?.kinematics;
  const kinematicsSummary = firstKin
    ? `Spine: ${firstKin.spine_angle ?? 0}° · L/R Elbow: ${firstKin.left_elbow_angle ?? 0}°/${firstKin.right_elbow_angle ?? 0}° · L/R Arm Ext: ${firstKin.left_arm_extension ?? 0}/${firstKin.right_arm_extension ?? 0}`
    : undefined;

  const title = item.title || raw.title || `Cảnh báo: ${primaryAction} (${severity})`;

  return {
    id: eventId,
    eventId,
    title,
    subTitle: `${cameraName} • ${location}`,
    sourceIp: item.sourceIp || cameraId,
    category: 'PHYSICAL_CAMERA',
    severity,
    timestamp: item.timestamp || raw.timestamp || vlm?.timestamp || new Date().toISOString(),
    timestampMs: item.timestampMs || item.timestamp_ms || raw.timestamp_ms,
    cameraId,
    cameraName,
    location,
    measuredFps,
    frameIndex,
    humanCount,
    actionType: primaryAction,
    primaryAction,
    threatLevel: severity,
    threatScore,
    confidence,
    isUrgent,
    actionConfirmed,
    aiVerified,
    actionValidation: val,
    weaponInfo,
    description,
    reasoning,
    recommendedAction,
    actors,
    visualCues,
    nvidiaVlmAnalysis: vlm,
    cameraSnapshots: null,
    playbackUrl: null,
    status: item.status || item.operator_status || 'PENDING_VERIFICATION',
    vlmAnalysis,
    rawResponse: reasoning,
    forensicSha256,
    subjects,
    cameraMeta: camMeta,
    auditInfo,
    audioInfo,
    threatVerdict: recommendedAction,
    role: subjects[0]?.role || actors[0]?.role,
    postureDetails: weaponInfo?.description || actors[0]?.posture || description,
    kinematicsSummary,
    weaponDetected: weaponInfo?.weapon_types?.join(', ') || null,
    weaponConfidence: weaponInfo?.confidence,
    keypointsCount: subjects[0]?.keypoints?.length,
    modelUsed: auditInfo?.ai_model || val?.validation_source,
  };
}

export function useSocTelemetry() {
  const [overview, setOverview] = useState<ISocOverview>(MOCK_OVERVIEW);
  const [cameras, setCameras] = useState<ICameraDevice[]>(MOCK_CAMERAS);
  const [incidents, setIncidents] = useState<IIncidentItem[]>(MOCK_INCIDENTS);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isBackendConnected, setIsBackendConnected] = useState<boolean>(false);

  const fetchData = useCallback(async () => {
    try {
      const resOverview = await fetch('/api/soc/overview', { signal: AbortSignal.timeout(2000) });
      if (resOverview.ok) {
        const data = await resOverview.json();
        setOverview(data);
        setIsBackendConnected(true);
      }
    } catch {
      setIsBackendConnected(false);
    }

    try {
      const resCameras = await fetch('/api/devices/cameras', { signal: AbortSignal.timeout(2000) });
      if (resCameras.ok) {
        const data = await resCameras.json();
        if (Array.isArray(data)) {
          setCameras(data);
        }
      }
    } catch {
      // Keep current state
    }

    try {
      const resIncidents = await fetch('/api/get-incident', { signal: AbortSignal.timeout(2000) });
      if (resIncidents.ok) {
        const result = await resIncidents.json();
        if (result && Array.isArray(result.incidents)) {
          setIncidents(result.incidents.map(mapKvIncidentItem));
        } else if (Array.isArray(result)) {
          setIncidents(result.map(mapKvIncidentItem));
        } else if (result && (result.id || result.event_id || result.camera_id)) {
          setIncidents([mapKvIncidentItem(result)]);
        }
      }
    } catch {
      // Keep current state
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const cycle = setInterval(fetchData, 1000);
    return () => clearInterval(cycle);
  }, [fetchData]);

  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimeout: ReturnType<typeof setTimeout>;

    function connectWs() {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws/live-stream`;

      try {
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
          setIsBackendConnected(true);
        };

        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data);
            if (msg.type === 'TELEMETRY_AND_AI_TICK' && Array.isArray(msg.cameras)) {
              setCameras(msg.cameras);
            } else if (msg.type === 'NEW_INCIDENT' && msg.incident) {
              const mapped = mapKvIncidentItem(msg.incident);
              setIncidents((prev) => [mapped, ...prev.filter((i) => i.id !== mapped.id)]);
              fetchData();
            }
          } catch {
            // Ignore malformed message
          }
        };

        ws.onerror = () => {
          ws?.close();
        };

        ws.onclose = () => {
          reconnectTimeout = setTimeout(connectWs, 3000);
        };
      } catch {
        reconnectTimeout = setTimeout(connectWs, 3000);
      }
    }

    connectWs();

    return () => {
      if (ws) ws.close();
      clearTimeout(reconnectTimeout);
    };
  }, [fetchData]);

  return {
    overview,
    cameras,
    setCameras,
    incidents,
    setIncidents,
    isLoading,
    isBackendConnected,
    refreshData: fetchData,
  };
}
