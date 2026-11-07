import React, { useState } from 'react';
import { Video, CheckCircle2, XCircle, ArrowDownCircle, Users, Eye } from 'lucide-react';
import { IIncidentItem } from '../../types/soc.ts';

interface EvidencePlaybackModalProps {
  incident: IIncidentItem | null;
  operatorId?: string;
  onClose: () => void;
  onSubmitDecision: (
    incidentId: string,
    decision: 'CONFIRM_AND_DISPATCH' | 'DOWNGRADE_MONITOR' | 'DISMISS_FALSE_POSITIVE',
    notes?: string
  ) => void;
}

export const EvidencePlaybackModal: React.FC<EvidencePlaybackModalProps> = ({
  incident,
  operatorId = 'OP-VN-SOC-804',
  onClose,
  onSubmitDecision,
}) => {
  const [operatorNotes, setOperatorNotes] = useState<string>('');

  if (!incident) return null;

  const streamPreviewUrl = incident.cameraId
    ? `/api/v1/cameras/${incident.cameraId}/stream`
    : undefined;

  return (
    <div className="fixed inset-0 bg-[#05070A]/85 backdrop-blur-[2px] z-50 flex items-center justify-center p-4 sm:p-6 select-none overflow-y-auto">
      <div className="w-[960px] max-w-full bg-[#0E131A] border border-[#1E2631] flex flex-col max-h-[92vh]">
        {/* Modal Header */}
        <div className="bg-[#121822] border-b border-[#1E2631] px-4 py-3 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2 min-w-0">
            <span className="w-2.5 h-2.5 bg-[#DC2626] shrink-0"></span>
            <span className="font-bold text-sm text-white font-mono truncate">
              {incident.actionType || incident.title} ({incident.id})
            </span>
            {incident.isUrgent && (
              <span className="bg-[#7F1D1D] border border-[#DC2626] text-white font-mono text-[10px] font-bold px-2 py-0.5 shrink-0 animate-pulse">
                URGENT
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white font-mono text-xs font-bold cursor-pointer shrink-0"
          >
            [ ✕ ĐÓNG ]
          </button>
        </div>

        {/* Modal Body: 2 Cột */}
        <div className="p-5 grid grid-cols-12 gap-5 overflow-y-auto flex-1">
          {/* Cột Trái: Video Player / Snapshot & Actors (7 Cột) */}
          <div className="col-span-12 lg:col-span-7 flex flex-col space-y-3">
            <div className="bg-[#05070A] border border-[#1E2631] aspect-video relative flex items-center justify-center overflow-hidden">
              {incident.cameraSnapshots?.eventPeakSnapshotUrl || incident.cameraSnapshots?.preEventSnapshotUrl ? (
                <img
                  src={
                    incident.cameraSnapshots?.eventPeakSnapshotUrl ||
                    incident.cameraSnapshots?.preEventSnapshotUrl
                  }
                  alt="Evidence Snapshot"
                  className="w-full h-full object-contain"
                />
              ) : streamPreviewUrl ? (
                <img
                  src={streamPreviewUrl}
                  alt={incident.cameraId || 'Camera Stream'}
                  onError={(e) => {
                    (e.currentTarget as HTMLImageElement).style.display = 'none';
                  }}
                  className="w-full h-full object-cover"
                />
              ) : null}

              <div className="text-center p-4 pointer-events-none">
                <Video className="w-9 h-9 text-[#EF4444] mx-auto mb-1.5 opacity-80" />
                <div className="font-mono text-xs text-white font-bold">
                  CAMERA: {incident.cameraId || 'LAPTOP_01'} &bull; FRAME #{incident.frameIndex ?? 'N/A'}
                </div>
                <div className="text-[11px] font-mono text-slate-400 mt-0.5">
                  {incident.location || incident.subTitle}
                </div>
              </div>

              <div className="absolute top-2 left-2 bg-[#EF4444]/90 text-white font-mono text-[10px] font-bold px-2 py-0.5 border border-[#EF4444] shadow">
                {incident.actionType || 'EVENT'} [{incident.severity}] &bull; SCORE:{' '}
                {incident.threatScore !== undefined
                  ? incident.threatScore <= 1
                    ? `${Math.round(incident.threatScore * 100)}%`
                    : incident.threatScore
                  : 'N/A'}
              </div>
            </div>

            {/* Danh sách Đối tượng (Actors) từ JSON Server */}
            <div className="bg-[#121822] p-3 border border-[#1E2631] space-y-2 font-mono text-xs">
              <div className="flex items-center justify-between text-[10px] text-[#64748B] uppercase">
                <span className="flex items-center gap-1.5 font-bold text-slate-300">
                  <Users className="w-3.5 h-3.5 text-[#3B82F6]" />
                  ĐỐI TƯỢNG TRONG KHUNG HÌNH (ACTORS: {incident.actors?.length || incident.humanCount || 0})
                </span>
                <span>HUMAN COUNT: {incident.humanCount ?? incident.actors?.length ?? 0}</span>
              </div>

              {incident.actors && incident.actors.length > 0 ? (
                <div className="space-y-1.5">
                  {incident.actors.map((actor, idx) => (
                    <div
                      key={`${actor.id}_${idx}`}
                      className="p-2 bg-[#080B10] border border-[#1E2631] flex flex-col gap-0.5"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-white">
                          Track #{actor.id} &bull;{' '}
                          <span
                            className={
                              actor.role === 'attacker'
                                ? 'text-[#EF4444] uppercase'
                                : 'text-[#38BDF8] uppercase'
                            }
                          >
                            {actor.role}
                          </span>
                        </span>
                        <span className="text-[10px] px-1.5 py-0.5 bg-[#161E29] border border-[#2D3748] text-[#F59E0B] font-bold uppercase">
                          Action: {actor.action}
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-300">Tư thế: {actor.posture}</div>
                      <div className="text-[10px] text-slate-500 flex items-center justify-between">
                        <span>
                          Tương tác với:{' '}
                          {actor.interacting_with !== undefined && actor.interacting_with !== null
                            ? `Track #${actor.interacting_with}`
                            : 'Không'}
                        </span>
                        {actor.bbox && <span>BBox: [{actor.bbox.join(', ')}]</span>}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-slate-500 text-[11px]">
                  Chưa có dữ liệu chi tiết từng cá nhân trong khung hình.
                </div>
              )}
            </div>
          </div>

          {/* Cột Phải: Chi tiết JSON từ Server (5 Cột) */}
          <div className="col-span-12 lg:col-span-5 flex flex-col justify-between space-y-3">
            <div className="space-y-3">
              {/* Metadata Sự cố */}
              <div className="bg-[#121822] p-3 border border-[#1E2631]">
                <div className="text-[10px] font-mono text-[#64748B] uppercase font-bold">
                  THÔNG TIN CHI TIẾT TỪ SERVER
                </div>
                <div className="font-mono text-xs text-slate-300 mt-1.5 space-y-1 leading-relaxed">
                  <div>
                    <strong>Camera ID:</strong>{' '}
                    <span className="text-[#38BDF8] font-bold">{incident.cameraId || 'N/A'}</span>
                  </div>
                  <div>
                    <strong>Vị trí (Location):</strong>{' '}
                    <span className="text-white">{incident.location || incident.subTitle}</span>
                  </div>
                  <div>
                    <strong>Thời điểm:</strong> {incident.timestamp}
                  </div>
                  <div>
                    <strong>Thông số Khung hình:</strong> FPS: {incident.measuredFps ?? 'N/A'} &bull; Frame:{' '}
                    #{incident.frameIndex ?? 'N/A'} &bull; Số người: {incident.humanCount ?? 'N/A'}
                  </div>
                  <div>
                    <strong>Hành vi:</strong>{' '}
                    <span className="text-[#EF4444] font-bold">{incident.actionType || incident.title}</span> &bull; Độ tin cậy:{' '}
                    <span className="text-[#10B981] font-bold">
                      {incident.confidence !== undefined
                        ? `${Math.round(incident.confidence * 100)}%`
                        : 'N/A'}
                    </span>
                  </div>
                  <div>
                    <strong>Khuyến nghị (Recommended):</strong>{' '}
                    <span className="px-1.5 py-0.5 bg-[#7F1D1D] text-white font-bold text-[10px]">
                      {incident.recommendedAction || 'DISPATCH_SECURITY'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Dấu hiệu trực quan (Visual Cues) */}
              {incident.visualCues && (
                <div className="bg-[#121822] p-3 border border-[#1E2631] font-mono text-xs">
                  <div className="text-[10px] text-[#64748B] uppercase font-bold mb-1.5 flex items-center gap-1">
                    <Eye className="w-3.5 h-3.5 text-[#F59E0B]" />
                    DẤU HIỆU TRỰC QUAN (VISUAL CUES)
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-[11px] text-center">
                    <div
                      className={`p-1.5 border ${
                        incident.visualCues.weapons_visible
                          ? 'bg-[#7F1D1D]/40 border-[#DC2626] text-[#FECACA] font-bold'
                          : 'bg-[#080B10] border-[#1E2631] text-slate-400'
                      }`}
                    >
                      Vũ khí: {incident.visualCues.weapons_visible ? 'CÓ' : 'KHÔNG'}
                    </div>
                    <div
                      className={`p-1.5 border ${
                        incident.visualCues.physical_contact
                          ? 'bg-[#7F1D1D]/40 border-[#DC2626] text-[#FECACA] font-bold'
                          : 'bg-[#080B10] border-[#1E2631] text-slate-400'
                      }`}
                    >
                      Va chạm: {incident.visualCues.physical_contact ? 'CÓ' : 'KHÔNG'}
                    </div>
                    <div
                      className={`p-1.5 border ${
                        incident.visualCues.fallen_person
                          ? 'bg-[#7F1D1D]/40 border-[#DC2626] text-[#FECACA] font-bold'
                          : 'bg-[#080B10] border-[#1E2631] text-slate-400'
                      }`}
                    >
                      Người ngã: {incident.visualCues.fallen_person ? 'CÓ' : 'KHÔNG'}
                    </div>
                  </div>
                </div>
              )}

              {/* Mô tả & Lý giải từ Server */}
              <div className="bg-[#121822] p-3 border border-[#1E2631] space-y-2">
                <div className="text-[10px] font-mono text-[#64748B] uppercase font-bold">
                  MÔ TẢ & LÝ GIẢI TỪ SERVER (DESCRIPTION & REASONING)
                </div>
                <div className="text-xs text-white font-semibold leading-relaxed">
                  {incident.description || incident.title}
                </div>
                <div className="text-xs text-slate-300 leading-relaxed border-t border-[#1E2631] pt-1.5">
                  {incident.reasoning || incident.vlmAnalysis}
                </div>
                {incident.nvidiaVlmAnalysis && (
                  <div className="text-[11px] text-[#38BDF8] font-mono border-t border-[#1E2631] pt-1.5">
                    [Source: {incident.nvidiaVlmAnalysis.source || 'nvidia_nim_vlm'}] {incident.nvidiaVlmAnalysis.reasoning}
                  </div>
                )}
              </div>

              {/* Ghi chú Vận hành viên */}
              <div>
                <input
                  type="text"
                  value={operatorNotes}
                  onChange={(e) => setOperatorNotes(e.target.value)}
                  placeholder="Nhập ghi chú điều hành của Vận hành viên (tùy chọn)..."
                  className="w-full bg-[#080B10] border border-[#1E2631] px-3 py-2 text-xs font-mono text-white placeholder-slate-500 focus:outline-none focus:border-[#10B981]"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Modal Footer: CHỐT CHẶN VẬN HÀNH VIÊN (MANDATORY HITL GATE) */}
        <div className="p-4 bg-[#121822] border-t border-[#1E2631] flex items-center justify-between flex-wrap gap-3 shrink-0">
          <div className="font-mono text-xs text-slate-400">
            Operator ID: <span className="text-[#10B981] font-bold">{operatorId}</span>
          </div>
          <div className="flex items-center gap-2.5 flex-wrap">
            <button
              onClick={() => onSubmitDecision(incident.id, 'DISMISS_FALSE_POSITIVE', operatorNotes)}
              className="bg-[#161E29] border border-[#2D3748] text-[#94A3B8] hover:bg-[#2D3748] hover:text-white font-mono text-xs font-bold px-3 py-2 inline-flex items-center gap-1.5 cursor-pointer transition-colors"
            >
              <XCircle className="w-3.5 h-3.5" />
              <span>HỦY BÁO ĐỘNG GIẢ</span>
            </button>

            <button
              onClick={() => onSubmitDecision(incident.id, 'DOWNGRADE_MONITOR', operatorNotes)}
              className="bg-[#78350F] border border-[#F59E0B] text-white hover:bg-[#F59E0B] font-mono text-xs font-bold px-3 py-2 inline-flex items-center gap-1.5 cursor-pointer transition-colors"
            >
              <ArrowDownCircle className="w-3.5 h-3.5" />
              <span>HẠ MỨC / THEO DÕI</span>
            </button>

            <button
              onClick={() => onSubmitDecision(incident.id, 'CONFIRM_AND_DISPATCH', operatorNotes)}
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
