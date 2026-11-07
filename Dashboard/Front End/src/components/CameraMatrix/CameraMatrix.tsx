import React, { useState, useEffect } from 'react';
import { Maximize2, Minimize2, Grid, ZoomIn } from 'lucide-react';
import { ICameraDevice } from '../../types/soc.ts';
import { CameraSlot } from './CameraSlot.tsx';
import { PtzToolbar } from './PtzToolbar.tsx';

interface CameraMatrixProps {
  cameras?: ICameraDevice[];
  onPtzCommand?: (cameraId: string, action: string) => void;
  zoomedCameraId?: string | null;
  onToggleZoom?: (cameraId: string | null) => void;
}

const FIXED_SLOTS = [
  { index: 0, slotKey: 'slot_0', defaultLabel: 'CAM_01' },
  { index: 1, slotKey: 'slot_1', defaultLabel: 'CAM_02' },
  { index: 2, slotKey: 'slot_2', defaultLabel: 'CAM_03' },
  { index: 3, slotKey: 'slot_3', defaultLabel: 'CAM_04' },
];

const CameraMatrixInner: React.FC<CameraMatrixProps> = ({
  cameras = [],
  onPtzCommand,
  zoomedCameraId = null,
  onToggleZoom,
}) => {
  const [digitalZoomMap, setDigitalZoomMap] = useState<Record<number, number>>({});

  const activeSlotIndex =
    zoomedCameraId !== null
      ? FIXED_SLOTS.find((s) => s.slotKey === zoomedCameraId || s.defaultLabel === zoomedCameraId)
          ?.index ?? 0
      : null;

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && zoomedCameraId) {
        onToggleZoom?.(null);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [zoomedCameraId, onToggleZoom]);

  const handleToggleSlotZoom = (slotIdx: number) => {
    const targetKey = `slot_${slotIdx}`;
    if (zoomedCameraId === targetKey) {
      onToggleZoom?.(null);
    } else {
      onToggleZoom?.(targetKey);
    }
  };

  const handlePtzZoom = (slotIdx: number, direction: 'IN' | 'OUT') => {
    setDigitalZoomMap((prev) => {
      const current = prev[slotIdx] || 1.0;
      const next =
        direction === 'IN' ? Math.min(3.5, current + 0.25) : Math.max(1.0, current - 0.25);
      return { ...prev, [slotIdx]: parseFloat(next.toFixed(2)) };
    });

    const camId = cameras[slotIdx]?.id || `CAM_0${slotIdx + 1}`;
    if (onPtzCommand) {
      onPtzCommand(camId, direction === 'IN' ? 'ZOOM_IN' : 'ZOOM_OUT');
    }
  };

  const handlePtzLeft = (action: 'ZOOM_IN' | 'ZOOM_OUT' | 'PAN' | 'AUTO_FOCUS') => {
    const targetIdx = activeSlotIndex ?? 0;
    if (action === 'ZOOM_IN') handlePtzZoom(targetIdx, 'IN');
    else if (action === 'ZOOM_OUT') handlePtzZoom(targetIdx, 'OUT');
    else if (onPtzCommand) onPtzCommand(cameras[targetIdx]?.id || `CAM_0${targetIdx + 1}`, action);
  };

  const handlePtzRight = (action: 'ZOOM_IN' | 'ZOOM_OUT' | 'PAN' | 'AUTO_FOCUS') => {
    const targetIdx = activeSlotIndex ?? 1;
    if (action === 'ZOOM_IN') handlePtzZoom(targetIdx, 'IN');
    else if (action === 'ZOOM_OUT') handlePtzZoom(targetIdx, 'OUT');
    else if (onPtzCommand) onPtzCommand(cameras[targetIdx]?.id || `CAM_0${targetIdx + 1}`, action);
  };

  const getSlotLabel = (slotIdx: number): string => {
    const cam = cameras[slotIdx];
    if (cam && cam.id && !cam.id.startsWith('unassigned_slot_')) {
      return `${cam.id}${cam.location ? ` · ${cam.location}` : ''}`;
    }
    return `CAM_0${slotIdx + 1}`;
  };

  return (
    <div className="bg-[#0E131A] border border-[#1E2631] flex flex-col h-full select-none">
      {/* Header Khối Matrix */}
      <div className="bg-[#121822] border-b border-[#1E2631] px-3.5 py-2 flex items-center justify-between select-none">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 bg-[#DC2626]"></span>
          <span className="font-bold text-xs uppercase tracking-wider text-[#E2E8F0]">
            {activeSlotIndex !== null
              ? `CAMERA FOCUS: ${getSlotLabel(activeSlotIndex)}`
              : 'LIVE CAMERA MATRIX (2x2)'}
          </span>
          {activeSlotIndex !== null && (
            <span className="bg-[#1E293B] border border-[#3B82F6] text-[#3B82F6] font-mono text-[9px] font-bold px-1.5 py-0.2">
              CHẾ ĐỘ QUAN SÁT CẬN CẢNH (80% VIEWPORT)
            </span>
          )}
        </div>

        {/* Cụm nút công cụ điều khiển View & Zoom */}
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => handleToggleSlotZoom(activeSlotIndex ?? 0)}
            title="Chế độ 1x1 (Phóng to quan sát camera chính)"
            className={`px-2 h-6 border font-mono text-[10px] font-bold flex items-center gap-1 cursor-pointer transition-colors ${
              activeSlotIndex !== null
                ? 'bg-[#1E293B] border-[#3B82F6] text-[#3B82F6]'
                : 'bg-[#0E131A] border-[#1E2631] text-[#94A3B8] hover:text-white hover:border-[#2D3748]'
            }`}
          >
            <ZoomIn className="w-3 h-3" />
            <span>1x1 FOCUS</span>
          </button>

          <button
            type="button"
            onClick={() => onToggleZoom?.(null)}
            title="Chế độ Lưới 2x2 Matrix"
            className={`px-2 h-6 border font-mono text-[10px] font-bold flex items-center gap-1 cursor-pointer transition-colors ${
              activeSlotIndex === null
                ? 'bg-[#1E293B] border-[#10B981] text-[#10B981]'
                : 'bg-[#0E131A] border-[#1E2631] text-[#94A3B8] hover:text-white hover:border-[#2D3748]'
            }`}
          >
            <Grid className="w-3 h-3" />
            <span>2x2 GRID</span>
          </button>

          <button
            type="button"
            onClick={() =>
              onToggleZoom?.(activeSlotIndex !== null ? null : 'slot_0')
            }
            title={activeSlotIndex !== null ? 'Thu nhỏ về 2x2 (ESC)' : 'Phóng to quan sát camera'}
            className="w-6 h-6 bg-[#0E131A] border border-[#1E2631] text-[#94A3B8] hover:text-white hover:border-[#2D3748] flex items-center justify-center cursor-pointer"
          >
            {activeSlotIndex !== null ? (
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

        {activeSlotIndex !== null ? (
          <div className="flex-1 flex flex-col gap-2 min-w-0">
            <div className="flex-1 min-h-[320px] relative">
              <CameraSlot
                key={`camera_slot_${activeSlotIndex}`}
                slotIndex={activeSlotIndex}
                cameraLabel={getSlotLabel(activeSlotIndex)}
                isZoomed={true}
                onToggleZoom={handleToggleSlotZoom}
                digitalZoom={digitalZoomMap[activeSlotIndex] || 1.0}
              />
            </div>

            <div className="grid grid-cols-3 gap-2 h-[110px] shrink-0">
              {FIXED_SLOTS.filter((s) => s.index !== activeSlotIndex).map((slot) => (
                <div key={`camera_slot_thumb_${slot.index}`} className="relative h-full">
                  <CameraSlot
                    slotIndex={slot.index}
                    cameraLabel={getSlotLabel(slot.index)}
                    isZoomed={false}
                    onToggleZoom={handleToggleSlotZoom}
                    digitalZoom={digitalZoomMap[slot.index] || 1.0}
                  />
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-2 grid-rows-2 gap-[2px] bg-[#1E2631] flex-1">
            {FIXED_SLOTS.map((slot) => (
              <CameraSlot
                key={`camera_slot_${slot.index}`}
                slotIndex={slot.index}
                cameraLabel={getSlotLabel(slot.index)}
                isZoomed={false}
                onToggleZoom={handleToggleSlotZoom}
                digitalZoom={digitalZoomMap[slot.index] || 1.0}
              />
            ))}
          </div>
        )}

        <PtzToolbar onCommand={handlePtzRight} />
      </div>
    </div>
  );
};

export const CameraMatrix = React.memo(
  CameraMatrixInner,
  (prev, next) =>
    prev.zoomedCameraId === next.zoomedCameraId &&
    prev.cameras?.length === next.cameras?.length &&
    prev.cameras?.[0]?.id === next.cameras?.[0]?.id
);
