import React, { useState } from 'react';
import { KpiCards } from '../KpiCards.tsx';
import { CameraMatrix } from '../CameraMatrix/CameraMatrix.tsx';
import { AlertLogModule } from '../AlertLog/AlertLogModule.tsx';
import { AiMetricsGrid } from '../AiMetricsGrid/AiMetricsGrid.tsx';
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
  // State quản lý phóng to camera quan sát chi tiết
  const [zoomedCameraId, setZoomedCameraId] = useState<string | null>(null);

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

  const handleToggleZoom = (camId: string | null) => {
    setZoomedCameraId(camId);
    if (camId) {
      onToast?.(`[CAMERA ZOOM] Đang quan sát cận cảnh camera: ${camId}. Alert Log chuyển thành menu phải (20% width).`);
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

      {/* Hàng 2: Camera Matrix & Alert Log Rút Gọn
          - Khi ở chế độ 2x2 bình thường: col-span-8 (Camera) & col-span-4 (Alert Log)
          - Khi phóng to quan sát: Camera chiếm 80% width (chia đều), Alert Log mở rộng thành right menu modal 20% width */}
      {zoomedCameraId ? (
        <section className="flex gap-4 min-w-0 transition-all duration-200">
          {/* Khu vực Camera chiếm 80% width */}
          <div className="w-[80%] min-w-0">
            <CameraMatrix
              cameras={cameras}
              onPtzCommand={onPtzCommand}
              zoomedCameraId={zoomedCameraId}
              onToggleZoom={handleToggleZoom}
            />
          </div>

          {/* Khu vực Alert Log mở rộng thành Right Menu Modal chiếm đúng 20% width */}
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
          {/* Lưới 2x2 tiêu chuẩn: 8 cột (68-70%) */}
          <div className="col-span-8 min-w-0">
            <CameraMatrix
              cameras={cameras}
              onPtzCommand={onPtzCommand}
              zoomedCameraId={null}
              onToggleZoom={handleToggleZoom}
            />
          </div>

          {/* Alert Log Rút gọn tiêu chuẩn: 4 cột (30-32%) */}
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

      {/* Hàng 3: Thống Kê Hiệu Năng AI & Phân Bố Đối Tượng */}
      <div className="min-w-0">
        <AiMetricsGrid cameras={cameras} />
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
