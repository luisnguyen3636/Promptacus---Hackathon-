import { useState, useEffect, useCallback } from 'react';
import { ISocOverview, ICameraDevice, IIncidentItem } from '../types/soc.ts';
import { MOCK_OVERVIEW, MOCK_CAMERAS, MOCK_INCIDENTS } from '../data/mockData.ts';

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
      // Continuous polling for DeepSeek analyzed incidents
      const resIncidents = await fetch('/api/get-incident', { signal: AbortSignal.timeout(2000) });
      if (resIncidents.ok) {
        const result = await resIncidents.json();
        if (result && Array.isArray(result.incidents) && result.incidents.length > 0) {
          const mapped: IIncidentItem[] = result.incidents.map((item: any) => ({
            id: item.id,
            title: item.object_description?.primary_action || item.title || 'Sự cố an ninh',
            subTitle: item.location_name || item.subTitle || 'Khu vực giám sát',
            sourceIp: item.camera_id || '127.0.0.1',
            category: 'PHYSICAL_CAMERA',
            severity: item.severity || 'MEDIUM',
            timestamp: item.evidence_timeline?.event_trigger || item.timestamp || 'Vừa xong',
            cameraId: item.camera_id || null,
            cameraSnapshots: {
              eventPeakSnapshotUrl: item.visual_evidence?.snapshot_url || null,
              preEventSnapshotUrl: item.visual_evidence?.crop_url || null,
            },
            playbackUrl: item.visual_evidence?.snapshot_url || null,
            status: item.operator_status || 'PENDING_VERIFICATION',
            vlmAnalysis: item.deepseek_analysis?.investigation_summary || item.vlmAnalysis,
            fullImageBase64: item.visual_evidence?.snapshot_url || null
          }));
          setIncidents(mapped);
        } else {
          // Fallback if no deepseek incidents yet
          const resFallback = await fetch('/api/incidents/recent', { signal: AbortSignal.timeout(1500) });
          if (resFallback.ok) {
            const data = await resFallback.json();
            setIncidents(data);
          }
        }
      }
    } catch {
      // Giữ state hiện tại
    } finally {
      setIsLoading(false);
    }
  }, []);

  // 2. Chu kỳ REST Polling
  useEffect(() => {
    fetchData();
    const cycle = setInterval(fetchData, 2000);
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
              setIncidents((prev) => [msg.incident, ...prev.filter(i => i.id !== msg.incident.id)]);
              fetchData();
            }
          } catch {
            // bỏ qua gói tin lỗi
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
  }, []);

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
