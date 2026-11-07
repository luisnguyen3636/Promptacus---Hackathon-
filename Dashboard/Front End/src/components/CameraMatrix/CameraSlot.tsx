import React, { useRef } from 'react';
import { ICameraDevice } from '../../types/soc.ts';
import { useCctvCanvas } from '../../hooks/useCctvCanvas.ts';

interface CameraSlotProps {
  camera: ICameraDevice;
}

export const CameraSlot: React.FC<CameraSlotProps> = ({ camera }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  useCctvCanvas(canvasRef, camera);

  return (
    <div className="relative bg-[#05070A] overflow-hidden aspect-[16/10] select-none min-w-0">
      {/* Lớp Phủ Thông tin Kỹ thuật (Góc trên trái - Giới hạn 65% chống tràn đè nhãn LIVE) */}
      <div className="absolute top-1.5 left-1.5 bg-[rgba(8,11,16,0.85)] border-l-2 border-[#3B82F6] px-2 py-1 font-mono text-[10px] leading-tight z-10 pointer-events-none max-w-[65%] overflow-hidden">
        <div className="font-bold text-white truncate" title={camera.name}>
          {camera.name}
        </div>
        <div className="text-slate-400 truncate" title={`IP: ${camera.ip}`}>
          IP: {camera.ip}
        </div>
        <div className="text-slate-400 truncate">
          FPS: {camera.fps}
        </div>
        <div className="text-slate-400 truncate">
          Bitrate: {camera.bitrateKbps}kbps
        </div>
      </div>

      {/* Nhãn LIVE Đỏ (Góc trên phải) */}
      <div className="absolute top-1.5 right-1.5 bg-[#DC2626] text-white font-mono text-[9px] font-bold px-1.5 py-0.5 tracking-wider z-10 pointer-events-none shrink-0">
        LIVE
      </div>

      {/* Canvas vẽ khung hình CCTV và AI Bounding Boxes */}
      <canvas ref={canvasRef} className="absolute inset-0 w-full h-full pointer-events-none z-0" />
    </div>
  );
};
