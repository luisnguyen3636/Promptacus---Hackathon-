import React, { useState } from 'react';
import { Search, Filter, Play, Clock, ShieldAlert, CheckCircle2, XCircle } from 'lucide-react';
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
    const matchSearch =
      inc.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      inc.sourceIp.includes(searchQuery) ||
      (inc.cameraId && inc.cameraId.toLowerCase().includes(searchQuery.toLowerCase())) ||
      inc.id.toLowerCase().includes(searchQuery.toLowerCase());
    return matchSeverity && matchStatus && matchSearch;
  });

  const totalIncidents = incidents.length;
  const criticalCount = incidents.filter(i => i.severity === 'CRITICAL').length;
  const pendingCount = incidents.filter(i => i.status === 'PENDING_VERIFICATION').length;
  const verifiedCount = incidents.filter(i => i.status === 'OPERATOR_CONFIRMED').length;

  return (
    <div className="space-y-4 select-none min-w-0">
      {/* Thanh Chỉ số Triage Sự cố Hôm nay */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-[#0E131A] border border-[#1E2631] p-3 flex items-center justify-between">
          <div>
            <div className="font-mono text-xl font-bold text-white">{totalIncidents} Incidents</div>
            <div className="text-[11px] text-slate-400 font-mono mt-0.5">Recorded Today</div>
          </div>
          <Clock className="w-6 h-6 text-[#10B981]" />
        </div>

        <div className="bg-[#0E131A] border border-[#1E2631] p-3 flex items-center justify-between">
          <div>
            <div className="font-mono text-xl font-bold text-[#DC2626]">{criticalCount} Critical</div>
            <div className="text-[11px] text-slate-400 font-mono mt-0.5">Physical Intrusion & Weapons</div>
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
            placeholder="Tìm kiếm mã sự cố (inc_xxx), IP, Camera..."
            className="bg-transparent border-none outline-none text-xs text-white placeholder-slate-500 w-full font-mono"
          />
        </div>

        {/* Nút lọc cấp độ */}
        <div className="flex items-center gap-1.5 shrink-0">
          <span className="text-[11px] font-mono text-slate-500 mr-1">SEVERITY:</span>
          {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM'].map((sev) => (
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
            { id: 'DISMISSED', label: 'ĐÃ HỦY' }
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
        {filtered.map((inc) => {
          let badgeColor = 'border-[#EAB308] text-[#EAB308] bg-[#EAB308]/10';
          if (inc.severity === 'CRITICAL') badgeColor = 'border-[#DC2626] text-[#DC2626] bg-[#DC2626]/15';
          else if (inc.severity === 'HIGH') badgeColor = 'border-[#F97316] text-[#F97316] bg-[#F97316]/10';

          const isConfirmed = inc.status === 'OPERATOR_CONFIRMED';
          const isDismissed = inc.status === 'DISMISSED';

          return (
            <div
              key={inc.id}
              className="bg-[#0E131A] border border-[#1E2631] p-4 flex flex-col space-y-3 hover:border-[#10B981] transition-colors"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-center gap-3 min-w-0">
                  <div
                    className={`w-3 h-3 shrink-0 ${
                      inc.severity === 'CRITICAL' ? 'bg-[#DC2626]' : inc.severity === 'HIGH' ? 'bg-[#F97316]' : 'bg-[#EAB308]'
                    }`}
                  />
                  <div className="min-w-0">
                    <div className="font-bold text-sm text-white flex items-center gap-2 flex-wrap">
                      <span className="truncate">{inc.title}</span>
                      <span className={`font-mono text-[10px] font-bold px-2 py-0.5 border ${badgeColor} shrink-0`}>
                        {inc.severity}
                      </span>
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
                      {inc.modelUsed && (
                        <span className="font-mono text-[10px] text-[#06B6D4] bg-[#06B6D4]/10 px-1.5 py-0.5 border border-[#06B6D4]/30 shrink-0">
                          {inc.modelUsed} ({inc.latencyMs || 925}ms)
                        </span>
                      )}
                    </div>

                    <div className="text-xs text-slate-400 font-mono mt-1">
                      Thời điểm: <span className="text-white font-bold">{inc.timestamp}</span> &bull; Khu vực:{' '}
                      <span className="text-[#38BDF8]">{inc.subTitle || 'Laptop Client Zone'}</span> &bull; Camera:{' '}
                      <span className="text-slate-300">{inc.cameraId || 'N/A'}</span>
                    </div>
                  </div>
                </div>

                <button
                  onClick={() => onSelectPlayback(inc)}
                  className="bg-[#161E29] border border-[#2D3748] text-white hover:bg-[#1E2631] hover:border-[#10B981] hover:text-[#10B981] font-mono text-xs font-bold px-3 py-1.5 inline-flex items-center gap-2 cursor-pointer transition-colors shrink-0"
                >
                  <Play className="w-3 h-3 fill-current" />
                  <span>XEM LẠI BẰNG CHỨNG & DISPATCH</span>
                </button>
              </div>

              {/* Kinematics and Posture Details */}
              {(inc.kinematicsSummary || inc.postureDetails) && (
                <div className="bg-[#121822] p-2.5 border border-[#1E2631] text-xs font-mono text-slate-300 grid grid-cols-1 md:grid-cols-2 gap-2">
                  <div>
                    <span className="text-[#64748B]">TƯ THẾ: </span>
                    <span className="text-slate-200">{inc.postureDetails || `Detected action: ${inc.title}`}</span>
                  </div>
                  <div>
                    <span className="text-[#64748B]">ĐỘNG HỌC: </span>
                    <span className="text-[#38BDF8]">{inc.kinematicsSummary || 'N/A'}</span>
                  </div>
                </div>
              )}

              {/* VLM Analysis Context */}
              {inc.vlmAnalysis && (
                <div className="bg-[#121822] p-3 border-l-2 border-[#10B981] text-xs text-slate-300 leading-relaxed font-sans">
                  <strong className="text-[#10B981] font-mono">VLM Hành vi Suy luận: </strong>
                  {inc.vlmAnalysis}
                </div>
              )}

              {/* Snapshots nếu có */}
              {inc.cameraSnapshots && (
                <div className="flex items-center gap-3 pt-1 border-t border-[#1E2631]/40">
                  <span className="font-mono text-[11px] text-slate-400">Ảnh Bằng chứng Rolling Buffer:</span>
                  <div className="flex gap-2">
                    <img
                      src={inc.cameraSnapshots.preEventSnapshotUrl}
                      alt="Pre-Event"
                      className="w-[84px] h-[48px] object-cover border border-[#1E2631] filter grayscale contrast-125"
                    />
                    <img
                      src={inc.cameraSnapshots.eventPeakSnapshotUrl}
                      alt="Event-Peak"
                      className="w-[84px] h-[48px] object-cover border border-[#1E2631] filter grayscale contrast-125"
                    />
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
