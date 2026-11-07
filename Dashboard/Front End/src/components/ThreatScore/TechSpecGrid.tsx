import React from 'react';
import { ISocMetrics } from '../../types/soc.ts';

interface TechSpecGridProps {
  metrics: ISocMetrics;
}

export const TechSpecGrid: React.FC<TechSpecGridProps> = ({ metrics }) => {
  return (
    <div className="grid grid-cols-2 grid-rows-2 bg-[#1E2631] gap-[1px] border-t border-[#1E2631] select-none min-w-0 overflow-hidden">
      {/* Ô 1: Packet Loss */}
      <div className="bg-[#0E131A] p-2.5 sm:p-3 min-w-0 overflow-hidden">
        <div className="text-[10px] xl:text-[11px] text-[#64748B] font-medium truncate" title="Packet Loss">
          Packet Loss
        </div>
        <div className="font-mono text-sm xl:text-base font-bold text-[#10B981] mt-0.5 truncate">
          {Number(metrics.packetLossPercent).toFixed(2)}%
        </div>
      </div>

      {/* Ô 2: Active Cameras */}
      <div className="bg-[#0E131A] p-2.5 sm:p-3 min-w-0 overflow-hidden">
        <div className="text-[10px] xl:text-[11px] text-[#64748B] font-medium truncate" title="Active Cameras">
          Active Cameras
        </div>
        <div className="font-mono text-sm xl:text-base font-bold text-white mt-0.5 truncate">
          {metrics.camerasOnline}/{metrics.camerasTotal}
        </div>
      </div>

      {/* Ô 3: NVR Storage */}
      <div className="bg-[#0E131A] p-2.5 sm:p-3 min-w-0 overflow-hidden">
        <div className="text-[10px] xl:text-[11px] text-[#64748B] font-medium truncate" title="NVR Storage">
          NVR Storage
        </div>
        <div className="font-mono text-sm xl:text-base font-bold text-[#F59E0B] mt-0.5 truncate">
          {metrics.nvrStoragePercent}%
        </div>
      </div>

      {/* Ô 4: PoE Load */}
      <div className="bg-[#0E131A] p-2.5 sm:p-3 min-w-0 overflow-hidden">
        <div className="text-[10px] xl:text-[11px] text-[#64748B] font-medium truncate" title="PoE Load">
          PoE Load
        </div>
        <div className="font-mono text-sm xl:text-base font-bold text-white mt-0.5 truncate">
          {metrics.poeLoadWatts}W
        </div>
      </div>
    </div>
  );
};
