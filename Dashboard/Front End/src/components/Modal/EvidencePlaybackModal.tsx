import React, { useState } from 'react';
import {
  Video,
  CheckCircle2,
  XCircle,
  ArrowDownCircle,
  Users,
  Eye,
  ShieldAlert,
  Fingerprint,
  Crosshair,
} from 'lucide-react';
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
  const [selectedImageMode, setSelectedImageMode] = useState<'MAIN' | 'SUBJECT' | 'HAND'>('MAIN');

  if (!incident) return null;

  const mainImageSrc =
    incident.fullImageBase64 ||
    incident.cameraSnapshots?.eventPeakSnapshotUrl ||
    incident.imageUrl ||
    incident.cameraSnapshots?.preEventSnapshotUrl;

  const subjectCropSrc =
    incident.subjectCropBase64 ||
    incident.subjects?.[0]?.crop_image_base64 ||
    incident.cameraSnapshots?.preEventSnapshotUrl;

  const handCropSrc =
    incident.handCropBase64 ||
    incident.cameraSnapshots?.handCropSnapshotUrl ||
    incident.handCropUrl;

  const activeImageSrc =
    selectedImageMode === 'HAND' && handCropSrc
      ? handCropSrc
      : selectedImageMode === 'SUBJECT' && subjectCropSrc
      ? subjectCropSrc
      : mainImageSrc;

  const streamPreviewUrl = incident.cameraId
    ? `/api/v1/cameras/${incident.cameraId}/stream`
    : undefined;

  return (
    <div className="fixed inset-0 bg-[#05070A]/85 backdrop-blur-[2px] z-50 flex items-center justify-center p-4 sm:p-6 select-none overflow-y-auto">
      <div className="w-[1040px] max-w-full bg-[#0E131A] border border-[#1E2631] flex flex-col max-h-[92vh]">
        {/* Modal Header */}
        <div className="bg-[#121822] border-b border-[#1E2631] px-4 py-3 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2 min-w-0 flex-wrap">
            <span className="w-2.5 h-2.5 bg-[#DC2626] shrink-0"></span>
            <span className="font-bold text-sm text-white font-mono truncate">
              {incident.title} [{incident.eventId || incident.id}]
            </span>
            {incident.isUrgent && (
              <span className="bg-[#7F1D1D] border border-[#DC2626] text-white font-mono text-[10px] font-bold px-2 py-0.5 shrink-0 animate-pulse">
                URGENT
              </span>
            )}
            {incident.aiVerified && (
              <span className="bg-[#112224] border border-[#10B981] text-[#10B981] font-mono text-[10px] font-bold px-2 py-0.5 shrink-0">
                AI VERIFIED
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
          {/* Cột Trái: Hình ảnh Bằng chứng, Crops, Kinematics & Subjects (7 Cột) */}
          <div className="col-span-12 lg:col-span-7 flex flex-col space-y-3">
            <div className="bg-[#05070A] border border-[#1E2631] aspect-video relative flex items-center justify-center overflow-hidden">
              {activeImageSrc ? (
                <img
                  src={activeImageSrc}
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
                  CAMERA: {incident.cameraName || incident.cameraId || 'LAPTOP_01'} &bull; FRAME #
                  {incident.frameIndex ?? incident.auditInfo?.frame_index ?? 'N/A'}
                </div>
                <div className="text-[11px] font-mono text-slate-400 mt-0.5">
                  {incident.location || incident.subTitle}
                </div>
              </div>

              <div className="absolute top-2 left-2 bg-[#EF4444]/90 text-white font-mono text-[10px] font-bold px-2 py-0.5 border border-[#EF4444] shadow">
                {incident.primaryAction || incident.actionType || 'EVENT'} [{incident.severity}] &bull; SCORE:{' '}
                {incident.threatScore !== undefined
                  ? incident.threatScore <= 1
                    ? `${Math.round(incident.threatScore * 100)}%`
                    : incident.threatScore
                  : 'N/A'}
              </div>
            </div>

            {/* Bộ chuyển đổi 3 ảnh bằng chứng: Full Image / Subject Crop / Hand Crop */}
            {(mainImageSrc || subjectCropSrc || handCropSrc) && (
              <div className="bg-[#121822] border border-[#1E2631] p-2.5 flex items-center justify-between gap-3 flex-wrap">
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setSelectedImageMode('MAIN')}
                    className={`px-2.5 py-1 font-mono text-[10px] font-bold border cursor-pointer ${
                      selectedImageMode === 'MAIN'
                        ? 'bg-[#112224] border-[#10B981] text-[#10B981]'
                        : 'bg-[#080B10] border-[#1E2631] text-slate-400 hover:text-white'
                    }`}
                  >
                    1. FULL FRAME ({incident.imageUrl ? 'image.jpg' : 'Base64'})
                  </button>
                  {subjectCropSrc && (
                    <button
                      onClick={() => setSelectedImageMode('SUBJECT')}
                      className={`px-2.5 py-1 font-mono text-[10px] font-bold border cursor-pointer ${
                        selectedImageMode === 'SUBJECT'
                          ? 'bg-[#112224] border-[#10B981] text-[#10B981]'
                          : 'bg-[#080B10] border-[#1E2631] text-slate-400 hover:text-white'
                      }`}
                    >
                      2. SUBJECT CROP ({incident.subjects?.[0]?.crop_image_size_bytes ? `${incident.subjects[0].crop_image_size_bytes}B` : 'Crop'})
                    </button>
                  )}
                  {handCropSrc && (
                    <button
                      onClick={() => setSelectedImageMode('HAND')}
                      className={`px-2.5 py-1 font-mono text-[10px] font-bold border cursor-pointer ${
                        selectedImageMode === 'HAND'
                          ? 'bg-[#7F1D1D] border-[#EF4444] text-white'
                          : 'bg-[#080B10] border-[#1E2631] text-slate-400 hover:text-white'
                      }`}
                    >
                      3. HAND / WEAPON CROP (hand_crop.jpg)
                    </button>
                  )}
                </div>

                {incident.forensicSha256 && (
                  <div
                    className="font-mono text-[10px] text-slate-400 flex items-center gap-1 truncate max-w-[320px]"
                    title={`SHA-256: ${incident.forensicSha256}`}
                  >
                    <Fingerprint className="w-3.5 h-3.5 text-[#10B981] shrink-0" />
                    <span className="truncate">SHA256: {incident.forensicSha256}</span>
                  </div>
                )}
              </div>
            )}

            {/* Danh sách Đối tượng (Subjects & Kinematics / Keypoints) */}
            <div className="bg-[#121822] p-3 border border-[#1E2631] space-y-2 font-mono text-xs">
              <div className="flex items-center justify-between text-[10px] text-[#64748B] uppercase">
                <span className="flex items-center gap-1.5 font-bold text-slate-300">
                  <Users className="w-3.5 h-3.5 text-[#3B82F6]" />
                  ĐỐI TƯỢNG &amp; ĐỘNG HỌC KHỚP XƯƠNG (SUBJECTS:{' '}
                  {incident.subjects?.length || incident.actors?.length || incident.humanCount || 0})
                </span>
                <span>HUMAN COUNT: {incident.humanCount ?? 1}</span>
              </div>

              {incident.subjects && incident.subjects.length > 0 ? (
                <div className="space-y-2">
                  {incident.subjects.map((sub, idx) => (
                    <div
                      key={sub?.track_id ?? idx}
                      className="p-2.5 bg-[#080B10] border border-[#1E2631] space-y-1.5"
                    >
                      <div className="flex items-center justify-between flex-wrap gap-2">
                        <span className="font-bold text-white">
                          Track #{sub?.track_id ?? idx + 1} &bull;{' '}
                          <span className="text-[#EF4444] uppercase">{sub?.role || 'suspect'}</span> &bull;{' '}
                          <span className="text-[#F59E0B]">{sub?.behavior || incident.actionType}</span>
                        </span>
                        <span className="text-[10px] px-1.5 py-0.5 bg-[#161E29] border border-[#2D3748] text-[#10B981] font-bold">
                          Conf: {Math.round((sub?.confidence ?? 0.95) * 100)}% | Score:{' '}
                          {Math.round((sub?.threat_score ?? 0.95) * 100)}%
                        </span>
                      </div>

                      {sub?.kinematics && (
                        <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5 text-[10px] text-slate-300 bg-[#121822] p-2 border border-[#1E2631]">
                          <div>
                            Spine Angle: <strong className="text-white">{sub.kinematics.spine_angle ?? 0}°</strong>
                          </div>
                          <div>
                            L-Elbow: <strong className="text-[#38BDF8]">{sub.kinematics.left_elbow_angle ?? 0}°</strong>
                          </div>
                          <div>
                            R-Elbow: <strong className="text-[#38BDF8]">{sub.kinematics.right_elbow_angle ?? 0}°</strong>
                          </div>
                          <div>
                            L-Arm Ext: <strong className="text-white">{sub.kinematics.left_arm_extension ?? 0}</strong>
                          </div>
                          <div>
                            R-Arm Ext: <strong className="text-white">{sub.kinematics.right_arm_extension ?? 0}</strong>
                          </div>
                          <div>
                            Speed: <strong className="text-[#10B981]">{sub.speed ?? 0} m/s</strong>
                          </div>
                        </div>
                      )}

                      {sub?.keypoints && sub.keypoints.length > 0 && (
                        <div className="text-[10px] text-slate-400 flex flex-wrap gap-1.5 pt-0.5">
                          <span className="text-slate-500">Keypoints:</span>
                          {sub.keypoints.map((kp, kIdx) => (
                            <span
                              key={kp?.id ?? kIdx}
                              className="px-1.5 py-0.5 bg-[#121822] border border-[#1E2631] text-slate-300"
                            >
                              {kp?.name || `kp_${kIdx}`}: ({kp?.x ?? 0}, {kp?.y ?? 0}) [
                              {Math.round((kp?.confidence ?? 0) * 100)}%]
                            </span>
                          ))}
                        </div>
                      )}

                      <div className="text-[10px] text-slate-500 flex items-center justify-between">
                        <span>BBox: [{(sub?.bbox || []).join(', ')}]</span>
                        {sub?.velocity_vector && (
                          <span>Velocity: [{sub.velocity_vector.join(', ')}]</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : incident.actors && incident.actors.length > 0 ? (
                <div className="space-y-1.5">
                  {incident.actors.map((actor, idx) => (
                    <div
                      key={`${actor?.id ?? idx}_${idx}`}
                      className="p-2 bg-[#080B10] border border-[#1E2631] flex flex-col gap-0.5"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-white">
                          Track #{actor?.id ?? idx + 1} &bull;{' '}
                          <span className="text-[#EF4444] uppercase">{actor?.role || 'suspect'}</span>
                        </span>
                        <span className="text-[10px] px-1.5 py-0.5 bg-[#161E29] border border-[#2D3748] text-[#F59E0B] font-bold uppercase">
                          Action: {actor?.action || incident.actionType}
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-300">Tư thế: {actor?.posture || 'N/A'}</div>
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

          {/* Cột Phải: Action Validation, Weapon Info, Audit & Reasoning (5 Cột) */}
          <div className="col-span-12 lg:col-span-5 flex flex-col justify-between space-y-3">
            <div className="space-y-3">
              {/* Metadata Camera & Audit */}
              <div className="bg-[#121822] p-3 border border-[#1E2631]">
                <div className="text-[10px] font-mono text-[#64748B] uppercase font-bold">
                  THÔNG TIN CAMERA &amp; KIỂM TOÁN (CAMERA &amp; AUDIT)
                </div>
                <div className="font-mono text-xs text-slate-300 mt-1.5 space-y-1 leading-relaxed">
                  <div>
                    <strong>Camera:</strong>{' '}
                    <span className="text-[#38BDF8] font-bold">
                      {incident.cameraName || incident.cameraId} ({incident.cameraId})
                    </span>
                  </div>
                  <div>
                    <strong>Vị trí (Address):</strong>{' '}
                    <span className="text-white">{incident.location || incident.subTitle}</span>
                    {incident.cameraMeta?.zone_id && (
                      <span className="text-slate-400"> [{incident.cameraMeta.zone_id}]</span>
                    )}
                  </div>
                  {incident.cameraMeta?.latitude !== undefined && (
                    <div>
                      <strong>Tọa độ GPS:</strong> {incident.cameraMeta.latitude},{' '}
                      {incident.cameraMeta.longitude}
                    </div>
                  )}
                  <div>
                    <strong>Thời điểm:</strong> {incident.timestamp}
                  </div>
                  {incident.auditInfo?.ai_model && (
                    <div>
                      <strong>AI Pipeline:</strong>{' '}
                      <span className="text-[#10B981]">{incident.auditInfo.ai_model}</span>
                    </div>
                  )}
                  {incident.auditInfo?.hash_algorithm && (
                    <div className="text-[11px] text-slate-400">
                      <strong>Hash Algo:</strong> {incident.auditInfo.hash_algorithm}
                    </div>
                  )}
                </div>
              </div>

              {/* Thông tin Vũ khí (Weapon Info) */}
              {incident.weaponInfo && (
                <div className="bg-[#180A0A] p-3 border border-[#7F1D1D] font-mono text-xs space-y-1">
                  <div className="text-[10px] text-[#EF4444] uppercase font-bold flex items-center justify-between">
                    <span className="flex items-center gap-1">
                      <Crosshair className="w-3.5 h-3.5" />
                      PHÁT HIỆN VŨ KHÍ / TƯ THẾ TÁC CHIẾN (WEAPON INFO)
                    </span>
                    <span>CONF: {Math.round((incident.weaponInfo.confidence ?? 0.95) * 100)}%</span>
                  </div>
                  <div className="text-white font-bold">
                    Loại: {(incident.weaponInfo.weapon_types || []).join(', ') || 'WEAPON_DETECTED'}
                  </div>
                  {incident.weaponInfo.description && (
                    <div className="text-[11px] text-[#FECACA]">{incident.weaponInfo.description}</div>
                  )}
                </div>
              )}

              {/* Xác thực Hành vi Đa phương thức (Action Validation) */}
              {incident.actionValidation && (
                <div className="bg-[#121822] p-3 border border-[#1E2631] font-mono text-xs space-y-1.5">
                  <div className="text-[10px] text-[#38BDF8] uppercase font-bold flex items-center justify-between">
                    <span className="flex items-center gap-1">
                      <ShieldAlert className="w-3.5 h-3.5" />
                      XÁC THỰC ĐA PHƯƠNG THỨC ({incident.actionValidation.validation_source || 'VLM'})
                    </span>
                    <span className="text-[#10B981]">
                      Benign Prob:{' '}
                      {incident.actionValidation.benign_hypothesis_probability !== undefined
                        ? `${Math.round(incident.actionValidation.benign_hypothesis_probability * 100)}%`
                        : 'N/A'}
                    </span>
                  </div>
                  <div className="text-xs text-white leading-relaxed font-sans">
                    {incident.actionValidation.reasoning}
                  </div>
                </div>
              )}

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

              {/* Mô tả & Lý giải VLM (Reasoning & vlmAnalysis) */}
              <div className="bg-[#121822] p-3 border border-[#1E2631] space-y-1.5">
                <div className="text-[10px] font-mono text-[#64748B] uppercase font-bold">
                  PHÂN TÍCH HÀNH VI &amp; LẬP LUẬN (REASONING &amp; VLM ANALYSIS)
                </div>
                <div className="text-xs text-slate-200 leading-relaxed">
                  {incident.reasoning || incident.vlmAnalysis}
                </div>
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
              <span>XÁC NHẬN &amp; ĐIỀU PHỐI (DISPATCH)</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
