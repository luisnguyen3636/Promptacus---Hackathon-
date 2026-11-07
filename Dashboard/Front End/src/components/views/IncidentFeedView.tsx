import React, { useState } from 'react';
import { Search, Play, Clock, ShieldAlert, CheckCircle2, XCircle, Users, Activity } from 'lucide-react';
import { IIncidentItem } from '../../types/soc.ts';

interface IncidentFeedViewProps {
  incidents: IIncidentItem[];
  onSelectPlayback: (incident: IIncidentItem) => void;
}

export const IncidentFeedView: React.FC<IncidentFeedViewProps> = ({
  incidents,
  onSelectPlayback,
}) => {
  const [filterSeverity, setFilterSeverity] = useState<string>('ALL');
  const [filterStatus, setFilterStatus] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const filtered = incidents.filter((inc) => {
    const matchSeverity = filterSeverity === 'ALL' || inc.severity === filterSeverity;
    const matchStatus = filterStatus === 'ALL' || inc.status === filterStatus;
    const q = searchQuery.toLowerCase();
    const matchSearch =
      !q ||
      inc.title.toLowerCase().includes(q) ||
      (inc.actionType && inc.actionType.toLowerCase().includes(q)) ||
      (inc.location && inc.location.toLowerCase().includes(q)) ||
      (inc.cameraId && inc.cameraId.toLowerCase().includes(q)) ||
      (inc.description && inc.description.toLowerCase().includes(q)) ||
      inc.id.toLowerCase().includes(q);
    return matchSeverity && matchStatus && matchSearch;
  });

  const totalIncidents = incidents.length;
  const criticalCount = incidents.filter((i) => i.severity === 'CRITICAL').length;
  const pendingCount = incidents.filter((i) => i.status === 'PENDING_VERIFICATION').length;
  const verifiedCount = incidents.filter((i) => i.status === 'OPERATOR_CONFIRMED').length;

  return (
    <div className="space-y-4 select-none min-w-0">
      {/* Thanh Chỉ số Triage Sự cố từ KV */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-[#0E131A] border border-[#1E2631] p-3 flex items-center justify-between">
          <div>
            <div className="font-mono text-xl font-bold text-white">{totalIncidents} Incidents</div>
            <div className="text-[11px] text-slate-400 font-mono mt-0.5">Stored in Cloudflare KV</div>
          </div>
          <Clock className="w-6 h-6 text-[#10B981]" />
        </div>

        <div className="bg-[#0E131A] border border-[#1E2631] p-3 flex items-center justify-between">
          <div>
            <div className="font-mono text-xl font-bold text-[#DC2626]">{criticalCount} Critical</div>
            <div className="text-[11px] text-slate-400 font-mono mt-0.5">High-Severity Server Events</div>
          </div>
          <ShieldAlert className="w-6 h-6 text-[#DC2626]" />
        </div>

        <div className="bg-[#0E131A] border border-[#1E2631] p-3 flex items-center justify-between">
          <div>
            <div className="font-mono text-xl font-bold text-[#F59E0B]">{pendingCount} Awaiting</div>
            <div className="text-[11px] text-slate-400 font-mono mt-0.5">Pending Operator HITL</div>
          </div>
          <CheckCircle2 className="w-6 h-6 text-[#F59E0B]" />
        </div>

        <div className="bg-[#0E131A] border border-[#1E2631] p-3 flex items-center justify-between">
          <div>
            <div className="font-mono text-xl font-bold text-[#10B981]">{verifiedCount} Dispatched</div>
            <div className="text-[11px] text-slate-400 font-mono mt-0.5">Operator Verified</div>
          </div>
          <XCircle className="w-6 h-6 text-[#10B981]" />
        </div>
      </div>

      {/* Thanh Lọc & Tìm kiếm Nâng cao */}
      <div className="bg-[#0E131A] border border-[#1E2631] p-3 flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-2 flex-1 min-w-[240px] bg-[#161E29] border border-[#1E2631] px-3 py-1.5">
          <Search className="w-4 h-4 text-slate-400 shrink-0" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Tìm kiếm mã sự cố, action_type (FIGHTING...), camera_id, location..."
            className="bg-transparent border-none outline-none text-xs text-white placeholder-slate-500 w-full font-mono"
          />
        </div>

        {/* Nút lọc cấp độ */}
        <div className="flex items-center gap-1.5 shrink-0">
          <span className="text-[11px] font-mono text-slate-500 mr-1">SEVERITY:</span>
          {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((sev) => (
            <button
              key={sev}
              onClick={() => setFilterSeverity(sev)}
              className={`px-2.5 py-1 font-mono text-xs font-bold border transition-colors cursor-pointer ${
                filterSeverity === sev
                  ? 'bg-[#112224] text-[#10B981] border-[#10B981]'
                  : 'bg-[#161E29] text-slate-400 border-[#1E2631] hover:text-white'
              }`}
            >
              {sev}
            </button>
          ))}
        </div>

        {/* Nút lọc trạng thái */}
        <div className="flex items-center gap-1.5 shrink-0">
          <span className="text-[11px] font-mono text-slate-500 mr-1">STATUS:</span>
          {[
            { id: 'ALL', label: 'TẤT CẢ' },
            { id: 'PENDING_VERIFICATION', label: 'CHỜ DUYỆT' },
            { id: 'OPERATOR_CONFIRMED', label: 'ĐÃ DISPATCH' },
            { id: 'DISMISSED', label: 'ĐÃ HỦY' },
          ].map((st) => (
            <button
              key={st.id}
              onClick={() => setFilterStatus(st.id)}
              className={`px-2 py-1 font-mono text-[10px] font-bold border transition-colors cursor-pointer ${
                filterStatus === st.id
                  ? 'bg-[#112224] text-[#10B981] border-[#10B981]'
                  : 'bg-[#161E29] text-slate-400 border-[#1E2631] hover:text-white'
              }`}
            >
              {st.label}
            </button>
          ))}
        </div>
      </div>

      {/* Dòng Thời gian Sự cố Chi tiết */}
      <div className="space-y-3">
        {filtered.length === 0 ? (
          <div className="bg-[#0E131A] border border-[#1E2631] p-10 text-center font-mono text-xs text-slate-500">
            Chưa có bản ghi sự cố nào từ Server lưu trong KV khớp với bộ lọc hiện tại.
          </div>
        ) : (
          filtered.map((inc) => {
            let badgeColor = 'border-[#EAB308] text-[#EAB308] bg-[#EAB308]/10';
            if (inc.severity === 'CRITICAL') badgeColor = 'border-[#DC2626] text-[#DC2626] bg-[#DC2626]/15';
            else if (inc.severity === 'HIGH') badgeColor = 'border-[#F97316] text-[#F97316] bg-[#F97316]/10';

            const isConfirmed = inc.status === 'OPERATOR_CONFIRMED';
            const isDismissed = inc.status === 'DISMISSED';
            const scorePct =
              inc.threatScore !== undefined
                ? inc.threatScore <= 1
                  ? Math.round(inc.threatScore * 100)
                  : Math.round(inc.threatScore)
                : 0;

            return (
              <div
                key={inc.id}
                className="bg-[#0E131A] border border-[#1E2631] p-4 flex flex-col space-y-3 hover:border-[#10B981] transition-colors"
              >
                <div className="flex items-start justify-between gap-4 flex-wrap">
                  <div className="flex items-center gap-3 min-w-0">
                    <div
                      className={`w-3 h-3 shrink-0 ${
                        inc.severity === 'CRITICAL'
                          ? 'bg-[#DC2626]'
                          : inc.severity === 'HIGH'
                          ? 'bg-[#F97316]'
                          : 'bg-[#EAB308]'
                      }`}
                    />
                    <div className="min-w-0">
                      <div className="font-bold text-sm text-white flex items-center gap-2 flex-wrap">
                        <span className="truncate">{inc.actionType || inc.title}</span>
                        <span className={`font-mono text-[10px] font-bold px-2 py-0.5 border ${badgeColor} shrink-0`}>
                          {inc.severity}
                        </span>
                        {inc.isUrgent && (
                          <span className="font-mono text-[10px] font-bold px-2 py-0.5 bg-[#7F1D1D] border border-[#EF4444] text-white shrink-0">
                            URGENT
                          </span>
                        )}
                        <span className="font-mono text-[10px] font-bold px-2 py-0.5 bg-[#161E29] border border-[#2D3748] text-[#38BDF8] shrink-0">
                          SCORE: {scorePct}%
                        </span>
                        {inc.recommendedAction && (
                          <span className="font-mono text-[10px] font-bold px-2 py-0.5 bg-[#F59E0B]/15 border border-[#F59E0B] text-[#F59E0B] shrink-0">
                            {inc.recommendedAction}
                          </span>
                        )}
                        {isConfirmed && (
                          <span className="font-mono text-[10px] font-bold px-2 py-0.5 border border-[#10B981] text-[#10B981] bg-[#112224] shrink-0">
                            ✔ OPERATOR CONFIRMED
                          </span>
                        )}
                        {isDismissed && (
                          <span className="font-mono text-[10px] font-bold px-2 py-0.5 border border-[#64748B] text-[#64748B] bg-[#161E29] shrink-0">
                            ✕ DISMISSED FALSE POSITIVE
                          </span>
                        )}
                        <span className="font-mono text-xs text-slate-500 shrink-0">[{inc.eventId || inc.id}]</span>
                      </div>

                      <div className="text-xs text-slate-400 font-mono mt-1 flex items-center gap-3 flex-wrap">
                        <span>
                          Thời điểm: <span className="text-white font-bold">{inc.timestamp}</span>
                        </span>
                        <span>&bull;</span>
                        <span>
                          Vị trí: <span className="text-[#38BDF8]">{inc.location || inc.subTitle || 'N/A'}</span>
                        </span>
                        <span>&bull;</span>
                        <span>
                          Camera: <span className="text-slate-200 font-bold">{inc.cameraId || 'N/A'}</span>
                        </span>
                        {inc.measuredFps !== undefined && (
                          <>
                            <span>&bull;</span>
                            <span className="inline-flex items-center gap-1 text-[#10B981]">
                              <Activity className="w-3 h-3" />
                              {inc.measuredFps} FPS (Frame #{inc.frameIndex ?? 0})
                            </span>
                          </>
                        )}
                        {inc.humanCount !== undefined && (
                          <>
                            <span>&bull;</span>
                            <span className="inline-flex items-center gap-1 text-white">
                              <Users className="w-3 h-3 text-[#38BDF8]" />
                              {inc.humanCount} người
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={() => onSelectPlayback(inc)}
                    className="bg-[#161E29] border border-[#2D3748] text-white hover:bg-[#1E2631] hover:border-[#10B981] hover:text-[#10B981] font-mono text-xs font-bold px-3 py-1.5 inline-flex items-center gap-2 cursor-pointer transition-colors shrink-0"
                  >
                    <Play className="w-3 h-3 fill-current" />
                    <span>CHI TIẾT &amp; THẨM ĐỊNH HITL</span>
                  </button>
                </div>

                {/* Mô tả & Lập luận từ Server Payload */}
                {(inc.description || inc.reasoning || inc.vlmAnalysis) && (
                  <div className="bg-[#121822] p-3 border-l-2 border-[#10B981] text-xs text-slate-300 space-y-1 font-sans">
                    {inc.description && (
                      <div>
                        <strong className="text-[#10B981] font-mono">MÔ TẢ SỰ CỐ: </strong>
                        {inc.description}
                      </div>
                    )}
                    {(inc.reasoning || inc.vlmAnalysis) && (
                      <div>
                        <strong className="text-[#38BDF8] font-mono">LẬP LUẬN (REASONING): </strong>
                        {inc.reasoning || inc.vlmAnalysis}
                      </div>
                    )}
                  </div>
                )}

                {/* Danh sách Actors & Visual Cues */}
                {((inc.actors && inc.actors.length > 0) || inc.visualCues) && (
                  <div className="bg-[#121822] p-2.5 border border-[#1E2631] text-xs font-mono text-slate-300 flex flex-wrap items-center justify-between gap-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-slate-500">ACTORS:</span>
                      {(inc.actors || []).map((a) => (
                        <span
                          key={a.id}
                          className="px-2 py-0.5 bg-[#090D14] border border-[#1E2631] text-[11px]"
                        >
                          <strong className={a.role === 'attacker' ? 'text-[#EF4444]' : 'text-[#38BDF8]'}>
                            #{a.id} {a.role.toUpperCase()}
                          </strong>
                          : {a.action} ({a.posture})
                        </span>
                      ))}
                    </div>

                    {inc.visualCues && (
                      <div className="flex items-center gap-2 text-[10px]">
                        <span className={inc.visualCues.physical_contact ? 'text-[#F59E0B] font-bold' : 'text-slate-500'}>
                          VA CHẠM: {inc.visualCues.physical_contact ? 'CÓ' : 'KHÔNG'}
                        </span>
                        <span>|</span>
                        <span className={inc.visualCues.weapons_visible ? 'text-[#EF4444] font-bold' : 'text-slate-500'}>
                          VŨ KHÍ: {inc.visualCues.weapons_visible ? 'CÓ' : 'KHÔNG'}
                        </span>
                        <span>|</span>
                        <span className={inc.visualCues.fallen_person ? 'text-[#EF4444] font-bold' : 'text-slate-500'}>
                          NGÃ GỤC: {inc.visualCues.fallen_person ? 'CÓ' : 'KHÔNG'}
                        </span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
