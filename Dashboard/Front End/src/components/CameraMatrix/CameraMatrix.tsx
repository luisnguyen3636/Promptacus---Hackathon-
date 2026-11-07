import React, { useState, useEffect } from 'react';
import { Maximize2, Minimize2, Grid, ZoomIn } from 'lucide-react';
import { ICameraDevice, IIncidentItem } from '../../types/soc.ts';
import { CameraSlot } from './CameraSlot.tsx';
import { PtzToolbar } from './PtzToolbar.tsx';

interface CameraMatrixProps {
  cameras: ICameraDevice[];
  incidents?: IIncidentItem[];
  onPtzCommand?: (cameraId: string, action: string) => void;
  zoomedCameraId?: string | null;
  onToggleZoom?: (cameraId: string | null) => void;
  onSelectPlayback?: (incident: IIncidentItem) => void;
}

export const CameraMatrix: React.FC<CameraMatrixProps> = ({
  cameras,
  incidents = [],
  onPtzCommand,
  zoomedCameraId = null,
  onToggleZoom,
  onSelectPlayback,
}) => {
  const [digitalZoomMap, setDigitalZoomMap] = useState<Record<string, number>>({});

  // Tạo ma trận 4 ô từ danh sách camera thật của Server (ô trống không chứa dữ liệu giả)
  const displayCameras: ICameraDevice[] = [...cameras];
  while (displayCameras.length < 4) {
    const idx = displayCameras.length + 1;
    displayCameras.push({
      id: `unassigned_slot_${idx}`,
      name: `Camera Slot #${idx}`,
      ip: 'N/A',
      fps: 0,
      bitrateKbps: 0,
      status: 'OFFLINE',
      streamUrl: '',
      ptzEnabled: false,
      boundingBoxes: [],
    });
  }

  const activeCamera = displayCameras.find((c) => c.id === zoomedCameraId) || displayCameras[0];

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
    if (!camId) return;
    setDigitalZoomMap((prev) => {
      const current = prev[camId] || 1.0;
      const next =
        direction === 'IN' ? Math.min(3.5, current + 0.25) : Math.max(1.0, current - 0.25);
      return { ...prev, [camId]: parseFloat(next.toFixed(2)) };
    });

    if (onPtzCommand && !camId.startsWith('unassigned_slot_')) {
      onPtzCommand(camId, direction === 'IN' ? 'ZOOM_IN' : 'ZOOM_OUT');
    }
  };

  const handlePtzLeft = (action: 'ZOOM_IN' | 'ZOOM_OUT' | 'PAN' | 'AUTO_FOCUS') => {
    const targetId = zoomedCameraId || displayCameras[0]?.id;
    if (!targetId) return;
    if (action === 'ZOOM_IN') handlePtzZoom(targetId, 'IN');
    else if (action === 'ZOOM_OUT') handlePtzZoom(targetId, 'OUT');
    else if (onPtzCommand && !targetId.startsWith('unassigned_slot_')) onPtzCommand(targetId, action);
  };

  const handlePtzRight = (action: 'ZOOM_IN' | 'ZOOM_OUT' | 'PAN' | 'AUTO_FOCUS') => {
    const targetId = zoomedCameraId || displayCameras[1]?.id || displayCameras[0]?.id;
    if (!targetId) return;
    if (action === 'ZOOM_IN') handlePtzZoom(targetId, 'IN');
    else if (action === 'ZOOM_OUT') handlePtzZoom(targetId, 'OUT');
    else if (onPtzCommand && !targetId.startsWith('unassigned_slot_')) onPtzCommand(targetId, action);
  };

  const getLogsForCamera = (camId: string, slotIndex: number): IIncidentItem[] => {
    if (camId.startsWith('unassigned_slot_')) {
      return slotIndex === 0 && cameras.length === 0 ? incidents : [];
    }
    return incidents.filter((inc) => inc.cameraId === camId);
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
          <button
            onClick={() => displayCameras[0] && handleToggleSlotZoom(displayCameras[0].id)}
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

          <button
            onClick={() =>
              onToggleZoom?.(zoomedCameraId ? null : displayCameras[0]?.id || null)
            }
            title={zoomedCameraId ? 'Thu nhỏ về 2x2 (ESC)' : 'Phóng to quan sát camera'}
            className="w-6 h-6 bg-[#0E131A] border border-[#1E2631] text-[#94A3B8] hover:text-white hover:border-[#2D3748] flex items-center justify-center cursor-pointer"
          >
            {zoomedCameraId ? (
              <Minimize2 className="w-3 h-3 text-[#3B82F6]" />
            ) : (
              <Maximize2 className="w-3 h-3" />
            )}
          </button>
        </div>
      </div>

      {/* Thân Khối: Cột PTZ Trái + Vùng Video Cameras + Cột PTZ Phải */}
      <div className="p-3 flex gap-2 flex-1 min-h-[380px]">
        <PtzToolbar onCommand={handlePtzLeft} />

        {zoomedCameraId ? (
          <div className="flex-1 flex flex-col gap-2 min-w-0">
            <div className="flex-1 min-h-[320px] relative">
              <CameraSlot
                camera={activeCamera}
                slotIndex={displayCameras.findIndex((c) => c.id === activeCamera.id)}
                cameraLogs={getLogsForCamera(
                  activeCamera.id,
                  displayCameras.findIndex((c) => c.id === activeCamera.id)
                )}
                isZoomed={true}
                onToggleZoom={handleToggleSlotZoom}
                digitalZoom={digitalZoomMap[activeCamera.id] || 1.0}
                onSelectLog={onSelectPlayback}
              />
            </div>

            <div className="grid grid-cols-3 gap-2 h-[110px] shrink-0">
              {displayCameras
                .filter((cam) => cam.id !== activeCamera.id)
                .slice(0, 3)
                .map((cam, idx) => (
                  <div key={cam.id} className="relative h-full">
                    <CameraSlot
                      camera={cam}
                      slotIndex={idx + 1}
                      cameraLogs={getLogsForCamera(cam.id, idx + 1)}
                      isZoomed={false}
                      onToggleZoom={handleToggleSlotZoom}
                      digitalZoom={digitalZoomMap[cam.id] || 1.0}
                      onSelectLog={onSelectPlayback}
                    />
                  </div>
                ))}
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-2 grid-rows-2 gap-[2px] bg-[#1E2631] flex-1">
            {displayCameras.slice(0, 4).map((cam, idx) => (
              <CameraSlot
                key={cam.id}
                camera={cam}
                slotIndex={idx}
                cameraLogs={getLogsForCamera(cam.id, idx)}
                isZoomed={false}
                onToggleZoom={handleToggleSlotZoom}
                digitalZoom={digitalZoomMap[cam.id] || 1.0}
                onSelectLog={onSelectPlayback}
              />
            ))}
          </div>
        )}

        <PtzToolbar onCommand={handlePtzRight} />
      </div>
    </div>
  );
};
