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
            RECENT SERVER EVENTS (CLOUDFLARE KV)
          </span>
        </div>
        <Activity className="w-4 h-4 text-[#64748B]" />
      </div>

      {/* Container Cuộn ngang chống tràn viền trên màn hình nhỏ */}
      <div className="overflow-x-auto min-w-0">
        {/* Tiêu đề Cột (7 Cột căn chuẩn) */}
        <div className="grid grid-cols-[20px_65px_minmax(160px,1fr)_120px_120px_90px_105px] items-center gap-2.5 px-3 py-2 border-b border-[#1E2631] bg-[#121822] text-[10px] font-mono text-[#64748B] uppercase select-none min-w-[680px]">
          <div></div>
          <div>TIME</div>
          <div>ACTION / DESCRIPTION / LOCATION</div>
          <div className="text-center">CAMERA ID</div>
          <div className="text-center">SCORE / ACTORS</div>
          <div className="text-center">SEVERITY</div>
          <div className="text-center">ACTION</div>
        </div>

        {/* Danh sách Sự kiện */}
        <div>
          {incidents.length === 0 ? (
            <div className="py-8 text-center text-slate-500 font-mono text-xs">
              [KV EMPTY] Chưa có sự cố nào được Server gửi lên. Hệ thống sẵn sàng lưu trữ JSON vào KV khi nhận dữ liệu.
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
