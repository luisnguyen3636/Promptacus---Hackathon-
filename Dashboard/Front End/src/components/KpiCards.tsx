import React from 'react';
import { Zap, Globe, Radio, AlertTriangle } from 'lucide-react';
import { ISocMetrics } from '../types/soc.ts';

interface KpiCardsProps {
  metrics: ISocMetrics;
}

export const KpiCards: React.FC<KpiCardsProps> = ({ metrics }) => {
  return (
    <section className="grid grid-cols-4 gap-4">
      {/* KPI 1: Stream Latency (Cyan) */}
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
              {metrics.latencyMs}
            </span>
            <span className="font-mono text-xs text-slate-400 shrink-0">ms</span>
          </div>
          <div className="text-xs text-slate-400 font-medium mt-0.5 truncate" title="Stream Latency">
            Stream Latency
          </div>
        </div>
        <div className="text-[11px] font-mono text-[#06B6D4] truncate" title="Nominal">
          Nominal
        </div>
      </div>

      {/* KPI 2: Ingress Bandwidth (Blue) */}
      <div className="bg-[#0E131A] border border-[#1E2631] border-t-[3px] border-t-[#3B82F6] p-3.5 h-[108px] flex flex-col justify-between overflow-hidden min-w-0 select-none">
        <div className="flex items-start justify-between min-w-0">
          <div className="w-8 h-8 bg-[#121822] border border-[#1E2631] flex items-center justify-center text-[#3B82F6] shrink-0">
            <Globe className="w-4 h-4" />
          </div>
          <span className="text-[10px] font-mono text-[#3B82F6] uppercase whitespace-nowrap shrink-0">NETWORK</span>
        </div>
        <div className="min-w-0">
          <div className="flex items-baseline gap-1.5 min-w-0 overflow-hidden">
            <span className="font-mono text-xl xl:text-2xl font-bold text-white truncate">
              {Number(metrics.downloadMbps).toFixed(1)}
            </span>
            <span className="font-mono text-xs text-slate-400 shrink-0">Mbps</span>
          </div>
          <div className="text-xs text-slate-400 font-medium mt-0.5 truncate" title="Ingress Bandwidth">
            Ingress Bandwidth
          </div>
        </div>
        <div className="text-[11px] font-mono text-slate-400 truncate" title={`↑ ${Number(metrics.uploadMbps).toFixed(1)} Mbps egress`}>
          ↑ {Number(metrics.uploadMbps).toFixed(1)} Mbps egress
        </div>
      </div>

      {/* KPI 3: Cameras Online (Emerald) */}
      <div className="bg-[#0E131A] border border-[#1E2631] border-t-[3px] border-t-[#10B981] p-3.5 h-[108px] flex flex-col justify-between overflow-hidden min-w-0 select-none">
        <div className="flex items-start justify-between min-w-0">
          <div className="w-8 h-8 bg-[#121822] border border-[#1E2631] flex items-center justify-center text-[#10B981] shrink-0">
            <Radio className="w-4 h-4" />
          </div>
          <span className="text-[10px] font-mono text-[#10B981] uppercase whitespace-nowrap shrink-0">SURVEILLANCE</span>
        </div>
        <div className="min-w-0">
          <div className="flex items-baseline gap-1 min-w-0 overflow-hidden font-mono text-xl xl:text-2xl font-bold text-white">
            <span className="truncate">{metrics.camerasOnline}</span>
            <span className="text-slate-500 text-base font-semibold shrink-0">/{metrics.camerasTotal}</span>
          </div>
          <div className="text-xs text-slate-400 font-medium mt-0.5 truncate" title="Cameras Online">
            Cameras Online
          </div>
        </div>
        <div className="text-[11px] font-mono text-slate-400 truncate" title={`${metrics.camerasTotal - metrics.camerasOnline} Offline · PoE Active`}>
          {metrics.camerasTotal - metrics.camerasOnline} Offline · PoE Active
        </div>
      </div>

      {/* KPI 4: Open Threats (Amber) */}
      <div className="bg-[#0E131A] border border-[#1E2631] border-t-[3px] border-t-[#F59E0B] p-3.5 h-[108px] flex flex-col justify-between overflow-hidden min-w-0 select-none">
        <div className="flex items-start justify-between min-w-0">
          <div className="w-8 h-8 bg-[#121822] border border-[#1E2631] flex items-center justify-center text-[#F59E0B] shrink-0">
            <AlertTriangle className="w-4 h-4" />
          </div>
          <span className="text-[10px] font-mono text-[#F59E0B] uppercase whitespace-nowrap shrink-0">SOC ALERT</span>
        </div>
        <div className="min-w-0">
          <div className="font-mono text-xl xl:text-2xl font-bold text-white truncate">
            {metrics.openThreats}
          </div>
          <div className="text-xs text-slate-400 font-medium mt-0.5 truncate" title="Open Threats">
            Open Threats
          </div>
        </div>
        <div className="text-[11px] font-mono text-amber-500 truncate" title={`${metrics.criticalThreats} Critical · Physical & Network`}>
          {metrics.criticalThreats} Critical · Physical & Network
        </div>
      </div>
    </section>
  );
};
