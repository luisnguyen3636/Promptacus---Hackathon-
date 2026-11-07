import React from 'react';
import { Video, AlertOctagon, CheckCircle2, XCircle, ArrowDownCircle } from 'lucide-react';
import { IIncidentItem } from '../../types/soc.ts';

interface EvidencePlaybackModalProps {
  incident: IIncidentItem | null;
  onClose: () => void;
  onSubmitDecision: (
    incidentId: string,
    decision: 'CONFIRM_AND_DISPATCH' | 'DOWNGRADE_MONITOR' | 'DISMISS_FALSE_POSITIVE',
    notes?: string
  ) => void;
}

export const EvidencePlaybackModal: React.FC<EvidencePlaybackModalProps> = ({
  incident,
  onClose,
  onSubmitDecision,
}) => {
  if (!incident) return null;

  return (
    <div className="fixed inset-0 bg-[#05070A]/85 backdrop-blur-[2px] z-50 flex items-center justify-center p-6 select-none">
      <div className="w-[900px] max-w-full bg-[#0E131A] border border-[#1E2631] flex flex-col">
        {/* Modal Header */}
        <div className="bg-[#121822] border-b border-[#1E2631] px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 bg-[#DC2626]"></span>
            <span className="font-bold text-sm text-white font-mono">
              {incident.title} ({incident.id})
            </span>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white font-mono text-xs font-bold cursor-pointer"
          >
            [ ✕ ĐÓNG ]
          </button>
        </div>

        {/* Modal Body: 2 Cột */}
        <div className="p-5 grid grid-cols-12 gap-5">
          {/* Cột Trái: Video Player & Timeline (7 Cột) */}
          <div className="col-span-7 flex flex-col space-y-3">
            <div className="bg-[#05070A] border border-[#1E2631] aspect-video relative flex items-center justify-center overflow-hidden">
              {incident.cameraSnapshots?.eventPeakSnapshotUrl || incident.cameraSnapshots?.preEventSnapshotUrl ? (
                <img
                  src={incident.cameraSnapshots?.eventPeakSnapshotUrl || incident.cameraSnapshots?.preEventSnapshotUrl}
                  alt="Forensic Evidence Peak Snapshot"
                  className="w-full h-full object-contain"
                />
              ) : (
                <div className="text-center p-4">
                  <Video className="w-10 h-10 text-[#EF4444] mx-auto mb-2 animate-pulse" />
                  <div className="font-mono text-xs text-white font-bold">
                    EVIDENCE PLAYBACK BUFFER (10s Pre + 10s Post)
                  </div>
                  <div className="text-[10px] font-mono text-slate-500 mt-1">
                    Codec: H.264/AAC · Forensic Grade Trace
                  </div>
                </div>
              )}

              {/* Bounding Box tag mô phỏng trên video */}
              <div className="absolute top-2 left-2 bg-[#EF4444]/90 text-white font-mono text-[9px] font-bold px-2 py-0.5 border border-[#EF4444] shadow">
                TARGET #{incident.id.toUpperCase()} [{incident.severity}]
              </div>
            </div>

            {/* Timeline Bar với mốc thời gian sự kiện */}
            <div className="bg-[#121822] p-2.5 border border-[#1E2631] space-y-1.5 font-mono">
              <div className="flex justify-between text-[10px] text-slate-400">
                <span>-10.0s (Pre-Event)</span>
                <span className="text-[#EF4444] font-bold">▲ EVENT TRIGGER ({incident.timestamp})</span>
                <span>+10.0s (Post-Event)</span>
              </div>
              <div className="h-2 bg-[#1E2631] relative">
                <div className="absolute inset-y-0 left-0 w-1/2 bg-[#3B82F6] opacity-60"></div>
                <div className="absolute inset-y-0 left-1/2 w-1 bg-[#EF4444]"></div>
              </div>
            </div>
          </div>

          {/* Cột Phải: Phân tích VLM & Metadata (5 Cột) */}
          <div className="col-span-5 flex flex-col justify-between space-y-3">
            <div className="space-y-3">
              <div className="bg-[#121822] p-3 border border-[#1E2631]">
                <div className="text-[10px] font-mono text-[#64748B] uppercase">METADATA SỰ CỐ & AI FORENSIC</div>
                <div className="font-mono text-xs text-slate-300 mt-1.5 space-y-1 leading-relaxed">
                  <div><strong>Mã Sự Cố:</strong> <span className="text-[#38BDF8]">{incident.eventId || incident.id}</span></div>
                  <div><strong>Thời gian:</strong> {incident.timestamp}</div>
                  <div><strong>Khu vực:</strong> {incident.subTitle || 'Laptop Client Zone'}</div>
                  <div><strong>Camera / IP:</strong> {incident.cameraId || 'N/A'} ({incident.sourceIp})</div>
                  <div>
                    <strong>Mức độ:</strong>{' '}
                    <span className="text-[#F97316] font-bold">[{incident.severity}]</span> &bull; Phán quyết:{' '}
                    <span className="text-[#10B981] font-bold">{incident.threatVerdict || 'OBSERVED_ACTIVITY'}</span>
                  </div>
                  <div>
                    <strong>Model AI:</strong>{' '}
                    <span className="text-slate-200">{incident.modelUsed || '@cf/deepseek-ai/deepseek-v4.1-flash-1017'}</span>{' '}
                    <span className="text-[#06B6D4]">({incident.latencyMs || 925}ms)</span>
                  </div>
                </div>
              </div>

              {/* Khối Động học & Tư thế Kinematics */}
              <div className="bg-[#121822] p-3 border border-[#1E2631]">
                <div className="text-[10px] font-mono text-[#64748B] uppercase mb-1">
                  ĐỘNG HỌC & TƯ THẾ (KINEMATICS)
                </div>
                <div className="text-xs text-slate-300 space-y-1 font-mono leading-relaxed">
                  <div><strong>Hành vi:</strong> <span className="text-white font-bold">{incident.title}</span> ({incident.role || 'bystander'})</div>
                  <div><strong>Tư thế:</strong> {incident.postureDetails || `Detected action: ${incident.title}`}</div>
                  <div><strong>Sinh học:</strong> {incident.kinematicsSummary || 'Góc khuỷu tay phải: N/A°, Độ duỗi tay: N/Am, Vận tốc cổ tay: N/Apx/s'}</div>
                  {incident.weaponDetected && (
                    <div className="text-[#EF4444] font-bold">
                      ⚠ Vũ khí: {incident.weaponDetected} (Độ tin cậy: {Math.round((incident.weaponConfidence || 0) * 100)}%)
                    </div>
                  )}
                </div>
              </div>

              {/* Khối Tóm tắt Điều tra VLM DeepSeek */}
              <div className="bg-[#121822] p-3 border border-[#1E2631]">
                <div className="text-[10px] font-mono text-[#64748B] uppercase mb-1">
                  KẾT QUẢ SUY LUẬN AI/VLM (DEEPSEEK FORENSIC ENGINE)
                </div>
                <div className="text-xs text-slate-200 leading-relaxed font-sans">
                  {incident.vlmAnalysis || incident.rawResponse || 'Không có bản phân tích ngữ cảnh cho sự cố này.'}
                </div>
              </div>
            </div>

            <div className="p-2.5 bg-[#161E29] border border-[#1E2631] text-[10px] font-mono text-slate-400">
              <strong>Audit Note:</strong> Quyết định của bạn sẽ được gắn chữ ký số kiểm toán và lưu vào nhật ký tác chiến chuẩn SOC.
            </div>
          </div>
        </div>

        {/* Modal Footer: CHỐT CHẶN VẬN HÀNH VIÊN (MANDATORY HITL GATE) */}
        <div className="p-4 bg-[#121822] border-t border-[#1E2631] flex items-center justify-between">
          <div className="font-mono text-xs text-slate-400">
            Operator ID: <span className="text-[#10B981] font-bold">OP-VN-SOC-804</span>
          </div>
          <div className="flex items-center gap-3">
            {/* Quyết định 3: Hủy báo động giả */}
            <button
              onClick={() => onSubmitDecision(incident.id, 'DISMISS_FALSE_POSITIVE')}
              className="bg-[#161E29] border border-[#2D3748] text-[#94A3B8] hover:bg-[#2D3748] hover:text-white font-mono text-xs font-bold px-3 py-2 inline-flex items-center gap-1.5 cursor-pointer transition-colors"
            >
              <XCircle className="w-3.5 h-3.5" />
              <span>HỦY BÁO ĐỘNG GIẢ</span>
            </button>

            {/* Quyết định 2: Hạ mức cảnh báo & Tiếp tục theo dõi */}
            <button
              onClick={() => onSubmitDecision(incident.id, 'DOWNGRADE_MONITOR')}
              className="bg-[#78350F] border border-[#F59E0B] text-white hover:bg-[#F59E0B] font-mono text-xs font-bold px-3 py-2 inline-flex items-center gap-1.5 cursor-pointer transition-colors"
            >
              <ArrowDownCircle className="w-3.5 h-3.5" />
              <span>HẠ MỨC / THEO DÕI</span>
            </button>

            {/* Quyết định 1: Xác nhận & Điều phối */}
            <button
              onClick={() => onSubmitDecision(incident.id, 'CONFIRM_AND_DISPATCH')}
              className="bg-[#7F1D1D] border border-[#DC2626] text-white hover:bg-[#DC2626] font-mono text-xs font-bold px-3.5 py-2 inline-flex items-center gap-1.5 cursor-pointer transition-colors"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>XÁC NHẬN & ĐIỀU PHỐI (DISPATCH)</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
