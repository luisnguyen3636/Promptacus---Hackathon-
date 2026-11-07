import React, { useState, useEffect, useRef } from 'react';
import { ICameraDevice, IIncidentItem } from '../../types/soc.ts';
import {
  Maximize2,
  Minimize2,
  Terminal,
  Radio,
  Users,
  MapPin,
  ShieldAlert,
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
  camera: ICameraDevice;
  slotIndex?: number;
  cameraLogs?: IIncidentItem[];
  isZoomed?: boolean;
  onToggleZoom?: (cameraId: string) => void;
  digitalZoom?: number;
  onSelectLog?: (incident: IIncidentItem) => void;
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

export const CameraSlot: React.FC<CameraSlotProps> = ({
  camera,
  slotIndex = 0,
  cameraLogs = [],
  isZoomed = false,
  onToggleZoom,
  digitalZoom = 1.0,
  onSelectLog,
}) => {
  const isUnassigned = camera.id.startsWith('unassigned_slot_');
  const storageKey = `SOC_CAMERA_HLS_SLOT_${slotIndex}`;

  const [streamUrl, setStreamUrl] = useState<string>(() => {
    try {
      return (
        localStorage.getItem(storageKey) ||
        localStorage.getItem(`SOC_CAMERA_HLS_${camera.id}`) ||
        ''
      );
    } catch {
      return '';
    }
  });

  const [isInputOpen, setIsInputOpen] = useState<boolean>(false);
  const [draftUrl, setDraftUrl] = useState<string>(streamUrl);
  const [renderMode, setRenderMode] = useState<'VIDEO' | 'IMAGE'>('VIDEO');

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const hlsInstanceRef = useRef<any>(null);

  const fpsVal = camera.measuredFps !== undefined ? camera.measuredFps : camera.fps;
  const latestLog = cameraLogs[0];
  const zoomScale = Math.max(1.0, Math.min(3.5, digitalZoom || camera.ptzState?.zoom || 1.0));

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
        localStorage.setItem(`SOC_CAMERA_HLS_${camera.id}`, trimmed);
      } else {
        localStorage.removeItem(storageKey);
        localStorage.removeItem(`SOC_CAMERA_HLS_${camera.id}`);
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
      localStorage.removeItem(`SOC_CAMERA_HLS_${camera.id}`);
    } catch {
      // Ignore
    }
    setIsInputOpen(false);
  };

  return (
    <div
      onClick={() => onToggleZoom && onToggleZoom(camera.id)}
      className={`relative bg-[#05070A] overflow-hidden select-none min-w-0 flex flex-col justify-between group cursor-pointer transition-all duration-200 ${
        isZoomed ? 'w-full h-full' : 'aspect-[16/10]'
      } border ${isZoomed ? 'border-[#3B82F6]' : 'border-[#1E2631] hover:border-[#3B82F6]'}`}
    >
      {/* 1. Lớp Render Video HLS (.m3u8) / Stream khi người dùng nhập link qua nút ẩn */}
      {streamUrl && (
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
              alt={camera.name}
              className="w-full h-full object-cover transition-transform duration-150"
              style={{ transform: `scale(${zoomScale})` }}
            />
          )}
        </div>
      )}

      {/* 2. Nút Ẩn (Hidden Button) cho phép nhập Link HLS / Stream ngay trên Camera */}
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          setDraftUrl(streamUrl);
          setIsInputOpen((prev) => !prev);
        }}
        title="Nhập link HLS (.m3u8) / Stream cho camera này"
        className="absolute bottom-1.5 right-1.5 z-30 w-6 h-6 bg-[#0B0F17]/80 border border-[#1E2631] text-slate-400 hover:text-[#10B981] hover:border-[#10B981] flex items-center justify-center opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity duration-150 cursor-pointer"
      >
        <Link2 className="w-3.5 h-3.5" />
      </button>

      {/* 3. Popover Nhập Link HLS / Stream (Khi bấm nút ẩn) */}
      {isInputOpen && (
        <form
          onSubmit={handleSaveStreamUrl}
          onClick={(e) => e.stopPropagation()}
          className="absolute inset-x-2 bottom-9 z-40 bg-[#0E131A]/95 border border-[#10B981] p-2.5 shadow-2xl space-y-2"
        >
          <div className="flex items-center justify-between text-[10px] font-mono text-[#10B981] font-bold uppercase">
            <span>NHẬP LINK HLS (.M3U8) / STREAM CAMERA</span>
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
              type="text"
              value={draftUrl}
              onChange={(e) => setDraftUrl(e.target.value)}
              placeholder="https://.../stream.m3u8 hoặc link stream..."
              autoFocus
              className="flex-1 bg-[#05070A] border border-[#1E2631] px-2 py-1 text-[11px] font-mono text-white placeholder-slate-600 focus:outline-none focus:border-[#10B981]"
            />
            <button
              type="submit"
              className="px-2.5 py-1 bg-[#10B981] text-[#05070A] font-mono text-[10px] font-bold hover:bg-[#10B981]/90 flex items-center gap-1 cursor-pointer shrink-0"
            >
              <Check className="w-3 h-3" />
              <span>LƯU</span>
            </button>
            {streamUrl && (
              <button
                type="button"
                onClick={handleClearStreamUrl}
                className="px-2 py-1 bg-[#7F1D1D] text-white font-mono text-[10px] font-bold hover:bg-[#DC2626] cursor-pointer shrink-0"
              >
                XÓA
              </button>
            )}
          </div>
        </form>
      )}

      {/* 4. Giao diện Telemetry & Log từ Server JSON */}
      <div className="relative z-10 flex-1 flex flex-col justify-between pointer-events-none">
        {/* Header Camera */}
        <div className="bg-[#0B0F17]/85 border-b border-[#1E2631]/80 px-2.5 py-1.5 flex items-center justify-between gap-2 shrink-0 pointer-events-auto">
          <div className="flex items-center gap-2 min-w-0">
            <Radio
              className={`w-3.5 h-3.5 shrink-0 ${
                !isUnassigned || streamUrl ? 'text-[#10B981] animate-pulse' : 'text-slate-600'
              }`}
            />
            <span className="font-mono text-xs font-bold text-white truncate">
              {isUnassigned ? `CAM_0${slotIndex + 1}` : camera.id}
            </span>
            {!isUnassigned && (
              <span className="font-mono text-[10px] text-slate-300 truncate">
                {camera.location || camera.name}
              </span>
            )}
          </div>

          <div className="flex items-center gap-1.5 shrink-0">
            {(!isUnassigned || streamUrl) && (
              <span className="bg-[#DC2626] text-white font-mono text-[9px] font-bold px-1.5 py-0.5 flex items-center gap-1">
                <span className="w-1.5 h-1.5 bg-white rounded-full animate-ping"></span>
                <span>LIVE</span>
              </span>
            )}
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onToggleZoom && onToggleZoom(camera.id);
              }}
              title={isZoomed ? 'Thu nhỏ về lưới 2x2' : 'Phóng to màn hình camera'}
              className="w-5 h-5 bg-[#121822] border border-[#1E2631] text-[#94A3B8] hover:text-white hover:border-[#3B82F6] flex items-center justify-center cursor-pointer transition-colors"
            >
              {isZoomed ? (
                <Minimize2 className="w-3 h-3 text-[#3B82F6]" />
              ) : (
                <Maximize2 className="w-3 h-3" />
              )}
            </button>
          </div>
        </div>

        {/* Nội dung chính khi chưa có Stream URL hoặc lớp phủ Log gọn nhẹ khi đang phát Stream */}
        {!streamUrl ? (
          isUnassigned && !latestLog ? (
            <div className="flex-1 flex flex-col items-center justify-center p-3 text-center">
              <Terminal className="w-6 h-6 text-slate-600 mb-1.5" />
              <div className="font-mono text-[11px] font-bold text-slate-500 uppercase">
                CHỜ DỮ LIỆU LOG TỪ SERVER
              </div>
              <div className="text-[10px] font-mono text-slate-600 mt-0.5">
                Đang lắng nghe JSON từ Server
              </div>
            </div>
          ) : (
            <div className="flex-1 p-2.5 font-mono text-[11px] overflow-y-auto space-y-2 pointer-events-auto">
              <div className="grid grid-cols-3 gap-1.5 bg-[#0B1018]/90 border border-[#1E2631] p-1.5 text-[10px]">
                <div className="flex items-center gap-1 text-slate-300 truncate">
                  <MapPin className="w-3 h-3 text-[#38BDF8] shrink-0" />
                  <span className="truncate">{camera.zoneId || 'ZONE_DEFAULT'}</span>
                </div>
                <div className="flex items-center gap-1 text-[#10B981] font-bold truncate">
                  <Users className="w-3 h-3 shrink-0" />
                  <span>Human: {camera.humanCount ?? latestLog?.humanCount ?? 0}</span>
                </div>
                <div className="text-right text-slate-400 truncate">
                  FPS: <span className="text-white font-bold">{fpsVal || latestLog?.measuredFps || 0}</span>
                </div>
              </div>

              {latestLog ? (
                <div
                  onClick={(e) => {
                    e.stopPropagation();
                    onSelectLog?.(latestLog);
                  }}
                  className={`p-2 border ${
                    latestLog.severity === 'CRITICAL'
                      ? 'bg-[#180A0A]/90 border-[#DC2626]'
                      : latestLog.severity === 'HIGH'
                      ? 'bg-[#181207]/90 border-[#F59E0B]'
                      : 'bg-[#0C131F]/90 border-[#1E2631]'
                  }`}
                >
                  <div className="flex items-center justify-between gap-1 mb-1">
                    <span className="font-bold text-white flex items-center gap-1 text-[11px]">
                      <ShieldAlert className="w-3.5 h-3.5 text-[#EF4444] shrink-0" />
                      {latestLog.primaryAction || latestLog.actionType || latestLog.title}
                    </span>
                    <span className="text-[10px] px-1.5 py-0.5 bg-[#7F1D1D] text-white font-bold">
                      {latestLog.severity} •{' '}
                      {latestLog.threatScore !== undefined
                        ? latestLog.threatScore <= 1
                          ? `${Math.round(latestLog.threatScore * 100)}%`
                          : `${Math.round(latestLog.threatScore)}%`
                        : 'N/A'}
                    </span>
                  </div>
                  <div className="text-[10px] text-slate-300 line-clamp-2 leading-relaxed">
                    {latestLog.description || latestLog.reasoning}
                  </div>
                </div>
              ) : (
                <div className="p-2.5 border border-[#1E2631] bg-[#090D14]/90 text-slate-400 text-[10px]">
                  Đã ghi nhận thiết bị <strong>{camera.id}</strong>. Đang chờ log sự kiện mới...
                </div>
              )}
            </div>
          )
        ) : (
          /* Khi đang phát HLS / Stream: chỉ hiển thị badge log nhỏ gọn ở góc dưới trái để không che video */
          <div className="p-2 flex items-end justify-between">
            {latestLog ? (
              <div
                onClick={(e) => {
                  e.stopPropagation();
                  onSelectLog?.(latestLog);
                }}
                className="bg-[#080B10]/85 border-l-2 border-[#EF4444] px-2 py-1 font-mono text-[10px] max-w-[80%] pointer-events-auto"
              >
                <div className="text-white font-bold truncate">
                  [{latestLog.primaryAction || latestLog.actionType}] {latestLog.severity}
                </div>
                <div className="text-slate-300 truncate">{latestLog.description || latestLog.title}</div>
              </div>
            ) : (
              <div />
            )}
          </div>
        )}

        {/* Footer */}
        <div className="bg-[#090D14]/85 border-t border-[#1E2631]/80 px-2.5 py-1 flex items-center justify-between font-mono text-[9px] text-slate-400 shrink-0">
          <span>
            {streamUrl ? 'HLS / STREAM ACTIVE' : `SYNC: ${camera.lastTimestamp || 'READY'}`}
          </span>
          <span className="pr-6">
            {zoomScale > 1.0 ? `ZOOM ${zoomScale.toFixed(1)}x` : `LOGS: ${cameraLogs.length}`}
          </span>
        </div>
      </div>
    </div>
  );
};
