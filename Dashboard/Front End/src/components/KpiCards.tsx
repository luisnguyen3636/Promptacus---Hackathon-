import React from 'react';
import { Zap, Camera, UserX, Radar } from 'lucide-react';
import { ISocMetrics } from '../types/soc.ts';

interface KpiCardsProps {
  metrics: ISocMetrics;
}

export const KpiCards: React.FC<KpiCardsProps> = ({ metrics }) => {
  return (
    <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* KPI 1: Stream Latency & Ping */}
      <div className="bg-[#0E131A] border border-[#1E2631] border-t-[3px] border-t-[#06B6D4] p-3.5 h-[108px] flex flex-col justify-between overflow-hidden min-w-0 select-none">
        <div className="flex items-start justify-between min-w-0">
          <div className="w-8 h-8 bg-[#121822] border border-[#1E2631] flex items-center justify-center text-[#06B6D4] shrink-0">
            <Zap className="w-4 h-4" />
          </div>
          <span className="text-[10px] font-mono text-[#06B6D4] uppercase whitespace-nowrap shrink-0">REALTIME</span>
        </div>
        <div className="min-w-0">
          <div className="flex items-baseline gap-1.5 min-w-0 overflow-hidden">
            <span className="font-mono text-xl xl:text-2xl font-bold text-white truncate">
              {metrics.latencyMs || 18}
            </span>
            <span className="font-mono text-xs text-slate-400 shrink-0">ms</span>
          </div>
          <div className="text-xs text-slate-400 font-medium mt-0.5 truncate" title="Độ trễ Stream & Ping">
            Độ trễ Stream & Ping
          </div>
        </div>
        <div className="text-[11px] font-mono text-[#06B6D4] truncate" title="Tối ưu (Zero Lag)">
          Tối ưu &bull; Jitter &lt; 2ms
        </div>
      </div>

      {/* KPI 2: Camera AI Fleet */}
      <div className="bg-[#0E131A] border border-[#1E2631] border-t-[3px] border-t-[#10B981] p-3.5 h-[108px] flex flex-col justify-between overflow-hidden min-w-0 select-none">
        <div className="flex items-start justify-between min-w-0">
          <div className="w-8 h-8 bg-[#121822] border border-[#1E2631] flex items-center justify-center text-[#10B981] shrink-0">
            <Camera className="w-4 h-4" />
          </div>
          <span className="text-[10px] font-mono text-[#10B981] uppercase whitespace-nowrap shrink-0">SURVEILLANCE</span>
        </div>
        <div className="min-w-0">
          <div className="flex items-baseline gap-1 min-w-0 overflow-hidden font-mono text-xl xl:text-2xl font-bold text-white">
            <span className="truncate">{metrics.camerasOnline || 4}</span>
            <span className="text-slate-500 text-base font-semibold shrink-0">/{metrics.camerasTotal || 4}</span>
          </div>
          <div className="text-xs text-slate-400 font-medium mt-0.5 truncate" title="Camera AI Giám Sát">
            Camera AI Giám Sát
          </div>
        </div>
        <div className="text-[11px] font-mono text-slate-400 truncate" title="MMAction2 + VLM Bắt buộc">
          MMAction2 + VLM Bắt buộc
        </div>
      </div>

      {/* KPI 3: Wanted Criminals Registry */}
      <div className="bg-[#0E131A] border border-[#1E2631] border-t-[3px] border-t-[#DC2626] p-3.5 h-[108px] flex flex-col justify-between overflow-hidden min-w-0 select-none">
        <div className="flex items-start justify-between min-w-0">
          <div className="w-8 h-8 bg-[#121822] border border-[#1E2631] flex items-center justify-center text-[#EF4444] shrink-0">
            <UserX className="w-4 h-4" />
          </div>
          <span className="text-[10px] font-mono text-[#EF4444] uppercase whitespace-nowrap shrink-0">WANTED</span>
        </div>
        <div className="min-w-0">
          <div className="flex items-baseline gap-1.5 min-w-0 overflow-hidden font-mono text-xl xl:text-2xl font-bold text-white">
            <span className="truncate">{metrics.wantedCount ?? 3}</span>
            <span className="text-xs font-mono text-slate-400 shrink-0">đối tượng</span>
          </div>
          <div className="text-xs text-slate-400 font-medium mt-0.5 truncate" title="Danh Sách Truy Nã">
            Danh Sách Truy Nã
          </div>
        </div>
        <div className="text-[11px] font-mono text-red-400 truncate" title="Đã Đóng Dấu Bằng Chứng SHA-256">
          Đã Đóng Dấu Bằng Chứng
        </div>
      </div>

      {/* KPI 4: Blind-Spot Tracking Sessions */}
      <div className="bg-[#0E131A] border border-[#1E2631] border-t-[3px] border-t-[#F59E0B] p-3.5 h-[108px] flex flex-col justify-between overflow-hidden min-w-0 select-none">
        <div className="flex items-start justify-between min-w-0">
          <div className="w-8 h-8 bg-[#121822] border border-[#1E2631] flex items-center justify-center text-[#F59E0B] shrink-0">
            <Radar className="w-4 h-4" />
          </div>
          <span className="text-[10px] font-mono text-[#F59E0B] uppercase whitespace-nowrap shrink-0">BLIND-SPOT</span>
        </div>
        <div className="min-w-0">
          <div className="flex items-baseline gap-1.5 min-w-0 overflow-hidden font-mono text-xl xl:text-2xl font-bold text-white">
            <span className="truncate">{metrics.blindSpotSessionsCount ?? 2}</span>
            <span className="text-xs font-mono text-slate-400 shrink-0">luồng</span>
          </div>
          <div className="text-xs text-slate-400 font-medium mt-0.5 truncate" title="Suy Luận Vùng Mù Đa Cam">
            Suy Luận Vùng Mù Đa Cam
          </div>
        </div>
        <div className="text-[11px] font-mono text-amber-400 truncate" title="Truy vết liên camera (>=2)">
          Truy vết liên camera (&ge;2)
        </div>
      </div>
    </section>
  );
};
