import React, { useState, useEffect, useRef } from 'react';
import {
  Maximize2,
  Minimize2,
  VideoOff,
  Link2,
  Check,
  X,
} from 'lucide-react';

declare global {
  interface Window {
    Hls?: any;
  }
}

interface CameraSlotProps {
  slotIndex: number;
  cameraLabel: string;
  isZoomed?: boolean;
  onToggleZoom?: (slotIndex: number) => void;
  digitalZoom?: number;
}

function ensureHlsJsLoaded(): Promise<any> {
  if (typeof window === 'undefined') return Promise.resolve(null);
  if (window.Hls) return Promise.resolve(window.Hls);

  return new Promise((resolve) => {
    const existing = document.querySelector('script[data-hls-js="true"]') as HTMLScriptElement | null;
    if (existing) {
      existing.addEventListener('load', () => resolve(window.Hls));
      existing.addEventListener('error', () => resolve(null));
      return;
    }
    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/hls.js@1/dist/hls.min.js';
    script.async = true;
    script.setAttribute('data-hls-js', 'true');
    script.onload = () => resolve(window.Hls);
    script.onerror = () => resolve(null);
    document.head.appendChild(script);
  });
}

const CameraSlotInner: React.FC<CameraSlotProps> = ({
  slotIndex,
  cameraLabel,
  isZoomed = false,
  onToggleZoom,
  digitalZoom = 1.0,
}) => {
  const storageKey = `SOC_CAMERA_HLS_SLOT_${slotIndex}`;

  const [streamUrl, setStreamUrl] = useState<string>(() => {
    try {
      return localStorage.getItem(storageKey) || '';
    } catch {
      return '';
    }
  });

  const [isInputOpen, setIsInputOpen] = useState<boolean>(false);
  const [draftUrl, setDraftUrl] = useState<string>(streamUrl);
  const [renderMode, setRenderMode] = useState<'VIDEO' | 'IMAGE'>('VIDEO');

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const hlsInstanceRef = useRef<any>(null);

  const zoomScale = Math.max(1.0, Math.min(3.5, digitalZoom || 1.0));

  useEffect(() => {
    if (isInputOpen) {
      setTimeout(() => {
        inputRef.current?.focus();
      }, 20);
    }
  }, [isInputOpen]);

  useEffect(() => {
    const url = streamUrl.trim();
    if (!url) {
      if (hlsInstanceRef.current) {
        hlsInstanceRef.current.destroy();
        hlsInstanceRef.current = null;
      }
      return;
    }

    const lower = url.toLowerCase();
    const isMjpegOrImg =
      lower.includes('.mjpg') ||
      lower.includes('.mjpeg') ||
      lower.endsWith('/stream') ||
      lower.endsWith('.jpg') ||
      lower.endsWith('.jpeg') ||
      lower.startsWith('data:image/');

    if (isMjpegOrImg && !lower.includes('.m3u8')) {
      setRenderMode('IMAGE');
      return;
    }

    setRenderMode('VIDEO');
    let cancelled = false;

    const attachVideo = async () => {
      const videoEl = videoRef.current;
      if (!videoEl) return;

      if (hlsInstanceRef.current) {
        hlsInstanceRef.current.destroy();
        hlsInstanceRef.current = null;
      }

      const isHlsUrl = lower.includes('.m3u8') || lower.includes('hls');

      if (isHlsUrl) {
        if (videoEl.canPlayType('application/vnd.apple.mpegurl')) {
          videoEl.src = url;
          videoEl.play().catch(() => {});
          return;
        }
        const HlsClass = await ensureHlsJsLoaded();
        if (cancelled || !videoRef.current) return;
        if (HlsClass && HlsClass.isSupported()) {
          const hls = new HlsClass({
            enableWorker: true,
            lowLatencyMode: true,
          });
          hlsInstanceRef.current = hls;
          hls.loadSource(url);
          hls.attachMedia(videoRef.current);
          hls.on(HlsClass.Events.MANIFEST_PARSED, () => {
            videoRef.current?.play().catch(() => {});
          });
          return;
        }
      }

      videoEl.src = url;
      videoEl.play().catch(() => {});
    };

    void attachVideo();

    return () => {
      cancelled = true;
      if (hlsInstanceRef.current) {
        hlsInstanceRef.current.destroy();
        hlsInstanceRef.current = null;
      }
    };
  }, [streamUrl]);

  const handleSaveStreamUrl = (e: React.FormEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const trimmed = draftUrl.trim();
    setStreamUrl(trimmed);
    try {
      if (trimmed) {
        localStorage.setItem(storageKey, trimmed);
      } else {
        localStorage.removeItem(storageKey);
      }
    } catch {
      // Ignore storage error
    }
    setIsInputOpen(false);
  };

  const handleClearStreamUrl = (e: React.MouseEvent) => {
    e.stopPropagation();
    setDraftUrl('');
    setStreamUrl('');
    try {
      localStorage.removeItem(storageKey);
    } catch {
      // Ignore
    }
    setIsInputOpen(false);
  };

  return (
    <div
      onClick={() => {
        if (!isInputOpen && onToggleZoom) {
          onToggleZoom(slotIndex);
        }
      }}
      className={`relative bg-[#05070A] overflow-hidden select-none min-w-0 group cursor-pointer transition-all duration-200 ${
        isZoomed ? 'w-full h-full' : 'aspect-[16/10]'
      } border ${isZoomed ? 'border-[#3B82F6]' : 'border-[#1E2631] hover:border-[#3B82F6]'}`}
    >
      {/* 1. Màn hình Video HLS (.m3u8) / Stream thuần túy (Không hiển thị log) */}
      {streamUrl ? (
        <div className="absolute inset-0 z-0 bg-black overflow-hidden">
          {renderMode === 'VIDEO' ? (
            <video
              ref={videoRef}
              autoPlay
              muted
              loop
              playsInline
              onError={() => setRenderMode('IMAGE')}
              className="w-full h-full object-cover transition-transform duration-150"
              style={{ transform: `scale(${zoomScale})` }}
            />
          ) : (
            <img
              src={streamUrl}
              alt={cameraLabel}
              className="w-full h-full object-cover transition-transform duration-150"
              style={{ transform: `scale(${zoomScale})` }}
            />
          )}
        </div>
      ) : (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-[#06090E] z-0 p-4 text-center">
          <VideoOff className="w-7 h-7 text-slate-700 mb-2" />
          <div className="font-mono text-xs font-bold text-slate-500 uppercase tracking-wider">
            {cameraLabel}
          </div>
          <div className="text-[10px] font-mono text-slate-600 mt-1">
            Di chuột vào góc dưới phải để gắn link HLS (.m3u8) / Stream
          </div>
        </div>
      )}

      {/* 2. Nhãn tên Camera nhỏ gọn ở góc trên trái */}
      <div className="absolute top-2 left-2 z-20 bg-[#080B10]/80 border-l-2 border-[#3B82F6] px-2 py-0.5 font-mono text-[10px] text-white font-bold pointer-events-none flex items-center gap-2">
        <span>{cameraLabel}</span>
        {zoomScale > 1.0 && (
          <span className="text-[#3B82F6]">{zoomScale.toFixed(1)}x</span>
        )}
      </div>

      {/* 3. Nhãn LIVE & Nút Phóng to ở góc trên phải */}
      <div className="absolute top-2 right-2 z-20 flex items-center gap-1.5">
        {streamUrl && (
          <div className="bg-[#DC2626] text-white font-mono text-[9px] font-bold px-1.5 py-0.5 flex items-center gap-1 pointer-events-none">
            <span className="w-1.5 h-1.5 bg-white rounded-full animate-ping"></span>
            <span>LIVE</span>
          </div>
        )}
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onToggleZoom && onToggleZoom(slotIndex);
          }}
          title={isZoomed ? 'Thu nhỏ về lưới 2x2' : 'Phóng to camera'}
          className="w-6 h-6 bg-[#080B10]/85 border border-[#1E2631] text-[#94A3B8] hover:text-white hover:border-[#3B82F6] flex items-center justify-center cursor-pointer transition-colors"
        >
          {isZoomed ? (
            <Minimize2 className="w-3.5 h-3.5 text-[#3B82F6]" />
          ) : (
            <Maximize2 className="w-3.5 h-3.5" />
          )}
        </button>
      </div>

      {/* 4. Nút Ẩn (Hidden Button) ở góc dưới phải để mở khung nhập Link HLS */}
      <button
        type="button"
        onMouseDown={(e) => e.stopPropagation()}
        onClick={(e) => {
          e.stopPropagation();
          if (!isInputOpen) {
            setDraftUrl(streamUrl);
          }
          setIsInputOpen((prev) => !prev);
        }}
        title="Nhập link HLS (.m3u8) / Stream cho camera này"
        className={`absolute bottom-2 right-2 z-30 w-6 h-6 bg-[#0B0F17]/90 border text-slate-300 hover:text-[#10B981] hover:border-[#10B981] flex items-center justify-center transition-opacity duration-150 cursor-pointer ${
          isInputOpen
            ? 'opacity-100 border-[#10B981] text-[#10B981]'
            : 'opacity-0 group-hover:opacity-100 border-[#1E2631]'
        }`}
      >
        <Link2 className="w-3.5 h-3.5" />
      </button>

      {/* 5. Hộp Nhập Link HLS Độc lập (Không bị ảnh hưởng bởi bất kỳ lần render nào từ bên ngoài) */}
      {isInputOpen && (
        <form
          onSubmit={handleSaveStreamUrl}
          onClick={(e) => e.stopPropagation()}
          onMouseDown={(e) => e.stopPropagation()}
          onKeyDown={(e) => e.stopPropagation()}
          className="absolute inset-x-2 bottom-10 z-40 bg-[#0E131A] border border-[#10B981] p-2.5 shadow-2xl space-y-2 cursor-default select-text"
        >
          <div className="flex items-center justify-between text-[10px] font-mono text-[#10B981] font-bold uppercase">
            <span>GẮN LINK HLS (.M3U8) / STREAM — {cameraLabel}</span>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setIsInputOpen(false);
              }}
              className="text-slate-400 hover:text-white cursor-pointer"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
          <div className="flex items-center gap-1.5">
            <input
              ref={inputRef}
              type="text"
              value={draftUrl}
              onChange={(e) => setDraftUrl(e.target.value)}
              placeholder="Dán link https://.../index.m3u8 hoặc stream URL..."
              className="flex-1 bg-[#05070A] border border-[#1E2631] px-2.5 py-1.5 text-xs font-mono text-white placeholder-slate-600 focus:outline-none focus:border-[#10B981] select-text"
            />
            <button
              type="submit"
              className="px-3 py-1.5 bg-[#10B981] text-[#05070A] font-mono text-[10px] font-bold hover:bg-[#10B981]/90 flex items-center gap-1 cursor-pointer shrink-0"
            >
              <Check className="w-3.5 h-3.5" />
              <span>LƯU</span>
            </button>
            {streamUrl && (
              <button
                type="button"
                onClick={handleClearStreamUrl}
                className="px-2.5 py-1.5 bg-[#7F1D1D] text-white font-mono text-[10px] font-bold hover:bg-[#DC2626] cursor-pointer shrink-0"
              >
                XÓA
              </button>
            )}
          </div>
        </form>
      )}
    </div>
  );
};

// Memoize CameraSlot so external telemetry/log updates never re-render or interrupt the video/link input
export const CameraSlot = React.memo(
  CameraSlotInner,
  (prev, next) =>
    prev.slotIndex === next.slotIndex &&
    prev.cameraLabel === next.cameraLabel &&
    prev.isZoomed === next.isZoomed &&
    prev.digitalZoom === next.digitalZoom
);
