import React, { useState } from 'react';
import {
  AlertTriangle,
  ShieldAlert,
  ShieldCheck,
  Crosshair,
  Search,
  Users,
  Eye,
  Play
} from 'lucide-react';
import { IIncidentItem } from '../../types/soc.ts';

interface ThreatIntelligenceViewProps {
  incidents?: IIncidentItem[];
  onSelectPlayback?: (incident: IIncidentItem) => void;
}

export const ThreatIntelligenceView: React.FC<ThreatIntelligenceViewProps> = ({
  incidents = [],
  onSelectPlayback,
}) => {
  const [searchFilter, setSearchFilter] = useState<string>('');
  const [cueFilter, setCueFilter] = useState<'ALL' | 'WEAPON' | 'CONTACT' | 'FALLEN' | 'URGENT'>('ALL');

  // Tính toán các chỉ số hoàn toàn từ dữ liệu thật do Server gửi lên
  const totalEvents = incidents.length;
  const urgentEvents = incidents.filter((i) => i.isUrgent || i.severity === 'CRITICAL').length;
  const physicalContactCount = incidents.filter((i) => i.visualCues?.physical_contact).length;
  const weaponsVisibleCount = incidents.filter((i) => i.visualCues?.weapons_visible).length;
  const fallenPersonCount = incidents.filter((i) => i.visualCues?.fallen_person).length;
  const totalActorsCount = incidents.reduce(
    (sum, i) => sum + (i.actors?.length || i.humanCount || 0),
    0
  );

  // Thống kê theo loại hành vi (action_type) thật từ Server
  const actionTypeCounts: Record<string, { count: number; maxScore: number; desc: string }> = {};
  incidents.forEach((inc) => {
    const act = inc.actionType || 'OBSERVED_EVENT';
    const score =
      inc.threatScore !== undefined
        ? inc.threatScore <= 1
          ? Math.round(inc.threatScore * 100)
          : Math.round(inc.threatScore)
        : 0;
    if (!actionTypeCounts[act]) {
      actionTypeCounts[act] = {
        count: 0,
        maxScore: score,
        desc: inc.description || inc.title,
      };
    }
    actionTypeCounts[act].count += 1;
    if (score > actionTypeCounts[act].maxScore) {
      actionTypeCounts[act].maxScore = score;
    }
  });

  const actionGroups = Object.entries(actionTypeCounts);

  const filteredIncidents = incidents.filter((inc) => {
    if (cueFilter === 'WEAPON' && !inc.visualCues?.weapons_visible) return false;
    if (cueFilter === 'CONTACT' && !inc.visualCues?.physical_contact) return false;
    if (cueFilter === 'FALLEN' && !inc.visualCues?.fallen_person) return false;
    if (cueFilter === 'URGENT' && !inc.isUrgent && inc.severity !== 'CRITICAL') return false;

    if (!searchFilter.trim()) return true;
    const q = searchFilter.toLowerCase();
    return (
      (inc.actionType || '').toLowerCase().includes(q) ||
      (inc.description || '').toLowerCase().includes(q) ||
      (inc.reasoning || '').toLowerCase().includes(q) ||
      (inc.cameraId || '').toLowerCase().includes(q) ||
      (inc.location || '').toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-4 select-none min-w-0">
      {/* 4 Thẻ Đo lường Tình báo Thật từ Server JSON */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-[#0E131A] border border-[#1E2631] border-t-[3px] border-t-[#06B6D4] p-3.5">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono text-[#06B6D4]">TỔNG SỰ KIỆN TÌNH BÁO</span>
            <AlertTriangle className="w-4 h-4 text-[#06B6D4]" />
          </div>
          <div className="font-mono text-2xl font-bold text-white mt-1">{totalEvents}</div>
          <div className="text-[11px] font-mono text-slate-400 mt-0.5">
            Đang lưu trữ trên Cloudflare KV
          </div>
        </div>

        <div className="bg-[#0E131A] border border-[#1E2631] border-t-[3px] border-t-[#DC2626] p-3.5">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono text-[#DC2626]">SỰ CỐ KHẨN CẤP (URGENT)</span>
            <ShieldAlert className="w-4 h-4 text-[#DC2626]" />
          </div>
          <div className="font-mono text-2xl font-bold text-white mt-1">{urgentEvents}</div>
          <div className="text-[11px] font-mono text-slate-400 mt-0.5">
            Khuyến nghị: DISPATCH_SECURITY
          </div>
        </div>

        <div className="bg-[#0E131A] border border-[#1E2631] border-t-[3px] border-t-[#F59E0B] p-3.5">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono text-[#F59E0B]">DẤU HIỆU VA CHẠM / VŨ KHÍ</span>
            <Crosshair className="w-4 h-4 text-[#F59E0B]" />
          </div>
          <div className="font-mono text-2xl font-bold text-white mt-1">
            {physicalContactCount + weaponsVisibleCount + fallenPersonCount}
          </div>
          <div className="text-[11px] font-mono text-slate-400 mt-0.5">
            Va chạm: {physicalContactCount} &bull; Vũ khí: {weaponsVisibleCount} &bull; Ngã: {fallenPersonCount}
          </div>
        </div>

        <div className="bg-[#0E131A] border border-[#1E2631] border-t-[3px] border-t-[#10B981] p-3.5">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono text-[#10B981]">ĐỐI TƯỢNG GHI NHẬN (ACTORS)</span>
            <Users className="w-4 h-4 text-[#10B981]" />
          </div>
          <div className="font-mono text-2xl font-bold text-white mt-1">{totalActorsCount}</div>
          <div className="text-[11px] font-mono text-[#10B981] mt-0.5">
            Tổng số cá nhân trong các bản tin
          </div>
        </div>
      </div>

      {/* Phân loại Hành vi thực tế từ Server (Action Type Matrix) */}
      <div className="bg-[#0E131A] border border-[#1E2631] p-4">
        <div className="text-xs font-bold uppercase text-white flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-[#10B981]" />
            <span>PHÂN LOẠI HÀNH VI TỪ SERVER (ACTION TYPE DISTRIBUTION)</span>
          </div>
          <span className="text-[10px] font-mono text-slate-500">Real-time KV Sync</span>
        </div>

        {actionGroups.length === 0 ? (
          <div className="p-6 text-center font-mono text-xs text-slate-500 border border-[#1E2631] bg-[#080B10]">
            Chưa có dữ liệu tình báo nào từ Server gửi lên.
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {actionGroups.map(([actType, info]) => (
              <div
                key={actType}
                className="bg-[#121822] border border-[#1E2631] p-3 flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[11px] font-mono font-bold text-[#F59E0B]">
                      {actType}
                    </span>
                    <span className="px-1.5 py-0.5 bg-[#0E131A] border border-[#1E2631] text-[10px] font-mono text-white font-bold">
                      {info.count} sự kiện
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-300 mt-1 line-clamp-2">{info.desc}</div>
                  <div className="text-[10px] font-mono text-[#EF4444] mt-2">
                    Max Threat Score: {info.maxScore}/100
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Bảng Phân tích Tình báo & Đối tượng (Actors & Visual Cues Feed) */}
      <div className="bg-[#0E131A] border border-[#1E2631] overflow-hidden">
        <div className="bg-[#121822] border-b border-[#1E2631] px-4 py-2.5 flex items-center justify-between flex-wrap gap-3">
          <div className="font-bold text-xs uppercase text-white">
            BẢNG PHÂN TÍCH TÌNH BÁO HÀNH VI & ĐỐI TƯỢNG (SERVER JSON FEED)
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            {/* Bộ lọc Visual Cues */}
            {(
              [
                { id: 'ALL', label: 'TẤT CẢ' },
                { id: 'URGENT', label: 'KHẨN CẤP' },
                { id: 'CONTACT', label: 'VA CHẠM VẬT LÝ' },
                { id: 'WEAPON', label: 'CÓ VŨ KHÍ' },
                { id: 'FALLEN', label: 'NGƯỜI NGÃ' },
              ] as const
            ).map((btn) => (
              <button
                key={btn.id}
                onClick={() => setCueFilter(btn.id)}
                className={`px-2 py-1 font-mono text-[10px] font-bold border cursor-pointer transition-colors ${
                  cueFilter === btn.id
                    ? 'bg-[#112224] border-[#10B981] text-[#10B981]'
                    : 'bg-[#080B10] border-[#1E2631] text-slate-400 hover:text-white'
                }`}
              >
                {btn.label}
              </button>
            ))}

            <div className="flex items-center gap-1.5 bg-[#080B10] border border-[#1E2631] px-2 py-1">
              <Search className="w-3.5 h-3.5 text-slate-400" />
              <input
                type="text"
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value)}
                placeholder="Tìm hành vi, camera, vị trí..."
                className="bg-transparent border-none outline-none text-xs text-white placeholder-slate-500 font-mono w-48"
              />
            </div>
          </div>
        </div>

        <div className="overflow-x-auto min-w-0">
          <table className="w-full text-left font-mono text-xs min-w-[850px]">
            <thead className="bg-[#121822] text-[#64748B] border-b border-[#1E2631]">
              <tr>
                <th className="p-3">CAMERA / LOCATION</th>
                <th className="p-3">ACTION TYPE</th>
                <th className="p-3">DESCRIPTION & REASONING</th>
                <th className="p-3">ACTORS (ROLES & POSTURE)</th>
                <th className="p-3">VISUAL CUES</th>
                <th className="p-3 text-center">THREAT SCORE</th>
                <th className="p-3 text-center">ACTION</th>
              </tr>
            </thead>
            <tbody>
              {filteredIncidents.length === 0 ? (
                <tr>
                  <td colSpan={7} className="p-8 text-center text-slate-500 font-mono text-xs">
                    Chưa có dữ liệu tình báo nào khớp với bộ lọc. Hệ thống đang chờ JSON từ Server.
                  </td>
                </tr>
              ) : (
                filteredIncidents.map((inc) => {
                  const scorePct =
                    inc.threatScore !== undefined
                      ? inc.threatScore <= 1
                        ? Math.round(inc.threatScore * 100)
                        : Math.round(inc.threatScore)
                      : 0;

                  return (
                    <tr
                      key={inc.id}
                      className="border-b border-[#1E2631] hover:bg-[#161E29]/50 align-top"
                    >
                      <td className="p-3">
                        <div className="text-white font-bold">{inc.cameraId || 'N/A'}</div>
                        <div className="text-[10px] text-slate-400">{inc.location || inc.subTitle}</div>
                        <div className="text-[10px] text-slate-500 mt-0.5">
                          FPS: {inc.measuredFps ?? 'N/A'} &bull; Frame #{inc.frameIndex ?? 'N/A'}
                        </div>
                      </td>

                      <td className="p-3">
                        <span className="text-[#EF4444] font-bold">{inc.actionType || inc.severity}</span>
                        <div className="text-[10px] text-slate-400 mt-0.5">
                          Confidence:{' '}
                          {inc.confidence !== undefined
                            ? `${Math.round(inc.confidence * 100)}%`
                            : 'N/A'}
                        </div>
                        <div className="text-[10px] text-[#10B981] mt-0.5">
                          {inc.recommendedAction}
                        </div>
                      </td>

                      <td className="p-3 max-w-[280px]">
                        <div className="text-slate-100 font-semibold">{inc.description || inc.title}</div>
                        <div className="text-[11px] text-slate-400 mt-1">{inc.reasoning}</div>
                      </td>

                      <td className="p-3 max-w-[240px]">
                        {inc.actors && inc.actors.length > 0 ? (
                          <div className="space-y-1">
                            {inc.actors.map((a, i) => (
                              <div key={i} className="text-[11px] bg-[#080B10] p-1.5 border border-[#1E2631]">
                                <span className="font-bold text-white">#{a.id}</span>{' '}
                                <span
                                  className={
                                    a.role === 'attacker'
                                      ? 'text-[#EF4444] font-bold uppercase'
                                      : 'text-[#38BDF8] font-bold uppercase'
                                  }
                                >
                                  [{a.role}]
                                </span>{' '}
                                <span className="text-[#F59E0B]">{a.action}</span>
                                <div className="text-[10px] text-slate-400">{a.posture}</div>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <span className="text-slate-500">Human count: {inc.humanCount ?? 0}</span>
                        )}
                      </td>

                      <td className="p-3">
                        {inc.visualCues ? (
                          <div className="space-y-1 text-[10px]">
                            <div
                              className={
                                inc.visualCues.weapons_visible ? 'text-[#EF4444] font-bold' : 'text-slate-500'
                              }
                            >
                              • Vũ khí: {inc.visualCues.weapons_visible ? 'CÓ' : 'Không'}
                            </div>
                            <div
                              className={
                                inc.visualCues.physical_contact ? 'text-[#F59E0B] font-bold' : 'text-slate-500'
                              }
                            >
                              • Va chạm: {inc.visualCues.physical_contact ? 'CÓ' : 'Không'}
                            </div>
                            <div
                              className={
                                inc.visualCues.fallen_person ? 'text-[#EF4444] font-bold' : 'text-slate-500'
                              }
                            >
                              • Người ngã: {inc.visualCues.fallen_person ? 'CÓ' : 'Không'}
                            </div>
                          </div>
                        ) : (
                          <span className="text-slate-500">N/A</span>
                        )}
                      </td>

                      <td className="p-3 text-center">
                        <span
                          className={`px-2 py-0.5 border font-bold text-[10px] ${
                            scorePct >= 80
                              ? 'border-[#DC2626] text-[#DC2626] bg-[#DC2626]/10'
                              : 'border-[#F59E0B] text-[#F59E0B] bg-[#F59E0B]/10'
                          }`}
                        >
                          {scorePct}/100
                        </span>
                      </td>

                      <td className="p-3 text-center">
                        <button
                          onClick={() => onSelectPlayback && onSelectPlayback(inc)}
                          className="px-2.5 py-1 bg-[#161E29] border border-[#2D3748] hover:border-[#10B981] text-white hover:text-[#10B981] font-mono text-[10px] font-bold inline-flex items-center gap-1 cursor-pointer transition-colors"
                        >
                          <Eye className="w-3 h-3" />
                          <span>CHI TIẾT</span>
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
