import React, { useState } from 'react';
import { CameraSlot } from '../CameraMatrix/CameraSlot.tsx';
import { ICameraDevice } from '../../types/soc.ts';
import { Camera, Eye, Sliders, Volume2, ShieldCheck, Download } from 'lucide-react';

interface LiveVideoWallViewProps {
  cameras: ICameraDevice[];
  onPtzCommand: (cameraId: string, action: string) => void;
  onToast?: (msg: string) => void;
}

export const LiveVideoWallView: React.FC<LiveVideoWallViewProps> = ({
  cameras,
  onPtzCommand,
  onToast,
}) => {
  const [layoutMode, setLayoutMode] = useState<'3x2' | '2x2' | '1x1'>('3x2');
  const [filterMode, setFilterMode] = useState<'IR' | 'RGB'>('IR');

  const wallCameras: ICameraDevice[] = [
    ...cameras,
    {
      id: "cam_05",
      name: "Lobby Reception Area",
      ip: "172.16.2.14",
      fps: 30,
      bitrateKbps: 42,
      status: "ONLINE",
      streamUrl: "",
      ptzEnabled: true,
      boundingBoxes: [
        {
          id: "box_05",
          label: "PERSON 95%",
          subLabel: "VISITOR",
          severity: "NORMAL",
          x: 0.4,
          y: 0.3,
          w: 0.2,
          h: 0.55
        }
      ]
    },
    {
      id: "cam_06",
      name: "Underground Parking Bay",
      ip: "172.16.3.28",
      fps: 30,
      bitrateKbps: 38,
      status: "ONLINE",
      streamUrl: "",
      ptzEnabled: true,
      boundingBoxes: [
        {
          id: "box_06",
          label: "VEHICLE 97%",
          subLabel: "ENTRY",
          severity: "NORMAL",
          x: 0.25,
          y: 0.35,
          w: 0.4,
          h: 0.45
        }
      ]
    }
  ];

  const handleCaptureAll = () => {
    onToast?.('[SNAPSHOT CAPTURED] Đã lưu 6 khung hình bằng chứng đồng loạt vào Rolling Buffer');
  };

  const handleApplyPreset = (camId: string, presetName: string) => {
    onToast?.(`[PTZ PRESET] ${camId} -> Chuyển sang vị trí mẫu: ${presetName}`);
  };

  let gridColsClass = 'grid-cols-3';
  if (layoutMode === '2x2') gridColsClass = 'grid-cols-2';
  if (layoutMode === '1x1') gridColsClass = 'grid-cols-1 max-w-4xl mx-auto';

  return (
    <div className="space-y-4 select-none min-w-0">
      {/* Thanh Điều khiển Video Wall Chuyên sâu */}
      <div className="bg-[#0E131A] border border-[#1E2631] px-4 py-2.5 flex items-center justify-between min-w-0 overflow-hidden">
        <div className="flex items-center gap-3 min-w-0 truncate">
          <Camera className="w-4 h-4 text-[#10B981] shrink-0" />
          <span className="font-bold text-xs uppercase tracking-wider text-white truncate">
            ENTERPRISE LIVE VIDEO WALL MATRIX (6 ACTIVE STREAMS)
          </span>
          <span className="bg-[#112224] border border-[#10B981] text-[#10B981] font-mono text-[10px] font-bold px-2 py-0.5 shrink-0">
            6/6 ENCRYPTED H.264
          </span>
        </div>

        {/* Cụm công cụ Layout & Bộ lọc Quang học */}
        <div className="flex items-center gap-2 shrink-0">
          {/* Bộ lọc IR / RGB */}
          <div className="flex items-center gap-1 border border-[#1E2631] bg-[#161E29] p-0.5">
            <button
              onClick={() => setFilterMode('IR')}
              className={`px-2 py-0.5 font-mono text-[10px] font-bold cursor-pointer transition-colors ${
                filterMode === 'IR' ? 'bg-[#10B981] text-[#080B10]' : 'text-slate-400 hover:text-white'
              }`}
            >
              IR MONO
            </button>
            <button
              onClick={() => setFilterMode('RGB')}
              className={`px-2 py-0.5 font-mono text-[10px] font-bold cursor-pointer transition-colors ${
                filterMode === 'RGB' ? 'bg-[#10B981] text-[#080B10]' : 'text-slate-400 hover:text-white'
              }`}
            >
              RGB FULL
            </button>
          </div>

          {/* Bộ chọn Layout */}
          <div className="flex items-center gap-1">
            <button
              onClick={() => setLayoutMode('3x2')}
              className={`px-2.5 py-1 font-mono text-xs font-bold border transition-colors cursor-pointer ${
                layoutMode === '3x2'
                  ? 'bg-[#112224] text-[#10B981] border-[#10B981]'
                  : 'bg-[#161E29] text-slate-400 border-[#1E2631] hover:text-white'
              }`}
            >
              3x2
            </button>
            <button
              onClick={() => setLayoutMode('2x2')}
              className={`px-2.5 py-1 font-mono text-xs font-bold border transition-colors cursor-pointer ${
                layoutMode === '2x2'
                  ? 'bg-[#112224] text-[#10B981] border-[#10B981]'
                  : 'bg-[#161E29] text-slate-400 border-[#1E2631] hover:text-white'
              }`}
            >
              2x2
            </button>
            <button
              onClick={() => setLayoutMode('1x1')}
              className={`px-2.5 py-1 font-mono text-xs font-bold border transition-colors cursor-pointer ${
                layoutMode === '1x1'
                  ? 'bg-[#112224] text-[#10B981] border-[#10B981]'
                  : 'bg-[#161E29] text-slate-400 border-[#1E2631] hover:text-white'
              }`}
            >
              FOCUS 1x1
            </button>
          </div>

          {/* Nút chụp toàn bộ */}
          <button
            onClick={handleCaptureAll}
            className="px-2.5 py-1 bg-[#161E29] border border-[#2D3748] hover:border-[#10B981] hover:text-[#10B981] text-white font-mono text-xs font-bold inline-flex items-center gap-1.5 cursor-pointer"
          >
            <Download className="w-3.5 h-3.5" />
            <span>SNAPSHOT ALL</span>
          </button>
        </div>
      </div>

      {/* Lưới Camera Toàn cảnh */}
      <div className={`grid ${gridColsClass} gap-3 bg-[#080B10]`}>
        {wallCameras.slice(0, layoutMode === '2x2' ? 4 : layoutMode === '1x1' ? 1 : 6).map((cam, idx) => (
          <div
            key={cam.id}
            className={`bg-[#0E131A] border border-[#1E2631] p-2 flex flex-col space-y-2 ${
              filterMode === 'IR' ? '' : 'hue-rotate-15'
            }`}
          >
            {/* Header thanh thông tin camera */}
            <div className="flex items-center justify-between px-1">
              <span className="font-mono text-xs font-bold text-white truncate" title={cam.name}>
                {cam.name}
              </span>
              <div className="flex items-center gap-2">
                <span className="font-mono text-[10px] text-slate-400">FPS: {cam.fps}</span>
                <span className="font-mono text-[10px] text-[#06B6D4]">{cam.bitrateKbps} kbps</span>
              </div>
            </div>

            {/* Video Slot có Canvas AI */}
            <div className="relative">
              <CameraSlot camera={cam} />
            </div>

            {/* Thanh PTZ Presets & Audio Level Meter */}
            <div className="flex items-center justify-between pt-1 border-t border-[#1E2631]/60 text-xs font-mono">
              {/* Audio meter mô phỏng */}
              <div className="flex items-center gap-1.5 text-slate-400">
                <Volume2 className="w-3.5 h-3.5 text-[#10B981]" />
                <div className="w-12 h-1.5 bg-[#1E2631] flex">
                  <div
                    className="h-full bg-[#10B981]"
                    style={{ width: `${Math.min(100, 30 + idx * 12)}%` }}
                  />
                </div>
                <span className="text-[9px] text-slate-500">{32 + idx * 8}dB</span>
              </div>

              {/* PTZ Quick Presets */}
              <div className="flex items-center gap-1">
                <span className="text-[10px] text-slate-500 mr-1">PRESET:</span>
                <button
                  onClick={() => handleApplyPreset(cam.id, 'P1 - Door')}
                  className="px-1.5 py-0.5 bg-[#161E29] border border-[#1E2631] hover:border-[#3B82F6] text-[10px] font-bold text-slate-300"
                >
                  P1
                </button>
                <button
                  onClick={() => handleApplyPreset(cam.id, 'P2 - Hall')}
                  className="px-1.5 py-0.5 bg-[#161E29] border border-[#1E2631] hover:border-[#3B82F6] text-[10px] font-bold text-slate-300"
                >
                  P2
                </button>
                <button
                  onClick={() => handleApplyPreset(cam.id, 'P3 - Rack')}
                  className="px-1.5 py-0.5 bg-[#161E29] border border-[#1E2631] hover:border-[#3B82F6] text-[10px] font-bold text-slate-300"
                >
                  P3
                </button>

                {/* PTZ Zoom Buttons */}
                <button
                  onClick={() => onPtzCommand(cam.id, 'ZOOM_IN')}
                  className="px-1.5 py-0.5 bg-[#161E29] border border-[#1E2631] hover:border-[#10B981] text-[10px] font-bold text-[#10B981]"
                >
                  +
                </button>
                <button
                  onClick={() => onPtzCommand(cam.id, 'ZOOM_OUT')}
                  className="px-1.5 py-0.5 bg-[#161E29] border border-[#1E2631] hover:border-[#10B981] text-[10px] font-bold text-[#10B981]"
                >
                  -
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
