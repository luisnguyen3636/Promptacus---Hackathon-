import React, { useRef, useState, useEffect } from 'react';
import { ICameraDevice } from '../../types/soc.ts';
import { useCctvCanvas } from '../../hooks/useCctvCanvas.ts';
import { Maximize2, Minimize2, RefreshCw, AlertCircle } from 'lucide-react';

interface CameraSlotProps {
  camera: ICameraDevice;
  isZoomed?: boolean;
  onToggleZoom?: (cameraId: string) => void;
  digitalZoom?: number;
}

export const CameraSlot: React.FC<CameraSlotProps> = ({
  camera,
  isZoomed = false,
  onToggleZoom,
  digitalZoom = 1.0,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [streamError, setStreamError] = useState<boolean>(false);
  const [streamLoaded, setStreamLoaded] = useState<boolean>(false);
  const [currentStreamSrc, setCurrentStreamSrc] = useState<string>(camera.streamUrl || '');
  const [retryCount, setRetryCount] = useState<number>(0);

  // Kiểm tra nếu camera có URL live stream HTTP/HTTPS hoặc route proxy
  const isHttpStream = Boolean(
    camera.streamUrl &&
    (camera.streamUrl.startsWith('http://') ||
     camera.streamUrl.startsWith('https://') ||
     camera.streamUrl.startsWith('/api/'))
  );

  useEffect(() => {
    setCurrentStreamSrc(camera.streamUrl || '');
    setStreamError(false);
  }, [camera.streamUrl]);

  // Tự động chuyển qua directStreamUrl nếu proxy bị gián đoạn
  const handleStreamError = () => {
    if (camera.directStreamUrl && currentStreamSrc !== camera.directStreamUrl) {
      console.warn(`[CameraSlot ${camera.id}] Stream proxy error, fallback to directStreamUrl:`, camera.directStreamUrl);
      setCurrentStreamSrc(camera.directStreamUrl);
    } else {
      setStreamError(true);
      setStreamLoaded(false);
    }
  };

  const handleManualRetry = (e: React.MouseEvent) => {
    e.stopPropagation();
    setStreamError(false);
    setRetryCount((prev) => prev + 1);
    setCurrentStreamSrc(
      `${camera.streamUrl || ''}${camera.streamUrl?.includes('?') ? '&' : '?'}retry=${Date.now()}`
    );
  };

  useCctvCanvas(canvasRef, camera, isHttpStream && streamLoaded && !streamError);

  const zoomScale = Math.max(1.0, Math.min(3.5, digitalZoom || camera.ptzState?.zoom || 1.0));

  return (
    <div
      onClick={() => onToggleZoom && onToggleZoom(camera.id)}
      className={`relative bg-[#05070A] overflow-hidden select-none min-w-0 group cursor-pointer transition-all duration-200 ${
        isZoomed ? 'w-full h-full' : 'aspect-[16/10]'
      } border ${isZoomed ? 'border-[#3B82F6]' : 'border-[#1E2631] hover:border-[#3B82F6]'}`}
    >
      {/* 1. Luồng Video Trực tiếp (MJPEG Stream) */}
      {isHttpStream && (
        <img
          key={`${currentStreamSrc}-${retryCount}`}
          src={currentStreamSrc}
          alt={camera.name}
          onLoad={() => {
            setStreamLoaded(true);
            setStreamError(false);
          }}
          onError={handleStreamError}
          className="absolute inset-0 w-full h-full object-cover z-0 transition-transform duration-150"
          style={{ transform: `scale(${zoomScale})` }}
        />
      )}

      {/* Thông báo Fallback khi Stream đang kết nối lại */}
      {isHttpStream && streamError && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-[#080B10]/90 z-10 p-3 text-center pointer-events-auto">
          <AlertCircle className="w-6 h-6 text-[#F59E0B] mb-1.5 animate-pulse" />
          <div className="font-mono text-xs font-bold text-white uppercase tracking-wider">
            Tín hiệu luồng đang kết nối lại
          </div>
          <div className="text-[10px] font-mono text-[#94A3B8] max-w-[260px] truncate mt-0.5">
            {currentStreamSrc}
          </div>
          <button
            onClick={handleManualRetry}
            className="mt-2.5 px-2.5 py-1 bg-[#161E29] border border-[#2D3748] hover:border-[#3B82F6] text-white font-mono text-[10px] font-bold flex items-center gap-1.5 cursor-pointer"
          >
            <RefreshCw className="w-3 h-3" />
            <span>KẾT NỐI LẠI</span>
          </button>
        </div>
      )}

      {/* 2. Canvas AI Bounding Boxes Overlay */}
      <canvas ref={canvasRef} className="absolute inset-0 w-full h-full pointer-events-none z-10" />

      {/* 3. Lớp Phủ Thông tin Kỹ thuật (Góc trên trái) */}
      <div className="absolute top-1.5 left-1.5 bg-[rgba(8,11,16,0.85)] border-l-2 border-[#3B82F6] px-2 py-1 font-mono text-[10px] leading-tight z-20 pointer-events-none max-w-[65%] overflow-hidden shadow-sm">
        <div className="font-bold text-white truncate" title={camera.name}>
          {camera.name}
        </div>
        <div className="text-slate-400 truncate" title={`IP: ${camera.ip}`}>
          IP: {camera.ip}
        </div>
        <div className="text-slate-400 truncate">
          FPS: {camera.fps || (streamLoaded ? 30 : 0)} &bull; Bitrate: {camera.bitrateKbps || (streamLoaded ? 2048 : 0)}kbps
        </div>
        {zoomScale > 1.0 && (
          <div className="text-[#3B82F6] font-bold">
            ZOOM: {zoomScale.toFixed(1)}x
          </div>
        )}
      </div>

      {/* 4. Nhãn LIVE Đỏ & Nút Zoom (Góc trên phải) */}
      <div className="absolute top-1.5 right-1.5 flex items-center gap-1 z-20">
        <div className="bg-[#DC2626] text-white font-mono text-[9px] font-bold px-1.5 py-0.5 tracking-wider pointer-events-none shrink-0 shadow-sm flex items-center gap-1">
          <span className="w-1.5 h-1.5 bg-white rounded-full animate-ping"></span>
          <span>LIVE</span>
        </div>

        <button
          onClick={(e) => {
            e.stopPropagation();
            onToggleZoom && onToggleZoom(camera.id);
          }}
          title={isZoomed ? "Thu nhỏ về lưới 2x2" : "Phóng to camera để quan sát"}
          className="w-6 h-6 bg-[rgba(8,11,16,0.85)] border border-[#1E2631] text-[#94A3B8] hover:text-white hover:border-[#3B82F6] flex items-center justify-center cursor-pointer transition-colors"
        >
          {isZoomed ? <Minimize2 className="w-3.5 h-3.5 text-[#3B82F6]" /> : <Maximize2 className="w-3.5 h-3.5" />}
        </button>
      </div>
    </div>
  );
};
