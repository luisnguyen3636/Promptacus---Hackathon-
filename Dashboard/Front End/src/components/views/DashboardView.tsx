import React, { useState } from 'react';
import { KpiCards } from '../KpiCards.tsx';
import { CameraMatrix } from '../CameraMatrix/CameraMatrix.tsx';
import { AlertLogModule } from '../AlertLog/AlertLogModule.tsx';
import { RecentThreatsTable } from '../RecentThreats/RecentThreatsTable.tsx';
import { ISocOverview, ICameraDevice, IIncidentItem } from '../../types/soc.ts';
import { Volume2, VolumeX, FileText } from 'lucide-react';

interface DashboardViewProps {
  overview: ISocOverview;
  cameras: ICameraDevice[];
  incidents: IIncidentItem[];
  onPtzCommand: (cameraId: string, action: string) => void;
  onSelectPlayback: (incident: IIncidentItem) => void;
  onToast?: (msg: string) => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  overview,
  cameras,
  incidents,
  onPtzCommand,
  onSelectPlayback,
  onToast,
}) => {
  const [isSirenMuted, setIsSirenMuted] = useState<boolean>(false);
  const [zoomedCameraId, setZoomedCameraId] = useState<string | null>(null);

  const handleToggleSiren = () => {
    setIsSirenMuted(!isSirenMuted);
    onToast?.(
      isSirenMuted
        ? '[SOC AUDIO] Còi báo động đã kích hoạt'
        : '[SOC AUDIO] Còi báo động đã tắt tiếng'
    );
  };

  const handleExportReport = () => {
    const reportData = {
      generatedAt: new Date().toISOString(),
      overview,
      cameras,
      incidents,
    };
    const blob = new Blob([JSON.stringify(reportData, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `soc-shift-report-${Date.now()}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    onToast?.('[REPORT GENERATED] Đã tải xuống báo cáo ca trực SOC (JSON)');
  };

  const handleToggleZoom = (camId: string | null) => {
    setZoomedCameraId(camId);
    if (camId) {
      onToast?.(
        `[CAMERA ZOOM] Đang quan sát cận cảnh camera: ${camId}. Alert Log mở rộng thành menu phải (20% width).`
      );
    } else {
      onToast?.('[CAMERA ZOOM] Đã trở về ma trận 2x2 tiêu chuẩn.');
    }
  };

  return (
    <div className="space-y-4 min-w-0 select-none">
      {/* Thanh Tác vụ Nhanh Đỉnh Dashboard */}
      <div className="bg-[#0E131A] border border-[#1E2631] px-4 py-2.5 flex items-center justify-between min-w-0 overflow-hidden">
        <div className="flex items-center gap-2 min-w-0 truncate">
          <span className="w-2 h-2 bg-[#10B981] animate-pulse shrink-0"></span>
          <span className="font-bold text-xs uppercase text-white truncate">
            URBAN SAFETY OPERATIONS CENTER &bull; LIVE SURVEILLANCE MATRIX
          </span>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {/* Nút Tắt/Bật Còi */}
          <button
            onClick={handleToggleSiren}
            className={`px-3 py-1 border font-mono text-xs font-bold inline-flex items-center gap-1.5 cursor-pointer transition-colors ${
              isSirenMuted
                ? 'bg-[#161E29] border-[#2D3748] text-slate-400'
                : 'bg-[#78350F] border-[#F59E0B] text-white hover:bg-[#F59E0B]'
            }`}
          >
            {isSirenMuted ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5" />}
            <span>{isSirenMuted ? 'ĐÃ TẮT TIẾNG' : 'TẮT CÒI BÁO ĐỘNG'}</span>
          </button>

          {/* Nút Xuất Báo cáo */}
          <button
            onClick={handleExportReport}
            className="px-3 py-1 bg-[#161E29] border border-[#2D3748] hover:border-[#10B981] hover:text-[#10B981] text-slate-200 font-mono text-xs font-bold inline-flex items-center gap-1.5 cursor-pointer transition-colors"
          >
            <FileText className="w-3.5 h-3.5" />
            <span>XUẤT BÁO CÁO CA TRỰC</span>
          </button>
        </div>
      </div>

      {/* Hàng 1: 4 Thẻ KPI Telemetry */}
      <KpiCards metrics={overview.metrics} />

      {/* Hàng 2: Camera Matrix & Alert Log Rút Gọn
          - Khi ở chế độ 2x2 bình thường: col-span-8 (Camera) & col-span-4 (Alert Log)
          - Khi phóng to quan sát: Camera chiếm 80% width (chia đều), Alert Log mở rộng thành right menu modal 20% width */}
      {zoomedCameraId ? (
        <section className="flex gap-4 min-w-0 transition-all duration-200">
          <div className="w-[80%] min-w-0">
            <CameraMatrix
              cameras={cameras}
              incidents={incidents}
              onPtzCommand={onPtzCommand}
              zoomedCameraId={zoomedCameraId}
              onToggleZoom={handleToggleZoom}
              onSelectPlayback={onSelectPlayback}
            />
          </div>

          <div className="w-[20%] min-w-0">
            <AlertLogModule
              threatScore={overview.threatScore}
              threatLevel={overview.threatLevel}
              incidents={incidents}
              metrics={overview.metrics}
              onSelectPlayback={onSelectPlayback}
              isExpanded={true}
              onCloseExpanded={() => handleToggleZoom(null)}
            />
          </div>
        </section>
      ) : (
        <section className="grid grid-cols-12 gap-4 min-w-0 transition-all duration-200">
          <div className="col-span-8 min-w-0">
            <CameraMatrix
              cameras={cameras}
              incidents={incidents}
              onPtzCommand={onPtzCommand}
              zoomedCameraId={null}
              onToggleZoom={handleToggleZoom}
              onSelectPlayback={onSelectPlayback}
            />
          </div>

          <div className="col-span-4 min-w-0">
            <AlertLogModule
              threatScore={overview.threatScore}
              threatLevel={overview.threatLevel}
              incidents={incidents}
              metrics={overview.metrics}
              onSelectPlayback={onSelectPlayback}
              isExpanded={false}
            />
          </div>
        </section>
      )}

      {/* Hàng 3: Bảng Sự cố & Xem lại Camera (RECENT THREATS) */}
      <div className="min-w-0">
        <RecentThreatsTable
          incidents={incidents}
          onSelectPlayback={onSelectPlayback}
        />
      </div>
    </div>
  );
};
