import React, { useState } from 'react';
import { Cpu, Zap, Activity, Sliders, Terminal } from 'lucide-react';
import { ICameraDevice } from '../../types/soc.ts';

interface AiAnalyzerViewProps {
  cameras: ICameraDevice[];
}

export const AiAnalyzerView: React.FC<AiAnalyzerViewProps> = ({ cameras }) => {
  const [personThreshold, setPersonThreshold] = useState<number>(85);
  const [vehicleThreshold, setVehicleThreshold] = useState<number>(80);
  const [loiterThreshold, setLoiterThreshold] = useState<number>(75);

  const activeTracksCount = cameras.reduce((acc, c) => acc + (c.boundingBoxes?.length || 0), 0);

  const dynamicLogs = cameras.flatMap((cam) =>
    (cam.boundingBoxes || []).map((b) => ({
      time: new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
      model: 'YOLO11-Pose / Biomechanical Rules',
      text: `${cam.name} (${cam.id}): ${b.label} - ${b.subLabel || 'TRACKED'} [Mức độ: ${b.severity}]`
    }))
  );

  const logs = dynamicLogs.length > 0 ? dynamicLogs : [
    { time: '--:--:--', model: 'AI-SOC Ingestion Gateway', text: 'Chờ luồng nhận diện từ AI Detector (Ready to ingest webhook)...' }
  ];

  return (
    <div className="space-y-4 select-none min-w-0">
      {/* 4 Thẻ Hiệu năng AI / VLM */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-[#0E131A] border border-[#1E2631] border-t-[3px] border-t-[#06B6D4] p-3.5">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono text-[#06B6D4]">INFERENCE TIME</span>
            <Zap className="w-4 h-4 text-[#06B6D4]" />
          </div>
          <div className="font-mono text-2xl font-bold text-white mt-1">14.2 ms</div>
          <div className="text-[11px] font-mono text-slate-400 mt-0.5">YOLOv8x TensorRT INT8</div>
        </div>

        <div className="bg-[#0E131A] border border-[#1E2631] border-t-[3px] border-t-[#3B82F6] p-3.5">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono text-[#3B82F6]">GPU CLUSTER LOAD</span>
            <Cpu className="w-4 h-4 text-[#3B82F6]" />
          </div>
          <div className="font-mono text-2xl font-bold text-white mt-1">64%</div>
          <div className="text-[11px] font-mono text-slate-400 mt-0.5">NVIDIA RTX A6000 48GB</div>
        </div>

        <div className="bg-[#0E131A] border border-[#1E2631] border-t-[3px] border-t-[#10B981] p-3.5">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono text-[#10B981]">ACCURACY (mAP@50)</span>
            <Activity className="w-4 h-4 text-[#10B981]" />
          </div>
          <div className="font-mono text-2xl font-bold text-white mt-1">96.8%</div>
          <div className="text-[11px] font-mono text-slate-400 mt-0.5">Zero State Flapping</div>
        </div>

        <div className="bg-[#0E131A] border border-[#1E2631] border-t-[3px] border-t-[#F59E0B] p-3.5">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono text-[#F59E0B]">ACTIVE THREADS</span>
            <Sliders className="w-4 h-4 text-[#F59E0B]" />
          </div>
          <div className="font-mono text-2xl font-bold text-white mt-1">{activeTracksCount} Tracks</div>
          <div className="text-[11px] font-mono text-slate-400 mt-0.5">Real-time AI Vision Tracks</div>
        </div>
      </div>

      {/* 2 Cột: Bảng chỉnh Ngưỡng & Console Log */}
      <div className="grid grid-cols-12 gap-4">
        {/* Cột Trái: Bộ chỉnh Ngưỡng Tin cậy (5 Cột) */}
        <div className="col-span-5 bg-[#0E131A] border border-[#1E2631] p-4 flex flex-col justify-between">
          <div>
            <div className="font-bold text-xs uppercase text-white flex items-center gap-2 mb-3">
              <Sliders className="w-4 h-4 text-[#10B981]" />
              <span>AI CONFIDENCE THRESHOLD TUNER</span>
            </div>

            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-xs font-mono mb-1">
                  <span className="text-slate-300">Person Intrusion Threshold:</span>
                  <span className="text-[#10B981] font-bold">{personThreshold}%</span>
                </div>
                <input
                  type="range"
                  min="50"
                  max="99"
                  value={personThreshold}
                  onChange={(e) => setPersonThreshold(Number(e.target.value))}
                  className="w-full accent-[#10B981] cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs font-mono mb-1">
                  <span className="text-slate-300">Vehicle Tracking Threshold:</span>
                  <span className="text-[#3B82F6] font-bold">{vehicleThreshold}%</span>
                </div>
                <input
                  type="range"
                  min="50"
                  max="99"
                  value={vehicleThreshold}
                  onChange={(e) => setVehicleThreshold(Number(e.target.value))}
                  className="w-full accent-[#3B82F6] cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs font-mono mb-1">
                  <span className="text-slate-300">Loitering Alert Sensitivity:</span>
                  <span className="text-[#F59E0B] font-bold">{loiterThreshold}%</span>
                </div>
                <input
                  type="range"
                  min="50"
                  max="99"
                  value={loiterThreshold}
                  onChange={(e) => setLoiterThreshold(Number(e.target.value))}
                  className="w-full accent-[#F59E0B] cursor-pointer"
                />
              </div>
            </div>
          </div>

          <div className="p-2.5 bg-[#121822] border border-[#1E2631] font-mono text-[10px] text-slate-400 mt-4">
            Changes apply in real time to the inference worker engine.
          </div>
        </div>

        {/* Cột Phải: Console Log VLM Stream (7 Cột) */}
        <div className="col-span-7 bg-[#0E131A] border border-[#1E2631] p-4 flex flex-col">
          <div className="flex items-center justify-between mb-3">
            <div className="font-bold text-xs uppercase text-white flex items-center gap-2">
              <Terminal className="w-4 h-4 text-[#3B82F6]" />
              <span>LIVE VLM REASONING STREAM CONSOLE</span>
            </div>
            <span className="font-mono text-[10px] text-[#10B981]">● STREAMING</span>
          </div>

          <div className="bg-[#05070A] border border-[#1E2631] p-3 font-mono text-xs space-y-2 flex-1 overflow-y-auto max-h-[260px]">
            {logs.map((log, i) => (
              <div key={i} className="text-slate-300 leading-relaxed border-b border-[#1E2631]/40 pb-1.5">
                <span className="text-slate-500">[{log.time}]</span>{' '}
                <span className="text-[#3B82F6] font-semibold">{log.model}:</span>{' '}
                <span className="text-slate-200">{log.text}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
