import React, { useState } from 'react';
import { AlertTriangle, ShieldAlert, Database, Ban, ShieldCheck, Crosshair, Search } from 'lucide-react';

interface ThreatIntelligenceViewProps {
  onBlockIp?: (ip: string) => void;
}

export const ThreatIntelligenceView: React.FC<ThreatIntelligenceViewProps> = ({ onBlockIp }) => {
  const [blockedIps, setBlockedIps] = useState<string[]>([]);
  const [searchFilter, setSearchFilter] = useState<string>('');

  const threatsList = [
    { ip: '45.33.32.256', region: 'External (AS15169)', type: 'Automated Port Scan (SYN Flood)', score: 78, mitre: 'T1595.001 Recon', lastSeen: '16:07 UTC' },
    { ip: '185.220.161.45', region: 'Tor Exit Relay / Proxy', type: 'Physical Perimeter Intruder Tag', score: 92, mitre: 'T1078 Initial Access', lastSeen: '16:12 UTC' },
    { ip: '194.26.29.112', region: 'Unknown Origin (Bulletproof Hosting)', type: 'SSH Brute Force Attempt', score: 84, mitre: 'T1110 Credential Access', lastSeen: '15:45 UTC' },
    { ip: '103.145.12.8', region: 'APNIC / Commercial IP Pool', type: 'API Rate Limit Abuse / Crawl', score: 65, mitre: 'T1059 Command Exec', lastSeen: '14:20 UTC' },
    { ip: '91.240.118.172', region: 'RIPE NCC / Suspicious Host', type: 'Camera RTSP Credential Probing', score: 88, mitre: 'T1592 Reconnaissance', lastSeen: '13:10 UTC' },
  ];

  const mitreTactics = [
    { phase: 'RECONNAISSANCE', code: 'TA0043', count: '14 Alarms', desc: 'Port Scan, RTSP probe, CCTV coverage probe', color: '#06B6D4' },
    { phase: 'INITIAL ACCESS', code: 'TA0001', count: '8 Alarms', desc: 'Physical perimeter breach, Door lock manipulation', color: '#F59E0B' },
    { phase: 'DEFENSE EVASION', code: 'TA0005', count: '12 Alarms', desc: 'Face concealment, Blind-spot loitering', color: '#EF4444' },
    { phase: 'EXFILTRATION', code: 'TA0010', count: '2 Alarms', desc: 'High-speed flight, Evidence dumping', color: '#DC2626' },
  ];

  const handleBlock = (ip: string) => {
    setBlockedIps(prev => [...prev, ip]);
    if (onBlockIp) onBlockIp(ip);
  };

  const filteredThreats = threatsList.filter(
    t => t.ip.includes(searchFilter) || t.type.toLowerCase().includes(searchFilter.toLowerCase())
  );

  return (
    <div className="space-y-4 select-none min-w-0">
      {/* 4 Thẻ Đo lường Tình báo Cốt lõi */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-[#0E131A] border border-[#1E2631] border-t-[3px] border-t-[#06B6D4] p-3.5">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono text-[#06B6D4]">ACTIVE IoC SIGNATURES</span>
            <AlertTriangle className="w-4 h-4 text-[#06B6D4]" />
          </div>
          <div className="font-mono text-2xl font-bold text-white mt-1">1,420</div>
          <div className="text-[11px] font-mono text-slate-400 mt-0.5">Threat DB v2024.12 Sync</div>
        </div>

        <div className="bg-[#0E131A] border border-[#1E2631] border-t-[3px] border-t-[#F59E0B] p-3.5">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono text-[#F59E0B]">PRE-CRIME PATTERNS</span>
            <Crosshair className="w-4 h-4 text-[#F59E0B]" />
          </div>
          <div className="font-mono text-2xl font-bold text-white mt-1">86 Patterns</div>
          <div className="text-[11px] font-mono text-slate-400 mt-0.5">Loitering, Weapons, Conceal</div>
        </div>

        <div className="bg-[#0E131A] border border-[#1E2631] border-t-[3px] border-t-[#DC2626] p-3.5">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono text-[#DC2626]">BLACK-LISTED SOURCES</span>
            <ShieldAlert className="w-4 h-4 text-[#DC2626]" />
          </div>
          <div className="font-mono text-2xl font-bold text-white mt-1">256 IPs</div>
          <div className="text-[11px] font-mono text-slate-400 mt-0.5">Automated Firewall Sync</div>
        </div>

        <div className="bg-[#0E131A] border border-[#1E2631] border-t-[3px] border-t-[#10B981] p-3.5">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono text-[#10B981]">INTELLIGENCE STATUS</span>
            <Database className="w-4 h-4 text-[#10B981]" />
          </div>
          <div className="font-mono text-2xl font-bold text-white mt-1">ONLINE</div>
          <div className="text-[11px] font-mono text-[#10B981] mt-0.5">National Cyber Center Feed</div>
        </div>
      </div>

      {/* Ma trận MITRE ATT&CK An ninh Đô thị */}
      <div className="bg-[#0E131A] border border-[#1E2631] p-4">
        <div className="text-xs font-bold uppercase text-white flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-[#10B981]" />
            <span>MITRE ATT&CK URBAN THREAT MATRIX MAPPING</span>
          </div>
          <span className="text-[10px] font-mono text-slate-500">Framework v14.1 Enterprise & Physical</span>
        </div>

        <div className="grid grid-cols-4 gap-3">
          {mitreTactics.map((m) => (
            <div key={m.code} className="bg-[#121822] border border-[#1E2631] p-3 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[10px] font-mono font-bold" style={{ color: m.color }}>{m.code}</span>
                  <span className="px-1.5 py-0.2 bg-[#0E131A] border border-[#1E2631] text-[9px] font-mono text-slate-400">{m.count}</span>
                </div>
                <div className="font-bold text-xs text-white">{m.phase}</div>
                <div className="text-[10px] text-slate-400 mt-1 leading-normal">{m.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Bảng Danh sách Đen & Nguồn Nghi vấn */}
      <div className="bg-[#0E131A] border border-[#1E2631] overflow-hidden">
        <div className="bg-[#121822] border-b border-[#1E2631] px-4 py-2.5 flex items-center justify-between">
          <div className="font-bold text-xs uppercase text-white">
            ACTIVE THREAT BLACKLIST & FORENSIC IP FEED
          </div>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 bg-[#080B10] border border-[#1E2631] px-2 py-1">
              <Search className="w-3.5 h-3.5 text-slate-400" />
              <input
                type="text"
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value)}
                placeholder="Tìm IP hoặc loại vi phạm..."
                className="bg-transparent border-none outline-none text-xs text-white placeholder-slate-500 font-mono w-44"
              />
            </div>
          </div>
        </div>

        <div className="overflow-x-auto min-w-0">
          <table className="w-full text-left font-mono text-xs min-w-[750px]">
            <thead className="bg-[#121822] text-[#64748B] border-b border-[#1E2631]">
              <tr>
                <th className="p-3">SOURCE IP</th>
                <th className="p-3">ORIGIN / REGION</th>
                <th className="p-3">ATTACK SIGNATURE / BEHAVIOR</th>
                <th className="p-3">MITRE CODE</th>
                <th className="p-3 text-center">RISK SCORE</th>
                <th className="p-3">LAST SEEN</th>
                <th className="p-3 text-center">ACTION</th>
              </tr>
            </thead>
            <tbody>
              {filteredThreats.map((t) => {
                const isBlocked = blockedIps.includes(t.ip);
                return (
                  <tr key={t.ip} className="border-b border-[#1E2631] hover:bg-[#161E29]/50">
                    <td className="p-3 text-white font-bold">{t.ip}</td>
                    <td className="p-3 text-slate-400">{t.region}</td>
                    <td className="p-3 text-slate-200">
                      <span className="text-[#F97316] font-semibold">{t.type}</span>
                    </td>
                    <td className="p-3 text-[#06B6D4] text-[11px]">{t.mitre}</td>
                    <td className="p-3 text-center">
                      <span className={`px-2 py-0.5 border font-bold text-[10px] ${
                        t.score > 85 ? 'border-[#DC2626] text-[#DC2626] bg-[#DC2626]/10' : 'border-[#F59E0B] text-[#F59E0B] bg-[#F59E0B]/10'
                      }`}>
                        {t.score}/100
                      </span>
                    </td>
                    <td className="p-3 text-slate-400">{t.lastSeen}</td>
                    <td className="p-3 text-center">
                      <button
                        disabled={isBlocked}
                        onClick={() => handleBlock(t.ip)}
                        className={`px-3 py-1 border font-mono text-[10px] font-bold inline-flex items-center gap-1 cursor-pointer transition-colors ${
                          isBlocked
                            ? 'bg-[#1E2631] border-[#2D3748] text-slate-500 cursor-not-allowed'
                            : 'bg-[#7F1D1D] border-[#DC2626] text-white hover:bg-[#DC2626]'
                        }`}
                      >
                        <Ban className="w-3 h-3" />
                        <span>{isBlocked ? 'BLOCKED' : 'BLOCK IP'}</span>
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
