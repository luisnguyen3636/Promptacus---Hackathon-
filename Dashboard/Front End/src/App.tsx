import React, { useState } from 'react';
import { Sidebar } from './components/Sidebar.tsx';
import { TopHeader } from './components/TopHeader.tsx';
import { EvidencePlaybackModal } from './components/Modal/EvidencePlaybackModal.tsx';
import { useSocTelemetry } from './hooks/useSocTelemetry.ts';
import { IIncidentItem } from './types/soc.ts';

// 6 Giao diện Tác chiến Chuyên biệt
import { DashboardView } from './components/views/DashboardView.tsx';
import { LiveVideoWallView } from './components/views/LiveVideoWallView.tsx';
import { WantedCriminalsView } from './components/views/WantedCriminalsView.tsx';
import { BlindSpotTrackingView } from './components/views/BlindSpotTrackingView.tsx';
import { IncidentFeedView } from './components/views/IncidentFeedView.tsx';
import { CameraManagerView } from './components/views/CameraManagerView.tsx';
import { SettingsView } from './components/views/SettingsView.tsx';

export const App: React.FC = () => {
  const { overview, cameras, incidents, setIncidents, isBackendConnected } = useSocTelemetry();
  const [activeTab, setActiveTab] = useState<string>('PSOC Dashboard');
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
    showToast(`[HITL VERIFIED] ${decision} bởi OP-VN-PSOC-804`);

    try {
      const res = await fetch(`/api/incidents/${incidentId}/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          operatorId: 'OP-VN-PSOC-804',
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
              status:
                decision === 'DISMISS_FALSE_POSITIVE'
                  ? 'DISMISSED'
                  : decision === 'DOWNGRADE_MONITOR'
                  ? 'DOWNGRADED_MONITORING'
                  : 'OPERATOR_CONFIRMED',
            }
          : item
      )
    );

    setActivePlaybackIncident(null);
  };

  // Bộ định tuyến hiển thị các Tab Tác chiến chuẩn hóa
  const renderActiveView = () => {
    switch (activeTab) {
      case 'Live Video Wall':
        return (
          <LiveVideoWallView
            cameras={cameras}
            onPtzCommand={handlePtzCommand}
          />
        );
      case 'Danh sách truy nã':
        return (
          <WantedCriminalsView
            incidents={incidents}
            onToast={showToast}
          />
        );
      case 'Suy luận vùng mù':
        return (
          <BlindSpotTrackingView
            onToast={showToast}
            onNavigateToWanted={() => setActiveTab('Danh sách truy nã')}
          />
        );
      case 'Incident Feed':
        return (
          <IncidentFeedView
            incidents={incidents}
            onSelectPlayback={(inc) => setActivePlaybackIncident(inc)}
          />
        );
      case 'Camera Manager':
        return (
          <CameraManagerView
            cameras={cameras}
            onPtzCommand={handlePtzCommand}
            onToast={showToast}
          />
        );
      case 'Settings':
        return (
          <SettingsView
            operatorId="OP-VN-PSOC-804"
          />
        );
      case 'PSOC Dashboard':
      default:
        return (
          <DashboardView
            overview={overview}
            cameras={cameras}
            incidents={incidents}
            onPtzCommand={handlePtzCommand}
            onSelectPlayback={(inc) => setActivePlaybackIncident(inc)}
            onHitlDecision={handleHitlDecision}
            onToast={showToast}
          />
        );
    }
  };

  return (
    <div className="bg-[#080B10] text-[#F8FAFC] min-h-screen overflow-x-hidden">
      {/* 1. Sidebar Trái (240px cố định) */}
      <Sidebar
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        wantedCount={overview.metrics?.wantedCount ?? 3}
        blindSpotCount={overview.metrics?.blindSpotSessionsCount ?? 2}
      />

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
