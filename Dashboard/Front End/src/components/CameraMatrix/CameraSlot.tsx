import React, { useRef, useState, useEffect } from 'react';
import { ICameraDevice } from '../../types/soc.ts';
import { useCctvCanvas } from '../../hooks/useCctvCanvas.ts';
import { AlertTriangle, ShieldAlert, Radio } from 'lucide-react';

interface CameraSlotProps {
  camera: ICameraDevice;
  onOpenPlayback?: (cameraId: string) => void;
}

export const CameraSlot: React.FC<CameraSlotProps> = ({ camera, onOpenPlayback }) => {
  const overlayCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const standbyCanvasRef = useRef<HTMLCanvasElement | null>(null);

  const [streamActive, setStreamActive] = useState<boolean>(true);
  const [streamError, setStreamError] = useState<boolean>(false);

  // Overlay canvas vẽ bounding boxes trên luồng live video
  useCctvCanvas(overlayCanvasRef, camera, true);
  // Standby canvas vẽ nền camera khi chưa có luồng
  useCctvCanvas(standbyCanvasRef, camera, false);

  const streamSrc = camera.streamUrl || `/api/v1/cameras/${camera.id}/stream`;
  const hasAlert = Boolean(camera.aiAlert && camera.aiAlert.hasAlert);
  const isCritical = camera.aiAlert?.severity === 'CRITICAL';

  // Tự động thử lại kết nối stream sau 5 giây nếu lỗi
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    if (streamError) {
      timer = setTimeout(() => {
        setStreamError(false);
      }, 5000);
    }
    return () => clearTimeout(timer);
  }, [streamError]);

  return (
    <div
      className={`relative bg-[#05070A] overflow-hidden aspect-[16/10] select-none min-w-0 transition-all ${
        hasAlert
          ? isCritical
            ? 'border-2 border-[#EF4444] shadow-[0_0_20px_rgba(239,68,68,0.7)] animate-pulse'
            : 'border-2 border-[#F59E0B] shadow-[0_0_15px_rgba(245,158,11,0.6)]'
          : 'border border-[#1E2631]'
      }`}
    >
      {/* 1. Luồng Hình Ảnh Trực Tiếp từ Camera Client (MJPEG / Live Feed) */}
      {!streamError ? (
        <img
          src={streamSrc}
          alt={camera.name}
          className="absolute inset-0 w-full h-full object-cover z-0"
          onLoad={() => {
            setStreamActive(true);
            setStreamError(false);
          }}
          onError={() => {
            setStreamError(true);
            setStreamActive(false);
          }}
        />
      ) : (
        /* 2. Màn hình chờ Standby CCTV khi chưa kết nối luồng */
        <canvas ref={standbyCanvasRef} className="absolute inset-0 w-full h-full pointer-events-none z-0" />
      )}

      {/* 3. Lớp Overlay Trong Suốt Vẽ AI Bounding Boxes & Crosshairs */}
      <canvas ref={overlayCanvasRef} className="absolute inset-0 w-full h-full pointer-events-none z-10" />

      {/* 4. Lớp Phủ Thông Tin Kỹ Thuật (Góc trên trái) */}
      <div className="absolute top-1.5 left-1.5 bg-[rgba(8,11,16,0.85)] border-l-2 border-[#3B82F6] px-2 py-1 font-mono text-[10px] leading-tight z-20 pointer-events-none max-w-[65%] overflow-hidden">
        <div className="font-bold text-white truncate" title={camera.name}>
          {camera.name}
        </div>
        <div className="text-slate-400 truncate" title={`IP: ${camera.ip}`}>
          IP: {camera.ip}
        </div>
        <div className="flex items-center gap-2 text-slate-400 truncate">
          <span>FPS: {camera.fps}</span>
          <span>·</span>
          <span>{camera.bitrateKbps}kbps</span>
        </div>
      </div>

      {/* 5. Nhãn Trạng Thái Trực Tiếp / Báo Động (Góc trên phải) */}
      <div className="absolute top-1.5 right-1.5 flex items-center gap-1 z-20">
        {hasAlert ? (
          <div className="flex items-center gap-1 bg-[#EF4444] text-white font-mono text-[9px] font-bold px-2 py-0.5 tracking-wider shadow-md animate-bounce">
            <ShieldAlert className="w-3 h-3" />
            <span>ALERT: {camera.aiAlert?.type}</span>
            {camera.aiAlert?.aiProvider && <span className="border-l border-white/40 pl-1">{camera.aiAlert.aiProvider}</span>}
          </div>
        ) : (
          <div className="flex items-center gap-1 bg-[#DC2626] text-white font-mono text-[9px] font-bold px-1.5 py-0.5 tracking-wider shrink-0">
            <Radio className="w-2.5 h-2.5 animate-pulse text-white" />
            <span>LIVE</span>
          </div>
        )}
      </div>

      {/* 6. BANNER CẢNH BÁO AI NGUY CẤP (Xử lý Alert từ AI) */}
      {hasAlert && (
        <div className="absolute bottom-1.5 inset-x-1.5 z-20 bg-[rgba(15,23,42,0.92)] border border-[#EF4444] px-2.5 py-1.5 flex items-center justify-between text-white font-mono">
          <div className="flex items-center gap-2 overflow-hidden">
            <AlertTriangle className="w-4 h-4 text-[#EF4444] shrink-0 animate-pulse" />
            <div className="truncate">
              <span className="text-[#EF4444] font-bold text-[10px] uppercase">
                [{camera.aiAlert?.type}]
              </span>
              <span className="text-[10px] text-slate-200 ml-1.5 truncate">
                {camera.aiAlert?.message || 'Phát hiện hành vi nguy hiểm'}
              </span>
            </div>
          </div>

          {camera.aiAlert?.confidence && (
            <div className="bg-[#EF4444]/20 border border-[#EF4444]/60 text-[#EF4444] font-bold text-[9px] px-1.5 py-0.5 shrink-0 ml-2">
              {Math.round(camera.aiAlert.confidence * 100)}% TIN CẬY
            </div>
          )}
        </div>
      )}
    </div>
  );
};
