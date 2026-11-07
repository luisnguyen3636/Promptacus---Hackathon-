import React from 'react';
import { Zap, Cpu, Activity, Sliders, AlertOctagon } from 'lucide-react';
import { ICameraDevice } from '../../types/soc.ts';

interface AiMetricsGridProps {
  cameras?: ICameraDevice[];
}

export const AiMetricsGrid: React.FC<AiMetricsGridProps> = ({ cameras = [] }) => {
  const activeTracksCount = cameras.reduce((acc, c) => acc + (c.boundingBoxes?.length || 0), 0);

  return (
    <div className="space-y-4 select-none min-w-0">
      {/* Hàng 1: 4 Thẻ Hiệu năng AI / Hardware Inference */}
      <div className="grid grid-cols-4 gap-4">
        {/* Card 1: Inference Time */}
        <div className="bg-[#0E131A] border border-[#1E2631] border-t-[3px] border-t-[#06B6D4] p-3.5 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono text-[#06B6D4] uppercase tracking-wider font-bold">
              INFERENCE TIME
            </span>
            <Zap className="w-4 h-4 text-[#06B6D4]" />
          </div>
          <div className="font-mono text-2xl font-bold text-white mt-1">14.2 ms</div>
          <div className="text-[11px] font-mono text-slate-400 mt-0.5">YOLOv8x TensorRT INT8</div>
        </div>

        {/* Card 2: GPU Cluster Load */}
        <div className="bg-[#0E131A] border border-[#1E2631] border-t-[3px] border-t-[#3B82F6] p-3.5 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono text-[#3B82F6] uppercase tracking-wider font-bold">
              GPU CLUSTER LOAD
            </span>
            <Cpu className="w-4 h-4 text-[#3B82F6]" />
          </div>
          <div className="font-mono text-2xl font-bold text-white mt-1">64%</div>
          <div className="text-[11px] font-mono text-slate-400 mt-0.5">NVIDIA RTX A6000 48GB</div>
        </div>

        {/* Card 3: Accuracy */}
        <div className="bg-[#0E131A] border border-[#1E2631] border-t-[3px] border-t-[#10B981] p-3.5 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono text-[#10B981] uppercase tracking-wider font-bold">
              ACCURACY (mAP@50)
            </span>
            <Activity className="w-4 h-4 text-[#10B981]" />
          </div>
          <div className="font-mono text-2xl font-bold text-white mt-1">96.8%</div>
          <div className="text-[11px] font-mono text-slate-400 mt-0.5">Zero State Flapping</div>
        </div>

        {/* Card 4: Active Threads */}
        <div className="bg-[#0E131A] border border-[#1E2631] border-t-[3px] border-t-[#F59E0B] p-3.5 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono text-[#F59E0B] uppercase tracking-wider font-bold">
              ACTIVE THREADS
            </span>
            <Sliders className="w-4 h-4 text-[#F59E0B]" />
          </div>
          <div className="font-mono text-2xl font-bold text-white mt-1">{activeTracksCount} Tracks</div>
          <div className="text-[11px] font-mono text-slate-400 mt-0.5">Real-time AI Vision Tracks</div>
        </div>
      </div>

      {/* Hàng 2: 4 Thẻ Phân bố Lớp Đối tượng (Class Distribution Matrix) */}
      <div className="grid grid-cols-4 gap-4">
        {/* Class Person */}
        <div className="bg-[#0E131A] border border-[#1E2631] p-3 flex items-center justify-between">
          <div>
            <div className="text-[10px] font-mono text-[#64748B] uppercase tracking-wider">CLASS: PERSON</div>
            <div className="font-mono text-xl font-bold text-white mt-0.5">2,410</div>
            <div className="text-[10px] font-mono text-[#10B981] mt-0.5">72.4% Detection Share</div>
          </div>
          <div className="w-8 h-8 bg-[#10B981]/10 border border-[#10B981]/40 flex items-center justify-center font-mono text-xs text-[#10B981] font-bold">
            P
          </div>
        </div>

        {/* Class Vehicle */}
        <div className="bg-[#0E131A] border border-[#1E2631] p-3 flex items-center justify-between">
          <div>
            <div className="text-[10px] font-mono text-[#64748B] uppercase tracking-wider">CLASS: VEHICLE</div>
            <div className="font-mono text-xl font-bold text-white mt-0.5">890</div>
            <div className="text-[10px] font-mono text-[#3B82F6] mt-0.5">24.1% Detection Share</div>
          </div>
          <div className="w-8 h-8 bg-[#3B82F6]/10 border border-[#3B82F6]/40 flex items-center justify-center font-mono text-xs text-[#3B82F6] font-bold">
            V
          </div>
        </div>

        {/* Class Loitering */}
        <div className="bg-[#0E131A] border border-[#1E2631] p-3 flex items-center justify-between">
          <div>
            <div className="text-[10px] font-mono text-[#64748B] uppercase tracking-wider">CLASS: LOITERING</div>
            <div className="font-mono text-xl font-bold text-white mt-0.5">42</div>
            <div className="text-[10px] font-mono text-[#F59E0B] mt-0.5">3.2% Anomaly Share</div>
          </div>
          <div className="w-8 h-8 bg-[#F59E0B]/10 border border-[#F59E0B]/40 flex items-center justify-center font-mono text-xs text-[#F59E0B] font-bold">
            L
          </div>
        </div>

        {/* Class Intrusion / Breach */}
        <div className="bg-[#0E131A] border border-[#1E2631] p-3 flex items-center justify-between">
          <div>
            <div className="text-[10px] font-mono text-[#EF4444] uppercase tracking-wider">
              CLASS: INTRUSION / BREACH
            </div>
            <div className="font-mono text-xl font-bold text-white mt-0.5">8</div>
            <div className="text-[10px] font-mono text-[#EF4444] mt-0.5 font-semibold">0.3% Critical Trigger</div>
          </div>
          <div className="w-8 h-8 bg-[#EF4444]/15 border border-[#EF4444] flex items-center justify-center font-mono text-xs text-[#EF4444] font-bold">
            !
          </div>
        </div>
      </div>
    </div>
  );
};
