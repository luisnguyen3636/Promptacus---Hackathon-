import React, { useEffect, useState } from 'react';
import { Sidebar } from './components/Sidebar.tsx';
import { TopHeader } from './components/TopHeader.tsx';
import { EvidencePlaybackModal } from './components/Modal/EvidencePlaybackModal.tsx';
import { AuthLoginModal } from './components/Modal/AuthLoginModal.tsx';
import { useSocTelemetry } from './hooks/useSocTelemetry.ts';
import { IIncidentItem, IOperatorSession } from './types/soc.ts';

// Các Giao diện Tác chiến Chuyên biệt
import { DashboardView } from './components/views/DashboardView.tsx';
import { ThreatIntelligenceView } from './components/views/ThreatIntelligenceView.tsx';
import { IncidentFeedView } from './components/views/IncidentFeedView.tsx';
import { DeviceManagerView } from './components/views/DeviceManagerView.tsx';
import { SettingsView } from './components/views/SettingsView.tsx';

const SESSION_STORAGE_KEY = 'SOC_OPERATOR_SESSION';

export const App: React.FC = () => {
  const { overview, cameras, incidents, setIncidents, isBackendConnected, refreshData } = useSocTelemetry();
  const [activeTab, setActiveTab] = useState<string>('SOC Dashboard');
  const [activePlaybackIncident, setActivePlaybackIncident] = useState<IIncidentItem | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState<boolean>(false);
  const [session, setSession] = useState<IOperatorSession | null>(() => {
    try {
      const saved = localStorage.getItem(SESSION_STORAGE_KEY);
      return saved ? (JSON.parse(saved) as IOperatorSession) : null;
    } catch {
      return null;
    }
  });

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage(null);
    }, 2800);
  };

  useEffect(() => {
    const verifySession = async () => {
      if (!session?.token) return;
      try {
        const res = await fetch('/api/auth/me', {
          headers: { Authorization: `Bearer ${session.token}` },
        });
        if (res.ok) {
          const json = await res.json();
          if (json?.authenticated && json?.session) {
            setSession(json.session);
            localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(json.session));
          }
        }
      } catch {
        // Keep local session if offline
      }
    };
    void verifySession();
  }, []);

  const handleLoginSuccess = (newSession: IOperatorSession) => {
    setSession(newSession);
    localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(newSession));
    showToast(`[AUTH] Đăng nhập thành công: ${newSession.operatorId} (${newSession.operatorName})`);
  };

  const handleLogout = () => {
    setSession(null);
    localStorage.removeItem(SESSION_STORAGE_KEY);
    showToast('[AUTH] Đã đăng xuất phiên trực SOC');
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
    const activeOperatorId = session?.operatorId || 'OP-VN-SOC-804';
    showToast(`[HITL VERIFIED] ${decision} bởi ${activeOperatorId}`);

    try {
      const res = await fetch(`/api/incidents/${incidentId}/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          operatorId: activeOperatorId,
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
    void refreshData();
  };

  const pendingIncidentCount = incidents.filter((i) => i.status === 'PENDING_VERIFICATION').length;

  // Bộ định tuyến hiển thị các Tab Tác chiến
  const renderActiveView = () => {
    switch (activeTab) {
      case 'Threat Intelligence':
        return (
          <ThreatIntelligenceView
            incidents={incidents}
            onSelectPlayback={(inc) => setActivePlaybackIncident(inc)}
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
            onReboot={(id) => showToast(`[DEVICE] Đã cập nhật/khởi động lại camera: ${id}`)}
            onRefresh={refreshData}
          />
        );
      case 'Settings':
        return (
          <SettingsView
            operatorId={session?.operatorId || 'OP-VN-SOC-804'}
            onToast={showToast}
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
        activeThreatCount={pendingIncidentCount}
        cameraCount={cameras.length}
      />

      {/* 2. Main Viewport (Cố định chiều rộng không tràn) */}
      <div className="ml-[240px] w-[calc(100%-240px)] max-w-[calc(100%-240px)] min-h-screen flex flex-col min-w-0 overflow-x-hidden">
        {/* Top Header Bar (52px) */}
        <TopHeader
          activeTab={activeTab}
          threatScore={overview.threatScore}
          threatLevel={overview.threatLevel}
          isConnected={isBackendConnected}
          session={session}
          incidents={incidents}
          onOpenAuthModal={() => setIsAuthModalOpen(true)}
          onSelectIncident={(inc) => setActivePlaybackIncident(inc)}
        />

        {/* Nội dung Tác chiến tương ứng với Tab đang chọn */}
        <main className="p-4 sm:p-6 space-y-4 flex-1 min-w-0 overflow-x-hidden">
          {renderActiveView()}
        </main>
      </div>

      {/* Modal Bằng chứng Video & Chốt chặn Operational HITL (CD-04) */}
      <EvidencePlaybackModal
        incident={activePlaybackIncident}
        operatorId={session?.operatorId || 'OP-VN-SOC-804'}
        onClose={() => setActivePlaybackIncident(null)}
        onSubmitDecision={handleHitlDecision}
      />

      {/* Modal Xác thực Vận hành viên SOC */}
      <AuthLoginModal
        isOpen={isAuthModalOpen}
        session={session}
        onClose={() => setIsAuthModalOpen(false)}
        onLoginSuccess={handleLoginSuccess}
        onLogout={handleLogout}
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
