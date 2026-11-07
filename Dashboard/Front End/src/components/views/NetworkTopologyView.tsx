import React from 'react';
import { Network, Server, Router, Camera, Cpu, HardDrive, ShieldCheck, Activity } from 'lucide-react';
import { ISocMetrics } from '../../types/soc.ts';

interface NetworkTopologyViewProps {
  metrics: ISocMetrics;
}

export const NetworkTopologyView: React.FC<NetworkTopologyViewProps> = ({ metrics }) => {
  const nodes = [
    {
      id: 'core-gw',
      name: 'SOC Core Gateway',
      ip: '10.0.0.1',
      icon: Router,
      status: 'ONLINE',
      stats: '10 Gbps SFP+ Fiber Uplink',
      rtt: '0.4ms',
      color: '#10B981',
    },
    {
      id: 'poe-sw',
      name: 'PoE Aggregation Switch',
      ip: '10.0.1.2',
      icon: Server,
      status: 'ONLINE',
      stats: `48 Ports Managed · Load: ${metrics.poeLoadWatts}W`,
      rtt: '0.8ms',
      color: '#10B981',
    },
    {
      id: 'edge-cams',
      name: 'Edge Cameras Subnet',
      ip: '192.168.16.0/24',
      icon: Camera,
      status: 'ONLINE',
      stats: `${metrics.camerasOnline} Online · 3 Offline`,
      rtt: '2.1ms',
      color: '#06B6D4',
    },
    {
      id: 'ai-vlm',
      name: 'AI VLM Inference Cluster',
      ip: '10.0.2.10',
      icon: Cpu,
      status: 'ONLINE',
      stats: 'TensorRT / YOLOv8 · Latency 14ms',
      rtt: '1.2ms',
      color: '#3B82F6',
    },
    {
      id: 'nvr-storage',
      name: 'SAN/NVR Storage Array',
      ip: '10.0.3.5',
      icon: HardDrive,
      status: 'ONLINE',
      stats: `Capacity: ${metrics.nvrStoragePercent}% · RAID-6 Array`,
      rtt: '1.5ms',
      color: '#F59E0B',
    },
    {
      id: 'dispatch-gw',
      name: 'HITL Dispatch Gateway',
      ip: '10.0.4.1',
      icon: ShieldCheck,
      status: 'ONLINE',
      stats: 'Encrypted Forensic Dispatch Gate',
      rtt: '3.4ms',
      color: '#10B981',
    },
  ];

  const switchPorts = [
    { port: 'Port 01', device: 'Server Room Cam 01', speed: '1000 Mbps', loss: '0.00%', poe: '12.4W', vlan: 'VLAN-10', crc: 0, state: 'UP' },
    { port: 'Port 02', device: 'Main Gate Cam 02', speed: '1000 Mbps', loss: '0.00%', poe: '14.2W', vlan: 'VLAN-10', crc: 0, state: 'UP' },
    { port: 'Port 03', device: 'Server Room Cam 03', speed: '1000 Mbps', loss: '0.00%', poe: '11.8W', vlan: 'VLAN-10', crc: 0, state: 'UP' },
    { port: 'Port 04', device: 'Main Gate Cam 04', speed: '1000 Mbps', loss: '0.00%', poe: '13.5W', vlan: 'VLAN-10', crc: 0, state: 'UP' },
    { port: 'Port 05', device: 'AI Inference Cluster A', speed: '10 Gbps', loss: '0.00%', poe: 'N/A', vlan: 'VLAN-20', crc: 0, state: 'UP' },
    { port: 'Port 06', device: 'SAN NVR Primary Storage', speed: '10 Gbps', loss: '0.00%', poe: 'N/A', vlan: 'VLAN-30', crc: 0, state: 'UP' },
  ];

  return (
    <div className="space-y-4 select-none min-w-0">
      {/* Header Khối */}
      <div className="bg-[#0E131A] border border-[#1E2631] px-4 py-2.5 flex items-center justify-between min-w-0 overflow-hidden">
        <div className="flex items-center gap-2 min-w-0 truncate">
          <Network className="w-4 h-4 text-[#10B981] shrink-0" />
          <span className="font-bold text-xs uppercase tracking-wider text-white truncate">
            PHYSICAL & LOGICAL NETWORK TOPOLOGY WITH PACKET FLOW
          </span>
        </div>
        <div className="font-mono text-xs text-slate-400 shrink-0">
          Uplink: <span className="text-[#10B981] font-bold">9744.0 Mbps</span> &bull; Loss:{' '}
          <span className="text-[#10B981] font-bold">0.00%</span> &bull; PoE Total:{' '}
          <span className="text-white font-bold">{metrics.poeLoadWatts}W</span>
        </div>
      </div>

      {/* Sơ đồ Hình học SVG Mô phỏng Luồng Dữ liệu Hạt xung */}
      <div className="bg-[#0E131A] border border-[#1E2631] p-4 relative overflow-hidden">
        <div className="text-[10px] font-mono text-[#64748B] uppercase mb-2">
          INTERACTIVE PACKET FLOW MATRIX (REAL-TIME BACKBONE LINK)
        </div>

        <svg className="w-full h-24 stroke-[#1E2631]" viewBox="0 0 900 100" fill="none">
          {/* Đường nối giữa các nodes */}
          <path d="M 80 50 L 230 50 L 380 50 L 530 50 L 680 50 L 830 50" stroke="#1E2631" strokeWidth="3" />
          <path
            d="M 80 50 L 230 50 L 380 50 L 530 50 L 680 50 L 830 50"
            stroke="#10B981"
            strokeWidth="2"
            strokeDasharray="8 14"
            className="animate-pulse"
          />

          {/* Node points */}
          <circle cx="80" cy="50" r="14" fill="#080B10" stroke="#10B981" strokeWidth="2" />
          <circle cx="230" cy="50" r="14" fill="#080B10" stroke="#10B981" strokeWidth="2" />
          <circle cx="380" cy="50" r="14" fill="#080B10" stroke="#06B6D4" strokeWidth="2" />
          <circle cx="530" cy="50" r="14" fill="#080B10" stroke="#3B82F6" strokeWidth="2" />
          <circle cx="680" cy="50" r="14" fill="#080B10" stroke="#F59E0B" strokeWidth="2" />
          <circle cx="830" cy="50" r="14" fill="#080B10" stroke="#10B981" strokeWidth="2" />

          {/* Labels */}
          <text x="80" y="80" fill="#94A3B8" fontSize="9" fontFamily="monospace" textAnchor="middle">CORE-GW</text>
          <text x="230" y="80" fill="#94A3B8" fontSize="9" fontFamily="monospace" textAnchor="middle">PoE-SWITCH</text>
          <text x="380" y="80" fill="#94A3B8" fontSize="9" fontFamily="monospace" textAnchor="middle">CAM-SUBNET</text>
          <text x="530" y="80" fill="#94A3B8" fontSize="9" fontFamily="monospace" textAnchor="middle">AI-CLUSTER</text>
          <text x="680" y="80" fill="#94A3B8" fontSize="9" fontFamily="monospace" textAnchor="middle">SAN-NVR</text>
          <text x="830" y="80" fill="#94A3B8" fontSize="9" fontFamily="monospace" textAnchor="middle">DISPATCH-GW</text>
        </svg>
      </div>

      {/* Sơ đồ 6 Nodes Mạng Tác chiến */}
      <div className="grid grid-cols-3 gap-4">
        {nodes.map((node) => {
          const Icon = node.icon;
          return (
            <div
              key={node.id}
              className="bg-[#0E131A] border border-[#1E2631] p-4 flex flex-col justify-between hover:border-[#10B981] transition-colors min-w-0"
            >
              <div className="flex items-start justify-between min-w-0">
                <div
                  className="w-9 h-9 border flex items-center justify-center bg-[#121822] shrink-0"
                  style={{ borderColor: node.color, color: node.color }}
                >
                  <Icon className="w-5 h-5" />
                </div>
                <div className="flex items-center gap-1.5 shrink-0">
                  <span className="font-mono text-[9px] text-slate-500">RTT: {node.rtt}</span>
                  <span className="font-mono text-[10px] font-bold px-1.5 py-0.5 bg-[#112224] border border-[#10B981] text-[#10B981]">
                    {node.status}
                  </span>
                </div>
              </div>
              <div className="mt-3 min-w-0">
                <div className="font-bold text-xs text-white truncate" title={node.name}>
                  {node.name}
                </div>
                <div className="font-mono text-[11px] text-slate-400 mt-0.5 truncate">
                  IP: <span className="text-slate-200">{node.ip}</span>
                </div>
                <div className="font-mono text-[10px] text-slate-500 mt-1 truncate" title={node.stats}>
                  {node.stats}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Bảng Chi tiết 6 Cổng Switch */}
      <div className="bg-[#0E131A] border border-[#1E2631] overflow-hidden">
        <div className="bg-[#121822] border-b border-[#1E2631] px-4 py-2 flex items-center justify-between text-xs font-bold uppercase text-[#E2E8F0]">
          <span>PoE SWITCH PORT TELEMETRY & LINK METRICS</span>
          <span className="text-[10px] font-mono text-[#10B981]">MTU: 9000 JUMBO · ZERO CRC ERROR</span>
        </div>
        <div className="overflow-x-auto min-w-0">
          <table className="w-full text-left font-mono text-xs min-w-[700px]">
            <thead className="bg-[#121822] text-[#64748B] border-b border-[#1E2631]">
              <tr>
                <th className="p-2.5">PORT</th>
                <th className="p-2.5">CONNECTED DEVICE</th>
                <th className="p-2.5">VLAN</th>
                <th className="p-2.5">SPEED</th>
                <th className="p-2.5">PACKET LOSS</th>
                <th className="p-2.5">PoE LOAD</th>
                <th className="p-2.5 text-center">STATUS</th>
              </tr>
            </thead>
            <tbody>
              {switchPorts.map((sp) => (
                <tr key={sp.port} className="border-b border-[#1E2631] hover:bg-[#161E29]/50">
                  <td className="p-2.5 text-[#10B981] font-bold">{sp.port}</td>
                  <td className="p-2.5 text-slate-200">{sp.device}</td>
                  <td className="p-2.5 text-[#06B6D4]">{sp.vlan}</td>
                  <td className="p-2.5 text-slate-400">{sp.speed}</td>
                  <td className="p-2.5 text-slate-400">{sp.loss}</td>
                  <td className="p-2.5 text-slate-400">{sp.poe}</td>
                  <td className="p-2.5 text-center">
                    <span className="px-1.5 py-0.5 bg-[#112224] border border-[#10B981] text-[#10B981] text-[10px] font-bold">
                      {sp.state}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
