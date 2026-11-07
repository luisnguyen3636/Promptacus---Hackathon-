import React from 'react';
import { Settings, Maximize2, MoreVertical } from 'lucide-react';
import { ICameraDevice } from '../../types/soc.ts';
import { CameraSlot } from './CameraSlot.tsx';
import { PtzToolbar } from './PtzToolbar.tsx';

interface CameraMatrixProps {
  cameras: ICameraDevice[];
  onPtzCommand?: (cameraId: string, action: string) => void;
}

export const CameraMatrix: React.FC<CameraMatrixProps> = ({
  cameras,
  onPtzCommand,
}) => {
  const displayCameras: ICameraDevice[] = [...cameras];
  while (displayCameras.length < 4) {
    const idx = displayCameras.length + 1;
    displayCameras.push({
      id: `standby_0${idx}`,
      name: `Slot ${idx} (Chờ luồng AI)`,
      ip: `192.168.1.${100 + idx}`,
      fps: 0,
      bitrateKbps: 0,
      status: 'DEGRADED',
      streamUrl: '',
      ptzEnabled: false,
      boundingBoxes: []
    });
  }

  const handlePtzLeft = (action: 'ZOOM_IN' | 'ZOOM_OUT' | 'PAN' | 'AUTO_FOCUS') => {
    if (onPtzCommand && displayCameras[0]) {
      onPtzCommand(displayCameras[0].id, action);
    }
  };

  const handlePtzRight = (action: 'ZOOM_IN' | 'ZOOM_OUT' | 'PAN' | 'AUTO_FOCUS') => {
    if (onPtzCommand && displayCameras[1]) {
      onPtzCommand(displayCameras[1].id, action);
    }
  };

  return (
    <div className="bg-[#0E131A] border border-[#1E2631] flex flex-col h-full">
      {/* Header Khối Matrix */}
      <div className="bg-[#121822] border-b border-[#1E2631] px-3.5 py-2 flex items-center justify-between select-none">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 bg-[#DC2626]"></span>
          <span className="font-bold text-xs uppercase tracking-wider text-[#E2E8F0]">
            LIVE CAMERA MATRIX (2x2)
          </span>
        </div>

        {/* Cụm 4 nút công cụ vuông 24x24px */}
        <div className="flex items-center gap-1">
          <button
            title="Cài đặt luồng"
            className="w-6 h-6 bg-[#0E131A] border border-[#1E2631] text-[#94A3B8] hover:text-white hover:border-[#2D3748] flex items-center justify-center cursor-pointer"
          >
            <Settings className="w-3 h-3" />
          </button>
          <button
            title="Chế độ 1x1"
            className="w-6 h-6 bg-[#0E131A] border border-[#1E2631] text-[#94A3B8] hover:text-white hover:border-[#2D3748] font-mono text-[10px] font-bold flex items-center justify-center cursor-pointer"
          >
            1x1
          </button>
          <button
            title="Toàn màn hình"
            className="w-6 h-6 bg-[#0E131A] border border-[#1E2631] text-[#94A3B8] hover:text-white hover:border-[#2D3748] flex items-center justify-center cursor-pointer"
          >
            <Maximize2 className="w-3 h-3" />
          </button>
          <button
            title="Tùy chọn khác"
            className="w-6 h-6 bg-[#0E131A] border border-[#1E2631] text-[#94A3B8] hover:text-white hover:border-[#2D3748] flex items-center justify-center cursor-pointer"
          >
            <MoreVertical className="w-3 h-3" />
          </button>
        </div>
      </div>

      {/* Thân Khối: Cột PTZ Trái + Lưới 4 Ô Video + Cột PTZ Phải */}
      <div className="p-3 flex gap-2 flex-1">
        {/* Cột PTZ Trái (Cam 1 & 3) */}
        <PtzToolbar onCommand={handlePtzLeft} />

        {/* Lưới 4 Ô Video (2x2) */}
        <div className="grid grid-cols-2 grid-rows-2 gap-[2px] bg-[#1E2631] flex-1">
          {displayCameras.slice(0, 4).map((cam) => (
            <CameraSlot key={cam.id} camera={cam} />
          ))}
        </div>

        {/* Cột PTZ Phải (Cam 2 & 4) */}
        <PtzToolbar onCommand={handlePtzRight} />
      </div>
    </div>
  );
};
