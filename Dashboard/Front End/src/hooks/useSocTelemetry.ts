import { useState, useEffect, useCallback } from 'react';
import { ISocOverview, ICameraDevice, IIncidentItem } from '../types/soc.ts';
import { MOCK_OVERVIEW, MOCK_CAMERAS, MOCK_INCIDENTS } from '../data/mockData.ts';

/**
 * Universal Mapper for Cloudflare KV Incident Objects
 * Perfectly extracts flat properties and nested parsed_json fields matching DeepSeek KV output:
 * { event_id, raw_response, parsed_json, model_used, latency_ms, timestamp }
 */
export function mapKvIncidentItem(item: any): IIncidentItem {
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
  const severity = (parsed.severity || item.severity || 'MEDIUM').toUpperCase() as any;
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

export function useSocTelemetry() {
  const [overview, setOverview] = useState<ISocOverview>(MOCK_OVERVIEW);
  const [cameras, setCameras] = useState<ICameraDevice[]>(MOCK_CAMERAS);
  const [incidents, setIncidents] = useState<IIncidentItem[]>(MOCK_INCIDENTS);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isBackendConnected, setIsBackendConnected] = useState<boolean>(false);

  // 1. Fetch REST Telemetry
  const fetchData = useCallback(async () => {
    try {
      const resOverview = await fetch('/api/soc/overview', { signal: AbortSignal.timeout(1500) });
      if (resOverview.ok) {
        const data = await resOverview.json();
        setOverview(data);
        setIsBackendConnected(true);
      }
    } catch {
      setIsBackendConnected(false);
    }

    try {
      const resCameras = await fetch('/api/devices/cameras', { signal: AbortSignal.timeout(1500) });
      if (resCameras.ok) {
        const data = await resCameras.json();
        setCameras(data);
      }
    } catch {
      // Giữ state hiện tại
    }

    try {
      // Continuous polling for DeepSeek analyzed incidents from Cloudflare KV
      const resIncidents = await fetch('/api/get-incident', { signal: AbortSignal.timeout(1500) });
      if (resIncidents.ok) {
        const result = await resIncidents.json();

        if (result && Array.isArray(result.incidents) && result.incidents.length > 0) {
          const mapped = result.incidents.map(mapKvIncidentItem);
          setIncidents(mapped);
        } else if (Array.isArray(result) && result.length > 0) {
          const mapped = result.map(mapKvIncidentItem);
          setIncidents(mapped);
        } else if (result && (result.event_id || result.parsed_json)) {
          const mapped = [mapKvIncidentItem(result)];
          setIncidents(mapped);
        } else {
          // Fallback if no deepseek incidents yet
          const resFallback = await fetch('/api/incidents/recent', { signal: AbortSignal.timeout(1500) });
          if (resFallback.ok) {
            const data = await resFallback.json();
            if (Array.isArray(data) && data.length > 0) {
              setIncidents(data.map(mapKvIncidentItem));
            }
          }
        }
      }
    } catch {
      // Giữ state hiện tại
    } finally {
      setIsLoading(false);
    }
  }, []);

  // 2. Chu kỳ REST Polling tối ưu 1000ms (1s Realtime KV Sync)
  useEffect(() => {
    fetchData();
    const cycle = setInterval(fetchData, 1000);
    return () => clearInterval(cycle);
  }, [fetchData]);

  // 3. Kết nối WebSocket Live AI Tracking Stream
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
            // Bỏ qua gói tin lỗi
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
