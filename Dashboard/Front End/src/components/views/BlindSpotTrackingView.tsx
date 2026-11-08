import React, { useState, useEffect } from 'react';
import {
  Radar,
  ArrowRight,
  ShieldAlert,
  CheckCircle2,
  XCircle,
  Clock,
  Compass,
  Footprints,
  Eye,
  Camera,
  RefreshCw,
  GitCommit,
  Check,
  AlertTriangle
} from 'lucide-react';
import { IBlindSpotSession } from '../../types/soc.ts';

interface BlindSpotTrackingViewProps {
  onToast?: (msg: string) => void;
  onNavigateToWanted?: () => void;
}

export const BlindSpotTrackingView: React.FC<BlindSpotTrackingViewProps> = ({
  onToast,
  onNavigateToWanted,
}) => {
  const [sessions, setSessions] = useState<IBlindSpotSession[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const fetchSessions = async () => {
    setIsLoading(true);
    try {
      const res = await fetch('/api/v1/blind-spot/sessions');
      if (res.ok) {
        const data = await res.json();
        setSessions(data.data || []);
        if (data.data?.length > 0 && !selectedSessionId) {
          setSelectedSessionId(data.data[0].sessionId);
        }
      }
    } catch {
      // Local fallback
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchSessions();
  }, []);

  const currentSession = sessions.find((s) => s.sessionId === selectedSessionId) || sessions[0];

  const handleVerify = async (sessionId: string, decision: 'CONFIRM' | 'REJECT') => {
    try {
      const res = await fetch('/api/v1/blind-spot/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sessionId,
          decision,
          operatorId: 'OP-VN-PSOC-804',
        }),
      });
      if (res.ok) {
        const data = await res.json();
        onToast?.(
          decision === 'CONFIRM'
            ? `[SUY LUẬN VÙNG MÙ] Đã xác thực thành công liên kết truy vết nghi phạm qua 2 camera!`
            : `[SUY LUẬN VÙNG MÙ] Đã bác bỏ liên kết không khớp`
        );
        fetchSessions();
      }
    } catch {
      onToast?.('[LỖI] Không thể xử lý xác thực');
    }
  };

  const handleTriggerNewCorrelation = async () => {
    try {
      const res = await fetch('/api/v1/blind-spot/correlate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sourceCameraId: 'CAM_01',
          destinationCameraId: 'CAM_02',
          blindSpotZone: 'BS_ZONE_01 (Hẻm 12 Chu Văn An)',
          transitTimeSec: 22,
        }),
      });
      if (res.ok) {
        onToast?.('[AI BLIND SPOT] Đã kích hoạt phiên suy luận liên camera mới!');
        fetchSessions();
      }
    } catch {
      onToast?.('[LỖI] Không thể kích hoạt suy luận');
    }
  };

  return (
    <div className="space-y-4 select-none min-w-0">
      {/* Header Panel */}
      <div className="bg-[#0E131A] border border-[#1E2631] px-4 py-3 flex items-center justify-between min-w-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-[#10B981]/20 border border-[#10B981] flex items-center justify-center shrink-0">
            <Radar className="w-4 h-4 text-[#10B981]" />
          </div>
          <div>
            <div className="font-bold text-sm text-white tracking-wide flex items-center gap-2">
              <span>PANEL SUY LUẬN VÙNG MÙ & TRUY VẾT TỘI PHẠM ĐA CAMERA</span>
              <span className="bg-[#112224] text-[#10B981] border border-[#10B981] text-[10px] font-mono px-2 py-0.5 font-bold">
                {sessions.length} PHIÊN TRUY VẾT
              </span>
            </div>
            <div className="text-[11px] font-mono text-slate-400">
              Thuật toán 5 yếu tố suy luận vùng khuất tầm nhìn (&ge; 2 Camera) &bull; So khớp Re-ID ngoại hình nghi phạm
            </div>
          </div>
        </div>

        <button
          onClick={handleTriggerNewCorrelation}
          className="px-3.5 py-1.5 bg-[#10B981] hover:bg-[#059669] text-black font-mono font-bold text-xs inline-flex items-center gap-1.5 transition-colors cursor-pointer"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>KÍCH HOẠT SUY LUẬN MỚI</span>
        </button>
      </div>

      {currentSession && (
        <>
          {/* KHUNG SO KHỚP HÌNH ẢNH TRỰC DIỆN GIỮA 2 CAMERA (>= 2 CAMERAS) */}
          <div className="bg-[#0A0E17] border border-[#1E2631] p-4 space-y-4">
            <div className="flex items-center justify-between border-b border-[#1E2631] pb-3">
              <div className="flex items-center gap-2">
                <Compass className="w-4 h-4 text-[#06B6D4]" />
                <span className="font-bold text-xs text-white uppercase font-mono">
                  PHIÊN TRUY VẾT: {currentSession.sessionId} &bull; VÙNG MÙ: {currentSession.blindSpotZone}
                </span>
              </div>
              <div className="flex items-center gap-2 font-mono text-xs">
                <span className="text-slate-400">Trạng thái xác thực:</span>
                <span
                  className={`px-2 py-0.5 font-bold border uppercase text-[10px] ${
                    currentSession.operatorVerification === 'CONFIRMED'
                      ? 'bg-[#0E1E1C] border-[#10B981] text-[#10B981]'
                      : currentSession.operatorVerification === 'REJECTED'
                      ? 'bg-[#7F1D1D] border-[#DC2626] text-white'
                      : 'bg-[#78350F] border-[#F59E0B] text-amber-200 animate-pulse'
                  }`}
                >
                  {currentSession.operatorVerification === 'CONFIRMED'
                    ? 'ĐÃ XÁC THỰC LIÊN KẾT'
                    : currentSession.operatorVerification === 'REJECTED'
                    ? 'ĐÃ BÁC BỎ'
                    : 'CHỜ OPERATOR XÁC NHẬN'}
                </span>
              </div>
            </div>

            {/* BỐ CỤC 3 KHỐI: CAMERA 1 -> VÙNG MÙ TRUNG GIAN -> CAMERA 2 */}
            <div className="grid grid-cols-12 gap-3 items-center">
              {/* KHỐI 1: CAMERA NGUỒN (CAM_01) */}
              <div className="col-span-4 bg-[#0E131A] border border-[#1E2631] p-3 space-y-2">
                <div className="flex items-center justify-between pb-1.5 border-b border-[#1E2631]">
                  <span className="text-xs font-bold text-white font-mono flex items-center gap-1.5">
                    <Camera className="w-3.5 h-3.5 text-[#06B6D4]" />
                    {currentSession.sourceCameraId} ({currentSession.sourceCameraName})
                  </span>
                  <span className="text-[10px] font-mono text-[#06B6D4] bg-[#06B6D4]/10 px-1.5 py-0.5 border border-[#06B6D4]/40">
                    NGUỒN RỜI ĐI
                  </span>
                </div>

                {/* Keyframe Camera 1 */}
                <div className="aspect-video bg-black border border-[#243042] relative overflow-hidden flex items-center justify-center">
                  <img
                    src={currentSession.sourceKeyframeUrl}
                    alt="Source Camera Keyframe"
                    className="w-full h-full object-cover"
                    onError={(e) => {
                      (e.target as HTMLElement).style.opacity = '0.3';
                    }}
                  />
                  <div className="absolute top-1 left-1 bg-black/80 px-1.5 py-0.5 text-[9px] font-mono text-white">
                    Ảnh đầu vào 1
                  </div>
                  <div className="absolute bottom-1 right-1 bg-red-950/80 border border-red-600 px-1.5 py-0.5 text-[9px] font-mono text-white">
                    HƯỚNG THOÁT: {currentSession.exitGate}
                  </div>
                </div>

                <div className="text-[11px] font-mono text-slate-300 space-y-1">
                  <div>
                    <span className="text-slate-500">Thời điểm rời đi:</span>{' '}
                    {new Date(currentSession.sourceExitTime).toLocaleTimeString()}
                  </div>
                  <div>
                    <span className="text-slate-500">Cổng thoát:</span>{' '}
                    <span className="text-amber-300 font-bold">{currentSession.exitGate}</span>
                  </div>
                </div>
              </div>

              {/* KHỐI 2: VÙNG MÙ TRUNG GIAN & THUẬT TOÁN SUY LUẬN (4 COLS) */}
              <div className="col-span-4 bg-[#111823] border border-[#243042] p-3 text-center space-y-2.5">
                <div className="font-bold text-xs text-amber-400 font-mono uppercase flex items-center justify-center gap-1.5">
                  <Radar className="w-4 h-4 animate-spin text-amber-400" />
                  <span>SUY LUẬN VÙNG MÙ (5-FACTOR AI)</span>
                </div>

                {/* Điểm Re-ID Similarity Lớn */}
                <div className="bg-[#0A0E17] border border-[#1E2631] py-2 px-3 space-y-1">
                  <div className="text-[10px] font-mono text-slate-400">ĐỘ TƯƠNG ĐỒNG NGOẠI HÌNH (RE-ID)</div>
                  <div className="text-2xl font-bold font-mono text-[#10B981]">
                    {(currentSession.reidSimilarityScore * 100).toFixed(1)}%
                  </div>
                  <div className="text-[10px] font-mono text-slate-400">
                    Trang phục &bull; Dáng đi &bull; Tỷ lệ cơ thể
                  </div>
                </div>

                {/* So sánh Thời gian Di chuyển Thực tế vs ETA */}
                <div className="grid grid-cols-2 gap-2 text-left font-mono text-[10px] bg-[#0A0E17] p-2 border border-[#1E2631]">
                  <div>
                    <span className="text-slate-500 block">DỰ KIẾN (ETA):</span>
                    <span className="text-slate-200 font-bold">
                      {currentSession.targetCandidates[0]?.estimatedTransitSec || 18.5} giây
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">THỰC TẾ (TRANSIT):</span>
                    <span className="text-[#10B981] font-bold">{currentSession.actualTransitSec} giây</span>
                  </div>
                </div>

                {/* Hành vi giấu kín dự đoán trong vùng mù */}
                <div className="text-left font-mono text-[10px] space-y-1">
                  <span className="text-slate-400 block uppercase">Dự đoán hành vi trong vùng mù:</span>
                  <div className="flex flex-wrap gap-1">
                    {currentSession.hiddenActionPredictions.map((act, aIdx) => (
                      <span
                        key={aIdx}
                        className="bg-[#1F2937] border border-amber-500/40 text-amber-300 px-1.5 py-0.5 text-[9px]"
                      >
                        {act}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* KHỐI 3: CAMERA ĐÍCH (CAM_02) */}
              <div className="col-span-4 bg-[#0E131A] border border-[#1E2631] p-3 space-y-2">
                <div className="flex items-center justify-between pb-1.5 border-b border-[#1E2631]">
                  <span className="text-xs font-bold text-white font-mono flex items-center gap-1.5">
                    <Camera className="w-3.5 h-3.5 text-[#10B981]" />
                    {currentSession.destinationCameraId} ({currentSession.destinationCameraName})
                  </span>
                  <span className="text-[10px] font-mono text-[#10B981] bg-[#10B981]/10 px-1.5 py-0.5 border border-[#10B981]/40">
                    ĐÍCH XUẤT HIỆN
                  </span>
                </div>

                {/* Keyframe Camera 2 */}
                <div className="aspect-video bg-black border border-[#243042] relative overflow-hidden flex items-center justify-center">
                  <img
                    src={currentSession.destinationKeyframeUrl}
                    alt="Destination Camera Keyframe"
                    className="w-full h-full object-cover"
                    onError={(e) => {
                      (e.target as HTMLElement).style.opacity = '0.3';
                    }}
                  />
                  <div className="absolute top-1 left-1 bg-black/80 px-1.5 py-0.5 text-[9px] font-mono text-white">
                    Ảnh đầu vào 2
                  </div>
                  <div className="absolute bottom-1 right-1 bg-emerald-950/80 border border-emerald-600 px-1.5 py-0.5 text-[9px] font-mono text-white">
                    XÁC SUẤT ĐÍCH: 82%
                  </div>
                </div>

                <div className="text-[11px] font-mono text-slate-300 space-y-1">
                  <div>
                    <span className="text-slate-500">Thời điểm xuất hiện:</span>{' '}
                    {new Date(currentSession.destinationEntryTime).toLocaleTimeString()}
                  </div>
                  <div>
                    <span className="text-slate-500">Khoảng cách qua vùng mù:</span>{' '}
                    <span className="text-slate-200">
                      {currentSession.targetCandidates[0]?.distanceMeters || 85} mét
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* BẢNG ĐẶC TRƯNG SO KHỚP NGOẠI HÌNH & NÚT DUYỆT */}
            <div className="bg-[#111823] p-3 border border-[#1E2631] flex items-center justify-between gap-4 font-mono text-xs">
              <div className="space-y-1 flex-1">
                <div className="font-bold text-slate-200 text-xs">
                  CHI TIẾT SO KHỚP ĐẶC TRƯNG HÌNH THỂ (BIOMETRIC RE-ID MATCH):
                </div>
                <div className="grid grid-cols-3 gap-2 text-[11px] text-slate-300">
                  <div>• Thân trên: {currentSession.clothingMatch?.upperBody}</div>
                  <div>• Thân dưới: {currentSession.clothingMatch?.lowerBody}</div>
                  <div>• Phụ kiện: {currentSession.clothingMatch?.accessories}</div>
                </div>
              </div>

              {/* Nút Quyết định của Điều hành viên */}
              <div className="flex items-center gap-2 shrink-0">
                <button
                  onClick={() => handleVerify(currentSession.sessionId, 'CONFIRM')}
                  className="px-3.5 py-2 bg-[#10B981] hover:bg-[#059669] text-black font-bold inline-flex items-center gap-1.5 cursor-pointer"
                >
                  <Check className="w-4 h-4" />
                  <span>XÁC THỰC DẤU VẾT</span>
                </button>

                <button
                  onClick={() => onNavigateToWanted?.()}
                  className="px-3.5 py-2 bg-[#06B6D4] hover:bg-[#0891B2] text-black font-bold inline-flex items-center gap-1.5 cursor-pointer"
                >
                  <ShieldAlert className="w-4 h-4" />
                  <span>GẮN HỒ SƠ TRUY NÃ</span>
                </button>

                <button
                  onClick={() => handleVerify(currentSession.sessionId, 'REJECT')}
                  className="px-3 py-2 bg-[#161E29] border border-[#243042] text-red-400 hover:text-white hover:border-red-500 cursor-pointer"
                >
                  BÁC BỎ
                </button>
              </div>
            </div>
          </div>
        </>
      )}

      {/* DANH SÁCH TẤT CẢ CÁC PHIÊN TRUY VẾT VÙNG MÙ */}
      <div className="bg-[#0A0E17] border border-[#1E2631] p-3 space-y-2 font-mono text-xs">
        <div className="font-bold text-white text-xs border-b border-[#1E2631] pb-2 flex items-center justify-between">
          <span>DANH SÁCH PHIÊN TRUY VẾT VÙNG MÙ QUA NHIỀU CAMERA</span>
          <span className="text-slate-400 text-[10px]">Tự động suy luận khi nghi phạm rời khung hình</span>
        </div>

        <div className="space-y-1.5">
          {sessions.map((ses) => {
            const isSelected = ses.sessionId === selectedSessionId;
            return (
              <div
                key={ses.sessionId}
                onClick={() => setSelectedSessionId(ses.sessionId)}
                className={`p-2.5 border flex items-center justify-between cursor-pointer transition-colors ${
                  isSelected
                    ? 'bg-[#112224] border-[#10B981]'
                    : 'bg-[#0E131A] border-[#1E2631] hover:border-slate-500'
                }`}
              >
                <div className="flex items-center gap-3">
                  <span className="font-bold text-[#10B981]">{ses.sessionId}</span>
                  <div className="flex items-center gap-2 text-slate-300">
                    <span className="bg-[#161E29] px-2 py-0.5 border border-[#243042] text-[#06B6D4]">
                      {ses.sourceCameraId}
                    </span>
                    <ArrowRight className="w-3.5 h-3.5 text-slate-500" />
                    <span className="text-amber-400">[{ses.blindSpotZone}]</span>
                    <ArrowRight className="w-3.5 h-3.5 text-slate-500" />
                    <span className="bg-[#161E29] px-2 py-0.5 border border-[#243042] text-[#10B981]">
                      {ses.destinationCameraId}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <span className="text-slate-400">
                    Re-ID: <span className="text-[#10B981] font-bold">{(ses.reidSimilarityScore * 100).toFixed(1)}%</span>
                  </span>
                  <span className="text-slate-400">
                    Transit: {ses.actualTransitSec}s
                  </span>
                  <span
                    className={`px-2 py-0.5 border text-[10px] font-bold uppercase ${
                      ses.operatorVerification === 'CONFIRMED'
                        ? 'border-[#10B981] text-[#10B981]'
                        : ses.operatorVerification === 'REJECTED'
                        ? 'border-red-500 text-red-400'
                        : 'border-amber-500 text-amber-300'
                    }`}
                  >
                    {ses.operatorVerification}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
