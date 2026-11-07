import React from 'react';
import { Activity } from 'lucide-react';
import { IIncidentItem } from '../../types/soc.ts';
import { ThreatRow } from './ThreatRow.tsx';

interface RecentThreatsTableProps {
  incidents: IIncidentItem[];
  onSelectPlayback: (incident: IIncidentItem) => void;
}

export const RecentThreatsTable: React.FC<RecentThreatsTableProps> = ({
  incidents,
  onSelectPlayback,
}) => {
  return (
    <section className="bg-[#0E131A] border border-[#1E2631] overflow-hidden">
      {/* Header Bảng */}
      <div className="bg-[#121822] border-b border-[#1E2631] px-4 py-2 flex items-center justify-between select-none">
        <div className="flex items-center gap-2">
          <span className="font-bold text-xs uppercase tracking-wider text-[#E2E8F0]">
            RECENT THREATS
          </span>
        </div>
        <Activity className="w-4 h-4 text-[#64748B]" />
      </div>

      {/* Container Cuộn ngang chống tràn viền trên màn hình nhỏ */}
      <div className="overflow-x-auto min-w-0">
        {/* Tiêu đề Cột (7 Cột căn chuẩn) */}
        <div className="grid grid-cols-[20px_55px_minmax(140px,1fr)_120px_120px_90px_105px] items-center gap-2.5 px-3 py-2 border-b border-[#1E2631] bg-[#121822] text-[10px] font-mono text-[#64748B] uppercase select-none min-w-[650px]">
          <div></div>
          <div>TIME</div>
          <div>EVENT / TARGET</div>
          <div className="text-center">SOURCE IP</div>
          <div>CAMERA SNAPSHOT</div>
          <div className="text-center">SEVERITY</div>
          <div className="text-center">ACTION</div>
        </div>

        {/* Danh sách Sự kiện */}
        <div>
          {incidents.length === 0 ? (
            <div className="py-8 text-center text-slate-500 font-mono text-xs">
              [SYSTEM NOMINAL] Không có sự cố đe dọa nào · Hệ thống sẵn sàng tiếp nhận luồng cảnh báo từ AI.
            </div>
          ) : (
            incidents.map((inc) => (
              <ThreatRow key={inc.id} incident={inc} onPlayback={onSelectPlayback} />
            ))
          )}
        </div>
      </div>
    </section>
  );
};
