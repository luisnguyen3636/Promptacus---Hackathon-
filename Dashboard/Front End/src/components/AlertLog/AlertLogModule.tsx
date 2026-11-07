import React, { useState } from 'react';
import { IIncidentItem, ISocMetrics, ThreatLevel } from '../../types/soc.ts';
import {
  AlertTriangle,
  ShieldAlert,
  ShieldCheck,
  Clock,
  Eye,
  ChevronRight,
  Filter,
  CheckCircle,
  XCircle,
  Bell
} from 'lucide-react';

interface AlertLogModuleProps {
  threatScore: number;
  threatLevel: ThreatLevel;
  incidents: IIncidentItem[];
  metrics?: ISocMetrics;
  onSelectPlayback: (incident: IIncidentItem) => void;
  isExpanded?: boolean; // Khi phóng to camera quan sát: mở rộng thành right menu 20% width
  onCloseExpanded?: () => void;
}

export const AlertLogModule: React.FC<AlertLogModuleProps> = ({
  threatScore,
  threatLevel,
  incidents,
  onSelectPlayback,
  isExpanded = false,
  onCloseExpanded,
}) => {
  const [filterSeverity, setFilterSeverity] = useState<'ALL' | 'CRITICAL' | 'HIGH' | 'PENDING'>('ALL');

  // Lọc danh sách cảnh báo theo tab
  const filteredIncidents = incidents.filter((inc) => {
    if (filterSeverity === 'CRITICAL') return inc.severity === 'CRITICAL';
    if (filterSeverity === 'HIGH') return inc.severity === 'HIGH' || inc.severity === 'CRITICAL';
    if (filterSeverity === 'PENDING') return inc.status === 'PENDING_VERIFICATION';
    return true;
  });

  const pendingCount = incidents.filter((i) => i.status === 'PENDING_VERIFICATION').length;
  const criticalCount = incidents.filter((i) => i.severity === 'CRITICAL').length;

  let scoreColor = 'text-[#10B981] border-[#10B981] bg-[#10B981]/10';
  if (threatScore > 75 || threatLevel === 'CRITICAL') scoreColor = 'text-[#EF4444] border-[#EF4444] bg-[#EF4444]/10';
  else if (threatScore > 50 || threatLevel === 'HIGH') scoreColor = 'text-[#F59E0B] border-[#F59E0B] bg-[#F59E0B]/10';
  else if (threatScore > 25 || threatLevel === 'MEDIUM') scoreColor = 'text-[#06B6D4] border-[#06B6D4] bg-[#06B6D4]/10';

  const getSeverityBadge = (severity: string) => {
    switch (severity?.toUpperCase()) {
      case 'CRITICAL':
        return (
          <span className="px-1.5 py-0.5 bg-[#7F1D1D] border border-[#DC2626] text-white font-mono text-[9px] font-bold inline-flex items-center gap-1 animate-pulse shrink-0">
            <span className="w-1.5 h-1.5 rounded-full bg-white"></span>
            CRITICAL
          </span>
        );
      case 'HIGH':
        return (
          <span className="px-1.5 py-0.5 bg-[#78350F] border border-[#F59E0B] text-[#FEF3C7] font-mono text-[9px] font-bold inline-flex items-center gap-1 shrink-0">
            HIGH
          </span>
        );
      case 'MEDIUM':
        return (
          <span className="px-1.5 py-0.5 bg-[#164E63] border border-[#06B6D4] text-[#CFFAFE] font-mono text-[9px] font-bold inline-flex items-center gap-1 shrink-0">
            MED
          </span>
        );
      default:
        return (
          <span className="px-1.5 py-0.5 bg-[#064E3B] border border-[#10B981] text-[#D1FAE5] font-mono text-[9px] font-bold inline-flex items-center gap-1 shrink-0">
            LOW
          </span>
        );
    }
  };

  return (
    <div
      className={`bg-[#0E131A] border border-[#1E2631] flex flex-col select-none transition-all duration-200 ${
        isExpanded
          ? 'w-full h-full shadow-2xl border-l-2 border-l-[#3B82F6]'
          : 'h-full min-h-[380px]'
      }`}
    >
      {/* 1. Header Khối Alert Log */}
      <div className="bg-[#121822] border-b border-[#1E2631] px-3 py-2 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          <Bell className="w-3.5 h-3.5 text-[#F59E0B] shrink-0 animate-bounce" />
          <div className="font-bold text-xs uppercase tracking-wider text-white truncate">
            {isExpanded ? 'RIGHT ALERT MODAL (20%)' : 'SOC ALERT LOG'}
          </div>
        </div>

        {/* Mini Threat Score Badge */}
        <div className={`px-2 py-0.5 border font-mono text-[10px] font-bold rounded-none shrink-0 ${scoreColor}`}>
          SCORE: {threatScore} &bull; {threatLevel}
        </div>
      </div>

      {/* 2. Thanh Tóm tắt Cảnh báo & Bộ Lọc Nhanh */}
      <div className="px-3 py-2 bg-[#090D14] border-b border-[#1E2631] flex items-center justify-between gap-1 text-[11px] font-mono shrink-0">
        <div className="flex items-center gap-1.5">
          <span className="text-slate-400">CHỜ DUYỆT:</span>
          <span className={`font-bold px-1.5 py-0.2 ${pendingCount > 0 ? 'bg-[#DC2626] text-white' : 'bg-[#1E293B] text-slate-300'}`}>
            {pendingCount}
          </span>
        </div>

        {/* Nút lọc nhanh */}
        <div className="flex items-center gap-1">
          <button
            onClick={() => setFilterSeverity('ALL')}
            className={`px-1.5 py-0.5 text-[9px] font-bold font-mono transition-colors ${
              filterSeverity === 'ALL' ? 'bg-[#3B82F6] text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            TẤT CẢ
          </button>
          <button
            onClick={() => setFilterSeverity('PENDING')}
            className={`px-1.5 py-0.5 text-[9px] font-bold font-mono transition-colors ${
              filterSeverity === 'PENDING' ? 'bg-[#DC2626] text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            PENDING
          </button>
          <button
            onClick={() => setFilterSeverity('HIGH')}
            className={`px-1.5 py-0.5 text-[9px] font-bold font-mono transition-colors ${
              filterSeverity === 'HIGH' ? 'bg-[#F59E0B] text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            HIGH+
          </button>
        </div>
      </div>

      {/* 3. Danh Sách Alert Log Rút Gọn (Cuộn mượt) */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1.5 max-h-[500px]">
        {filteredIncidents.length === 0 ? (
          <div className="p-4 text-center text-slate-500 font-mono text-xs flex flex-col items-center justify-center h-48">
            <ShieldCheck className="w-8 h-8 text-[#10B981] mb-2 opacity-60" />
            <div>Không có mối đe dọa nào đang kích hoạt</div>
            <div className="text-[10px] text-slate-600 mt-1">Hệ thống đang quan sát liên tục</div>
          </div>
        ) : (
          filteredIncidents.map((inc) => {
            const timeStr = inc.timestamp?.includes('T')
              ? inc.timestamp.split('T')[1].substring(0, 8)
              : inc.timestamp || '--:--:--';

            const isPending = inc.status === 'PENDING_VERIFICATION';

            return (
              <div
                key={inc.id}
                onClick={() => onSelectPlayback(inc)}
                className={`p-2 border transition-all duration-150 cursor-pointer group select-none ${
                  inc.severity === 'CRITICAL'
                    ? 'bg-[#180A0A] border-[#7F1D1D] hover:border-[#EF4444]'
                    : inc.severity === 'HIGH'
                    ? 'bg-[#181207] border-[#78350F] hover:border-[#F59E0B]'
                    : 'bg-[#0B1017] border-[#1E2631] hover:border-[#3B82F6]'
                }`}
              >
                {/* Hàng 1: Badge Severity + Time + Mã Camera */}
                <div className="flex items-center justify-between gap-1 mb-1">
                  <div className="flex items-center gap-1.5 min-w-0">
                    {getSeverityBadge(inc.severity)}
                    <span className="font-mono text-[10px] text-slate-400 font-bold truncate">
                      {inc.cameraId || 'LAPTOP_01'}
                    </span>
                  </div>
                  <div className="flex items-center gap-1 text-[10px] font-mono text-slate-400 shrink-0">
                    <Clock className="w-2.5 h-2.5" />
                    <span>{timeStr}</span>
                  </div>
                </div>

                {/* Hàng 2: Tên Hành vi & Chi tiết tóm tắt */}
                <div className="font-bold text-xs text-white group-hover:text-[#3B82F6] truncate transition-colors">
                  {inc.title || 'PHÁT HIỆN HÀNH VI BẤT THƯỜNG'}
                </div>

                <div className="text-[10px] text-slate-400 line-clamp-2 mt-0.5 leading-snug">
                  {inc.vlmAnalysis || inc.postureDetails || 'AI Kinematics & DeepSeek VLM Evaluated.'}
                </div>

                {/* Hàng 3: Trạng thái & Nút Thẩm định HITL */}
                <div className="mt-1.5 pt-1 border-t border-[#1E2631] flex items-center justify-between text-[10px] font-mono">
                  <span className={isPending ? 'text-[#F59E0B] font-bold animate-pulse' : 'text-[#10B981]'}>
                    {isPending ? 'CHỜ THẨM ĐỊNH' : 'ĐÃ XÁC NHẬN'}
                  </span>

                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectPlayback(inc);
                    }}
                    className="px-1.5 py-0.5 bg-[#161E29] border border-[#2D3748] group-hover:border-[#3B82F6] text-white text-[9px] font-bold flex items-center gap-1 cursor-pointer transition-colors"
                  >
                    <Eye className="w-2.5 h-2.5 text-[#3B82F6]" />
                    <span>XEM</span>
                    <ChevronRight className="w-2.5 h-2.5" />
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* 4. Footer Mini Thông số Nhanh */}
      <div className="p-2 bg-[#090D14] border-t border-[#1E2631] text-[10px] font-mono text-slate-400 flex items-center justify-between shrink-0">
        <span>CẬP NHẬT: REALTIME</span>
        <span className="text-[#10B981] font-bold">ONLINE 100%</span>
      </div>
    </div>
  );
};
