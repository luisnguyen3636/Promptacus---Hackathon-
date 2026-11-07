import React, { useState } from 'react';
import { Sidebar } from './components/Sidebar.tsx';
import { TopHeader } from './components/TopHeader.tsx';
import { EvidencePlaybackModal } from './components/Modal/EvidencePlaybackModal.tsx';
import { useSocTelemetry } from './hooks/useSocTelemetry.ts';
import { IIncidentItem } from './types/soc.ts';

// Các Giao diện Tác chiến Chuyên biệt
import { DashboardView } from './components/views/DashboardView.tsx';
import { ThreatIntelligenceView } from './components/views/ThreatIntelligenceView.tsx';
import { IncidentFeedView } from './components/views/IncidentFeedView.tsx';
import { DeviceManagerView } from './components/views/DeviceManagerView.tsx';
import { SettingsView } from './components/views/SettingsView.tsx';

export const App: React.FC = () => {
  const { overview, cameras, incidents, setIncidents, isBackendConnected } = useSocTelemetry();
  const [activeTab, setActiveTab] = useState<string>('SOC Dashboard');
  const [activePlaybackIncident, setActivePlaybackIncident] = useState<IIncidentItem | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage(null);
    }, 2800);
  };

  const handlePtzCommand = async (cameraId: string, action: string) => {
    showToast(`[PTZ COMMAND] Cam: ${cameraId} -> Action: ${action}`);
    try {
      const res = await fetch(`/api/cameras/${cameraId}/ptz`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, speed: 1 }),
      });
      if (res.ok) {
        const data = await res.json();
        console.log('[PTZ RESPONSE]', data);
      }
    } catch {
      // Local fallback
    }
  };

  const handleHitlDecision = async (
    incidentId: string,
    decision: 'CONFIRM_AND_DISPATCH' | 'DOWNGRADE_MONITOR' | 'DISMISS_FALSE_POSITIVE',
    notes?: string
  ) => {
    showToast(`[HITL VERIFIED] ${decision} bởi OP-VN-SOC-804`);

    try {
      const res = await fetch(`/api/incidents/${incidentId}/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          operatorId: 'OP-VN-SOC-804',
          decision,
          notes,
          verifiedAt: new Date().toISOString(),
        }),
      });

      if (res.ok) {
        const result = await res.json();
        console.log('[HITL VERIFY RESULT]', result);
      }
    } catch {
      // Local fallback
    }

    // Cập nhật trạng thái sự cố trên giao diện
    setIncidents((prev) =>
      prev.map((item) =>
        item.id === incidentId
          ? {
              ...item,
              status: decision === 'DISMISS_FALSE_POSITIVE' ? 'DISMISSED' : 'OPERATOR_CONFIRMED',
            }
          : item
      )
    );

    setActivePlaybackIncident(null);
  };

  // Bộ định tuyến hiển thị các Tab Tác chiến
  const renderActiveView = () => {
    switch (activeTab) {
      case 'Threat Intelligence':
        return (
          <ThreatIntelligenceView
            onBlockIp={(ip) => showToast(`[SECURITY] Blocked IP: ${ip}`)}
          />
        );
      case 'Incident Feed':
        return (
          <IncidentFeedView
            incidents={incidents}
            onSelectPlayback={(inc) => setActivePlaybackIncident(inc)}
          />
        );
      case 'Device Manager':
        return (
          <DeviceManagerView
            cameras={cameras}
            onReboot={(id) => showToast(`[DEVICE] Reboot command sent: ${id}`)}
          />
        );
      case 'Settings':
        return (
          <SettingsView
            operatorId="OP-VN-SOC-804"
          />
        );
      case 'SOC Dashboard':
      default:
        return (
          <DashboardView
            overview={overview}
            cameras={cameras}
            incidents={incidents}
            onPtzCommand={handlePtzCommand}
            onSelectPlayback={(inc) => setActivePlaybackIncident(inc)}
          />
        );
    }
  };

  return (
    <div className="bg-[#080B10] text-[#F8FAFC] min-h-screen overflow-x-hidden">
      {/* 1. Sidebar Trái (240px cố định) */}
      <Sidebar activeTab={activeTab} onSelectTab={setActiveTab} />

      {/* 2. Main Viewport (Cố định chiều rộng không tràn) */}
      <div className="ml-[240px] w-[calc(100%-240px)] max-w-[calc(100%-240px)] min-h-screen flex flex-col min-w-0 overflow-x-hidden">
        {/* Top Header Bar (52px) */}
        <TopHeader
          activeTab={activeTab}
          threatScore={overview.threatScore}
          threatLevel={overview.threatLevel}
          isConnected={isBackendConnected}
        />

        {/* Nội dung Tác chiến tương ứng với Tab đang chọn */}
        <main className="p-4 sm:p-6 space-y-4 flex-1 min-w-0 overflow-x-hidden">
          {renderActiveView()}
        </main>
      </div>

      {/* Modal Bằng chứng Video & Chốt chặn Operational HITL (CD-04) */}
      <EvidencePlaybackModal
        incident={activePlaybackIncident}
        onClose={() => setActivePlaybackIncident(null)}
        onSubmitDecision={handleHitlDecision}
      />

      {/* Thông báo Toast Công nghiệp Sắc nét */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 bg-[#0E131A] border border-[#10B981] text-[#10B981] px-4 py-2.5 font-mono text-xs font-bold z-50 select-none shadow-lg">
          {toastMessage}
        </div>
      )}
    </div>
  );
};
export default App;
