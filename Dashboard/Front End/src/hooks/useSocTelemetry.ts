import { useState, useEffect, useCallback } from 'react';
import { ISocOverview, ICameraDevice, IIncidentItem } from '../types/soc.ts';
import { MOCK_OVERVIEW, MOCK_CAMERAS, MOCK_INCIDENTS } from '../data/mockData.ts';

/**
 * Universal Mapper for Server JSON & Cloudflare KV Incident Objects
 * Maps all fields from the server's JSON format:
 * { status, camera_id, location, timestamp, measured_fps, frame_index, human_count,
 *   severity, action_type, threat_score, confidence, is_urgent, description,
 *   reasoning, recommended_action, actors, visual_cues, nvidia_vlm_analysis }
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
  const parsed = item.parsed_json || {};
  const objDesc = parsed.object_description || item.object_description || {};

  const cameraId =
    item.cameraId ||
    item.camera_id ||
    vlm?.camera_id ||
    raw.camera_id ||
    'LAPTOP_01';

  const location =
    item.location ||
    item.subTitle ||
    raw.location ||
    vlm?.location ||
    item.location_name ||
    cameraId;

  const actionType =
    item.actionType ||
    item.action_type ||
    vlm?.action_type ||
    objDesc.primary_action ||
    item.title ||
    'OBSERVED_EVENT';

  const description =
    item.description ||
    raw.description ||
    vlm?.description ||
    parsed.investigation_summary ||
    item.title ||
    actionType;

  const reasoning =
    item.reasoning ||
    raw.reasoning ||
    vlm?.reasoning ||
    item.vlmAnalysis ||
    description;

  const rawSeverity = String(
    item.severity || raw.severity || vlm?.severity || parsed.severity || 'MEDIUM'
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
      : vlm?.threat_score !== undefined
      ? Number(vlm.threat_score)
      : undefined;

  const confidence =
    item.confidence !== undefined
      ? Number(item.confidence)
      : vlm?.confidence !== undefined
      ? Number(vlm.confidence)
      : undefined;

  const isUrgent =
    item.isUrgent !== undefined
      ? Boolean(item.isUrgent)
      : item.is_urgent !== undefined
      ? Boolean(item.is_urgent)
      : vlm?.is_urgent !== undefined
      ? Boolean(vlm.is_urgent)
      : severity === 'CRITICAL';

  const recommendedAction =
    item.recommendedAction ||
    item.recommended_action ||
    vlm?.recommended_action ||
    (isUrgent ? 'DISPATCH_SECURITY' : 'MONITOR');

  const actors = item.actors || raw.actors || vlm?.actors || [];
  const visualCues = item.visualCues || item.visual_cues || raw.visual_cues || vlm?.visual_cues;

  const measuredFps =
    item.measuredFps !== undefined
      ? Number(item.measuredFps)
      : item.measured_fps !== undefined
      ? Number(item.measured_fps)
      : undefined;

  const frameIndex =
    item.frameIndex !== undefined
      ? Number(item.frameIndex)
      : item.frame_index !== undefined
      ? Number(item.frame_index)
      : undefined;

  const humanCount =
    item.humanCount !== undefined
      ? Number(item.humanCount)
      : item.human_count !== undefined
      ? Number(item.human_count)
      : actors.length;

  const eventId =
    item.id ||
    item.eventId ||
    item.event_id ||
    `EVT_${cameraId}_${frameIndex ?? Date.now()}`;

  const actorPostures = actors
    .map((a: any) => `#${a.id} (${a.role}): ${a.action} - ${a.posture}`)
    .join(' | ');

  const title = item.title || `${actionType} — ${description}`;

  return {
    id: eventId,
    eventId,
    title,
    subTitle: location,
    sourceIp: item.sourceIp || cameraId,
    category: 'PHYSICAL_CAMERA',
    severity,
    timestamp: item.timestamp || vlm?.timestamp || new Date().toISOString(),
    cameraId,
    location,
    measuredFps,
    frameIndex,
    humanCount,
    actionType,
    threatScore,
    confidence,
    isUrgent,
    description,
    reasoning,
    recommendedAction,
    actors,
    visualCues,
    nvidiaVlmAnalysis: vlm,
    cameraSnapshots: item.cameraSnapshots || null,
    playbackUrl: item.playbackUrl || null,
    status: item.status || item.operator_status || 'PENDING_VERIFICATION',
    vlmAnalysis: reasoning || description,
    rawResponse: reasoning,
    threatVerdict: recommendedAction,
    role: actors[0]?.role || objDesc.role,
    postureDetails: actorPostures || objDesc.posture_details || description,
    kinematicsSummary: visualCues
      ? `Vũ khí: ${visualCues.weapons_visible ? 'CÓ' : 'Không'} · Va chạm vật lý: ${
          visualCues.physical_contact ? 'CÓ' : 'Không'
        } · Người ngã: ${visualCues.fallen_person ? 'CÓ' : 'Không'}`
      : undefined,
    fullImageBase64: item.fullImageBase64 || null,
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
      // Giữ state hiện tại
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
      // Giữ state hiện tại
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
