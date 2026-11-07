import React, { useState, useEffect } from 'react';
import { Settings, Maximize2, Minimize2, Grid, ZoomIn, ZoomOut } from 'lucide-react';
import { ICameraDevice } from '../../types/soc.ts';
import { CameraSlot } from './CameraSlot.tsx';
import { PtzToolbar } from './PtzToolbar.tsx';

interface CameraMatrixProps {
  cameras: ICameraDevice[];
  onPtzCommand?: (cameraId: string, action: string) => void;
  zoomedCameraId?: string | null;
  onToggleZoom?: (cameraId: string | null) => void;
}

export const CameraMatrix: React.FC<CameraMatrixProps> = ({
  cameras,
  onPtzCommand,
  zoomedCameraId = null,
  onToggleZoom,
}) => {
  const [digitalZoomMap, setDigitalZoomMap] = useState<Record<string, number>>({});

  // Chuẩn bị danh sách 4 camera (ưu tiên camera thực tế và camera LAPTOP_01)
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

  // Camera đang được focus/zoom (mặc định là camera đầu tiên nếu có zoomedCameraId)
  const activeCamera = displayCameras.find((c) => c.id === zoomedCameraId) || displayCameras[0];

  // Hỗ trợ phím ESC để thoát chế độ phóng to về 2x2
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && zoomedCameraId) {
        onToggleZoom?.(null);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [zoomedCameraId, onToggleZoom]);

  const handleToggleSlotZoom = (camId: string) => {
    if (zoomedCameraId === camId) {
      onToggleZoom?.(null);
    } else {
      onToggleZoom?.(camId);
    }
  };

  const handlePtzZoom = (camId: string, direction: 'IN' | 'OUT') => {
    setDigitalZoomMap((prev) => {
      const current = prev[camId] || 1.0;
      const next = direction === 'IN' ? Math.min(3.5, current + 0.25) : Math.max(1.0, current - 0.25);
      return { ...prev, [camId]: parseFloat(next.toFixed(2)) };
    });

    if (onPtzCommand) {
      onPtzCommand(camId, direction === 'IN' ? 'ZOOM_IN' : 'ZOOM_OUT');
    }
  };

  const handlePtzLeft = (action: 'ZOOM_IN' | 'ZOOM_OUT' | 'PAN' | 'AUTO_FOCUS') => {
    const targetId = zoomedCameraId || displayCameras[0]?.id;
    if (action === 'ZOOM_IN') handlePtzZoom(targetId, 'IN');
    else if (action === 'ZOOM_OUT') handlePtzZoom(targetId, 'OUT');
    else if (onPtzCommand && targetId) onPtzCommand(targetId, action);
  };

  const handlePtzRight = (action: 'ZOOM_IN' | 'ZOOM_OUT' | 'PAN' | 'AUTO_FOCUS') => {
    const targetId = zoomedCameraId || displayCameras[1]?.id;
    if (action === 'ZOOM_IN') handlePtzZoom(targetId, 'IN');
    else if (action === 'ZOOM_OUT') handlePtzZoom(targetId, 'OUT');
    else if (onPtzCommand && targetId) onPtzCommand(targetId, action);
  };

  return (
    <div className="bg-[#0E131A] border border-[#1E2631] flex flex-col h-full select-none">
      {/* Header Khối Matrix */}
      <div className="bg-[#121822] border-b border-[#1E2631] px-3.5 py-2 flex items-center justify-between select-none">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 bg-[#DC2626]"></span>
          <span className="font-bold text-xs uppercase tracking-wider text-[#E2E8F0]">
            {zoomedCameraId ? `CAMERA FOCUS: ${activeCamera.name}` : 'LIVE CAMERA MATRIX (2x2)'}
          </span>
          {zoomedCameraId && (
            <span className="bg-[#1E293B] border border-[#3B82F6] text-[#3B82F6] font-mono text-[9px] font-bold px-1.5 py-0.2">
              CHẾ ĐỘ QUAN SÁT CẬN CẢNH (80% VIEWPORT)
            </span>
          )}
        </div>

        {/* Cụm nút công cụ điều khiển View & Zoom */}
        <div className="flex items-center gap-1.5">
          {/* Nút 1x1 Focus Mode */}
          <button
            onClick={() => handleToggleSlotZoom(displayCameras[0]?.id)}
            title="Chế độ 1x1 (Phóng to quan sát camera chính)"
            className={`px-2 h-6 border font-mono text-[10px] font-bold flex items-center gap-1 cursor-pointer transition-colors ${
              zoomedCameraId
                ? 'bg-[#1E293B] border-[#3B82F6] text-[#3B82F6]'
                : 'bg-[#0E131A] border-[#1E2631] text-[#94A3B8] hover:text-white hover:border-[#2D3748]'
            }`}
          >
            <ZoomIn className="w-3 h-3" />
            <span>1x1 FOCUS</span>
          </button>

          {/* Nút Lưới 2x2 Matrix Mode */}
          <button
            onClick={() => onToggleZoom?.(null)}
            title="Chế độ Lưới 2x2 Matrix"
            className={`px-2 h-6 border font-mono text-[10px] font-bold flex items-center gap-1 cursor-pointer transition-colors ${
              !zoomedCameraId
                ? 'bg-[#1E293B] border-[#10B981] text-[#10B981]'
                : 'bg-[#0E131A] border-[#1E2631] text-[#94A3B8] hover:text-white hover:border-[#2D3748]'
            }`}
          >
            <Grid className="w-3 h-3" />
            <span>2x2 GRID</span>
          </button>

          {/* Phóng to / Thu nhỏ Toggle */}
          <button
            onClick={() => onToggleZoom?.(zoomedCameraId ? null : displayCameras[0]?.id)}
            title={zoomedCameraId ? 'Thu nhỏ về 2x2 (ESC)' : 'Phóng to quan sát camera'}
            className="w-6 h-6 bg-[#0E131A] border border-[#1E2631] text-[#94A3B8] hover:text-white hover:border-[#2D3748] flex items-center justify-center cursor-pointer"
          >
            {zoomedCameraId ? <Minimize2 className="w-3 h-3 text-[#3B82F6]" /> : <Maximize2 className="w-3 h-3" />}
          </button>
        </div>
      </div>

      {/* Thân Khối: Cột PTZ Trái + Vùng Video Cameras + Cột PTZ Phải */}
      <div className="p-3 flex gap-2 flex-1 min-h-[380px]">
        {/* Cột PTZ Trái */}
        <PtzToolbar onCommand={handlePtzLeft} />

        {/* VÙNG HIỂN THỊ CAMERA */}
        {zoomedCameraId ? (
          /* KHI PHÓNG TO ĐỂ QUAN SÁT:
             Camera chính chiếm khung nhìn lớn, 3 camera còn lại chia đều bên dưới / cạnh bên */
          <div className="flex-1 flex flex-col gap-2 min-w-0">
            {/* Khung Camera Quan sát Chính */}
            <div className="flex-1 min-h-[320px] relative">
              <CameraSlot
                camera={activeCamera}
                isZoomed={true}
                onToggleZoom={handleToggleSlotZoom}
                digitalZoom={digitalZoomMap[activeCamera.id] || 1.0}
              />
            </div>

            {/* Dải 3 camera còn lại chia đều bên dưới */}
            <div className="grid grid-cols-3 gap-2 h-[110px] shrink-0">
              {displayCameras
                .filter((cam) => cam.id !== activeCamera.id)
                .slice(0, 3)
                .map((cam) => (
                  <div key={cam.id} className="relative h-full">
                    <CameraSlot
                      camera={cam}
                      isZoomed={false}
                      onToggleZoom={handleToggleSlotZoom}
                      digitalZoom={digitalZoomMap[cam.id] || 1.0}
                    />
                  </div>
                ))}
            </div>
          </div>
        ) : (
          /* KHI Ở CHẾ ĐỘ 2x2 TIÊU CHUẨN: Lưới 4 Ô Video chia đều cân bằng */
          <div className="grid grid-cols-2 grid-rows-2 gap-[2px] bg-[#1E2631] flex-1">
            {displayCameras.slice(0, 4).map((cam) => (
              <CameraSlot
                key={cam.id}
                camera={cam}
                isZoomed={false}
                onToggleZoom={handleToggleSlotZoom}
                digitalZoom={digitalZoomMap[cam.id] || 1.0}
              />
            ))}
          </div>
        )}

        {/* Cột PTZ Phải */}
        <PtzToolbar onCommand={handlePtzRight} />
      </div>
    </div>
  );
};
