import React, { useState } from 'react';
import { KpiCards } from '../KpiCards.tsx';
import { CameraMatrix } from '../CameraMatrix/CameraMatrix.tsx';
import { ThreatScoreModule } from '../ThreatScore/ThreatScoreModule.tsx';
import { TrafficCharts } from '../TrafficCharts/TrafficCharts.tsx';
import { RecentThreatsTable } from '../RecentThreats/RecentThreatsTable.tsx';
import { ISocOverview, ICameraDevice, IIncidentItem } from '../../types/soc.ts';
import { Volume2, VolumeX, FileText, ShieldAlert, ShieldCheck } from 'lucide-react';

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
  const [isLockdownActive, setIsLockdownActive] = useState<boolean>(false);

  const handleToggleSiren = () => {
    setIsSirenMuted(!isSirenMuted);
    onToast?.(isSirenMuted ? '[SOC AUDIO] Còi báo động đã kích hoạt' : '[SOC AUDIO] Còi báo động đã tắt tiếng');
  };

  const handleExportReport = () => {
    onToast?.('[REPORT GENERATED] Đã trích xuất báo cáo ca trực SOC (PDF/CSV)');
  };

  const handleToggleLockdown = () => {
    setIsLockdownActive(!isLockdownActive);
    onToast?.(
      !isLockdownActive
        ? '[EMERGENCY ALERT] KÍCH HOẠT CHẾ ĐỘ PHÒNG THỦ KHẨN CẤP (LOCKDOWN)'
        : '[SOC NORMALIZED] Đã hủy chế độ phòng thủ khẩn cấp'
    );
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

          {/* Nút Lockdown */}
          <button
            onClick={handleToggleLockdown}
            className={`px-3 py-1 border font-mono text-xs font-bold inline-flex items-center gap-1.5 cursor-pointer transition-colors ${
              isLockdownActive
                ? 'bg-[#7F1D1D] border-[#DC2626] text-white animate-pulse'
                : 'bg-[#161E29] border-[#2D3748] text-slate-300 hover:border-[#DC2626] hover:text-[#DC2626]'
            }`}
          >
            {isLockdownActive ? <ShieldAlert className="w-3.5 h-3.5" /> : <ShieldCheck className="w-3.5 h-3.5" />}
            <span>{isLockdownActive ? 'LOCKDOWN: ĐANG BẬT' : 'PHÒNG THỦ KHẨN CẤP'}</span>
          </button>
        </div>
      </div>

      {/* Hàng 1: 4 Thẻ KPI Telemetry */}
      <KpiCards metrics={overview.metrics} />

      {/* Hàng 2: Camera Matrix 2x2 (68%) & Threat Score (32%) */}
      <section className="grid grid-cols-12 gap-4 min-w-0">
        <div className="col-span-8 min-w-0">
          <CameraMatrix cameras={cameras} onPtzCommand={onPtzCommand} />
        </div>
        <div className="col-span-4 min-w-0">
          <ThreatScoreModule
            score={overview.threatScore}
            status={overview.status}
            metrics={overview.metrics}
          />
        </div>
      </section>

      {/* Hàng 3: 2 Biểu đồ Lưu lượng Video */}
      <div className="min-w-0">
        <TrafficCharts
          ingressVal={overview.metrics.downloadMbps}
          egressVal={overview.metrics.uploadMbps}
        />
      </div>

      {/* Hàng 4: Bảng Sự cố & Xem lại Camera (RECENT THREATS) */}
      <div className="min-w-0">
        <RecentThreatsTable
          incidents={incidents}
          onSelectPlayback={onSelectPlayback}
        />
      </div>
    </div>
  );
};
