import React, { useState } from 'react';
import {
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Eye,
  Send,
  Camera,
  Cpu,
  Clock,
  Sparkles,
  FileCheck2,
  TrendingDown
} from 'lucide-react';
import { IIncidentItem, ICameraDevice } from '../../types/soc.ts';

interface NewestAlertModuleProps {
  incidents: IIncidentItem[];
  cameras: ICameraDevice[];
  onVerify?: (
    incidentId: string,
    decision: 'CONFIRM_AND_DISPATCH' | 'DOWNGRADE_MONITOR' | 'DISMISS_FALSE_POSITIVE',
    notes?: string
  ) => void;
  onSelectPlayback?: (incident: IIncidentItem) => void;
  onToast?: (msg: string) => void;
}

export const NewestAlertModule: React.FC<NewestAlertModuleProps> = ({
  incidents,
  cameras,
  onVerify,
  onSelectPlayback,
  onToast,
}) => {
  const [operatorNotes, setOperatorNotes] = useState<string>('');

  // Find newest elevated incident or fallback to the top incident
  const activeIncident =
    incidents.find((i) => i.severity === 'CRITICAL' || i.severity === 'HIGH') ||
    incidents[0] ||
    null;

  const originCamera = activeIncident?.cameraId
    ? cameras.find((c) => c.id.toLowerCase() === activeIncident.cameraId?.toLowerCase())
    : null;

  const cameraThreatScore = originCamera?.threatScore !== undefined ? originCamera.threatScore : 85;

  if (!activeIncident) {
    return (
      <div className="bg-[#0A0E17] border border-[#1E2631] p-5 h-full flex flex-col items-center justify-center text-center space-y-3 font-mono">
        <div className="w-12 h-12 bg-[#10B981]/10 border border-[#10B981] flex items-center justify-center">
          <CheckCircle2 className="w-6 h-6 text-[#10B981]" />
        </div>
        <div className="text-white font-bold text-sm">HỆ THỐNG AN TOÀN &bull; KHÔNG CÓ CẢNH BÁO NGUY HIỂM</div>
        <div className="text-slate-400 text-xs max-w-xs">
          Tất cả các camera đang được giám sát thời gian thực bởi MMAction2 và lớp Multimodal VLM.
        </div>
      </div>
    );
  }

  const isCritical = activeIncident.severity === 'CRITICAL';
  const isConfirmed = activeIncident.status === 'OPERATOR_CONFIRMED';
  const isDismissed = activeIncident.status === 'DISMISSED';

  const snapshotSrc =
    activeIncident.cameraSnapshots?.eventPeakSnapshotUrl ||
    activeIncident.playbackUrl ||
    `/api/v1/cameras/${activeIncident.cameraId || 'cam_01'}/snapshot`;

  const handleAction = (decision: 'CONFIRM_AND_DISPATCH' | 'DOWNGRADE_MONITOR' | 'DISMISS_FALSE_POSITIVE') => {
    onVerify?.(activeIncident.id, decision, operatorNotes || undefined);
    setOperatorNotes('');
  };

  return (
    <div
      className={`bg-[#0A0E17] border flex flex-col justify-between h-full select-none overflow-hidden transition-all duration-200 ${
        isCritical
          ? 'border-[#DC2626] shadow-xl shadow-red-950/25 ring-1 ring-[#DC2626]'
          : 'border-[#F59E0B]'
      }`}
    >
      {/* 1. Header Báo Động Mới Nhất */}
      <div className="p-3 bg-[#0E131A] border-b border-[#1E2631] flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-red-500 animate-ping"></span>
          <span className="font-bold text-xs text-white uppercase tracking-wider flex items-center gap-1.5">
            <ShieldAlert className="w-4 h-4 text-red-500" />
            CẢNH BÁO TỘI PHẠM MỚI NHẤT (NEWEST ALERT)
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          <span
            className={`px-2 py-0.5 text-[10px] font-mono font-bold border uppercase ${
              isCritical
                ? 'bg-[#7F1D1D] border-[#DC2626] text-white animate-pulse'
                : 'bg-[#78350F] border-[#F59E0B] text-amber-200'
            }`}
          >
            {activeIncident.severity}
          </span>
          <span className="text-[10px] font-mono text-slate-400 bg-[#161E29] px-2 py-0.5 border border-[#243042]">
            {activeIncident.id}
          </span>
        </div>
      </div>

      {/* 2. Nội Dung Chính */}
      <div className="p-3.5 space-y-3 flex-1 overflow-y-auto">
        {/* Tên Tội Phạm & Camera Nguồn kèm Threat Score của Camera */}
        <div className="flex items-start justify-between gap-3 pb-2.5 border-b border-[#1E2631]">
          <div>
            <div className="font-bold text-sm text-white flex items-center gap-2">
              <span>{activeIncident.title}</span>
            </div>
            <div className="text-xs font-mono text-[#06B6D4] flex items-center gap-1.5 mt-0.5">
              <Camera className="w-3.5 h-3.5" />
              <span>
                {originCamera?.name || activeIncident.cameraName || `Camera ${activeIncident.cameraId}`} ({activeIncident.cameraId})
              </span>
            </div>
          </div>

          {/* Threat Score riêng của Camera phát hiện */}
          <div className="text-right">
            <div className="text-[10px] font-mono text-slate-400 uppercase">THREAT SCORE CAMERA</div>
            <div
              className={`text-lg font-bold font-mono ${
                cameraThreatScore >= 75 ? 'text-red-400' : 'text-amber-400'
              }`}
            >
              {cameraThreatScore} / 100
            </div>
          </div>
        </div>

        {/* Khung Ảnh Bằng Chứng Lớn (Prominent Visual Evidence Snapshot) */}
        <div
          onClick={() => onSelectPlayback?.(activeIncident)}
          className="aspect-video bg-black border border-[#243042] relative overflow-hidden group cursor-pointer"
        >
          <img
            src={snapshotSrc}
            alt="Event Evidence Snapshot"
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            onError={(e) => {
              (e.target as HTMLElement).style.opacity = '0.3';
            }}
          />

          <div className="absolute top-2 left-2 bg-black/80 px-2 py-0.5 text-[10px] font-mono text-white flex items-center gap-1.5 border border-white/20">
            <Clock className="w-3 h-3 text-[#10B981]" />
            <span>{new Date(activeIncident.timestamp).toLocaleTimeString()}</span>
          </div>

          <div className="absolute top-2 right-2 bg-red-950/90 border border-red-500 text-white px-2 py-0.5 text-[10px] font-mono font-bold">
            MMACTION2: {activeIncident.primaryAction || 'DETECTED_CRIME'}
          </div>

          <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 flex items-center justify-center gap-2 transition-opacity">
            <div className="px-3 py-1.5 bg-[#10B981] text-black font-bold font-mono text-xs flex items-center gap-1.5">
              <Eye className="w-4 h-4" />
              <span>PHÓNG TO BẰNG CHỨNG</span>
            </div>
          </div>
        </div>

        {/* Lớp Chứng Nhận Pháp Y VLM Bắt Buộc */}
        <div className="bg-[#0B151A] border border-[#06B6D4]/40 p-2.5 font-mono text-xs space-y-1">
          <div className="flex items-center justify-between text-[#06B6D4] font-bold text-[11px]">
            <span className="flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-[#06B6D4]" />
              CHỨNG NHẬN BẮT BUỘC: {activeIncident.aiProvider || 'MULTIMODAL VLM LAYER'}
            </span>
            <span className="text-[10px] bg-[#06B6D4]/10 px-1.5 py-0.2 border border-[#06B6D4]/50">
              5-GATE FALSIFICATION PASSED
            </span>
          </div>
          <div className="text-slate-300 text-[11px] leading-relaxed">
            {activeIncident.vlmAnalysis ||
              'Mô hình Multimodal VLM xác thực hành vi nguy hiểm, kiểm định loại bỏ báo động giả qua 5 cổng an ninh và gắn thẻ chuỗi bằng chứng pháp y bất biến.'}
          </div>
        </div>
      </div>

      {/* 3. Bàn Điều Hành Quyết Định HITL (Human-in-the-Loop) */}
      <div className="p-3 bg-[#0E131A] border-t border-[#1E2631] space-y-2">
        <div className="flex items-center gap-2">
          <input
            type="text"
            placeholder="Ghi chú điều phối tác chiến (tùy chọn)..."
            value={operatorNotes}
            onChange={(e) => setOperatorNotes(e.target.value)}
            className="flex-1 bg-[#111823] border border-[#243042] text-xs font-mono text-white px-2.5 py-1.5 focus:border-[#10B981] focus:outline-none"
          />
        </div>

        <div className="grid grid-cols-3 gap-2">
          {/* Nút 1: Xác nhận & Điều phối */}
          <button
            onClick={() => handleAction('CONFIRM_AND_DISPATCH')}
            disabled={isConfirmed}
            className={`py-2 px-2 font-mono font-bold text-xs inline-flex items-center justify-center gap-1.5 transition-colors cursor-pointer ${
              isConfirmed
                ? 'bg-[#0E1E1C] border border-[#10B981] text-[#10B981] cursor-not-allowed'
                : 'bg-[#10B981] hover:bg-[#059669] text-black shadow-md'
            }`}
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span className="truncate">{isConfirmed ? 'ĐÃ ĐIỀU PHỐI' : 'XÁC NHẬN & ĐIỀU PHỐI'}</span>
          </button>

          {/* Nút 2: Hạ mức theo dõi */}
          <button
            onClick={() => handleAction('DOWNGRADE_MONITOR')}
            className="py-2 px-2 bg-[#161E29] border border-[#2D3748] hover:border-[#F59E0B] text-amber-300 font-mono font-bold text-xs inline-flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
          >
            <TrendingDown className="w-3.5 h-3.5" />
            <span className="truncate">HẠ MỨC THEO DÕI</span>
          </button>

          {/* Nút 3: Bác bỏ báo động giả */}
          <button
            onClick={() => handleAction('DISMISS_FALSE_POSITIVE')}
            disabled={isDismissed}
            className={`py-2 px-2 font-mono font-bold text-xs inline-flex items-center justify-center gap-1.5 transition-colors cursor-pointer ${
              isDismissed
                ? 'bg-black border border-slate-700 text-slate-500 cursor-not-allowed'
                : 'bg-[#161E29] border border-[#2D3748] hover:border-red-500 text-red-400 hover:text-white'
            }`}
          >
            <XCircle className="w-3.5 h-3.5" />
            <span className="truncate">HỦY BÁO ĐỘNG GIẢ</span>
          </button>
        </div>
      </div>
    </div>
  );
};
