import React, { useState } from 'react';
import { Bell, ArrowRight, UserCheck, ShieldAlert } from 'lucide-react';
import { useUtcClock } from '../hooks/useUtcClock.ts';
import { IIncidentItem, IOperatorSession } from '../types/soc.ts';

interface TopHeaderProps {
  activeTab?: string;
  threatScore?: number;
  threatLevel?: string;
  isConnected?: boolean;
  session?: IOperatorSession | null;
  incidents?: IIncidentItem[];
  onOpenAuthModal?: () => void;
  onSelectIncident?: (inc: IIncidentItem) => void;
}

export const TopHeader: React.FC<TopHeaderProps> = ({
  activeTab = 'SOC Dashboard',
  threatScore = 0,
  threatLevel = 'LOW',
  isConnected = false,
  session = null,
  incidents = [],
  onOpenAuthModal,
  onSelectIncident,
}) => {
  const utcTime = useUtcClock();
  const [isBellOpen, setIsBellOpen] = useState<boolean>(false);

  const pendingIncidents = incidents.filter((i) => i.status === 'PENDING_VERIFICATION');

  let threatColorClass = 'text-[#10B981] border-[#10B981]/30';
  if (threatScore > 75 || threatLevel === 'CRITICAL') {
    threatColorClass = 'text-[#DC2626] border-[#DC2626]/40';
  } else if (threatScore > 50 || threatLevel === 'HIGH') {
    threatColorClass = 'text-[#F59E0B] border-[#F59E0B]/40';
  } else if (threatScore > 25 || threatLevel === 'MEDIUM') {
    threatColorClass = 'text-[#06B6D4] border-[#06B6D4]/30';
  }

  return (
    <header className="h-[52px] bg-[#080B10] border-b border-[#1E2631] flex items-center justify-between px-6 sticky top-0 z-30 select-none min-w-0">
      {/* Breadcrumbs & Real-time UTC Clock */}
      <div className="flex items-center gap-3 sm:gap-4 min-w-0 overflow-hidden">
        <div className="text-xs font-medium truncate">
          <span className="text-[#64748B]">CYBERGUARD</span>
          <span className="text-[#64748B] mx-1.5">/</span>
          <span className="text-[#F8FAFC] font-semibold">{activeTab}</span>
        </div>
        <div className="h-4 w-[1px] bg-[#1E2631] shrink-0"></div>
        <div className="text-xs font-mono text-[#94A3B8] whitespace-nowrap shrink-0">
          {utcTime}
        </div>
      </div>

      {/* Trạng thái Tổng quan & Nút Đăng nhập */}
      <div className="flex items-center gap-2 sm:gap-3 shrink-0 relative">
        {/* Threat Level Badge */}
        <div
          className={`px-2.5 sm:px-3 py-1 bg-[#0E131A] border font-mono text-[11px] sm:text-xs font-semibold whitespace-nowrap shrink-0 ${threatColorClass}`}
        >
          ● THREAT LEVEL: {threatLevel} ({threatScore})
        </div>

        {/* Live Wave Indicator */}
        <div className="flex items-center gap-1.5 px-2 sm:px-2.5 py-1 bg-[#0E131A] border border-[#1E2631] shrink-0">
          <span
            className={`w-2 h-2 shrink-0 ${
              isConnected ? 'bg-[#10B981] animate-ping' : 'bg-[#F59E0B]'
            }`}
          ></span>
          <span
            className={`font-mono text-xs font-bold whitespace-nowrap ${
              isConnected ? 'text-[#10B981]' : 'text-[#F59E0B]'
            }`}
          >
            {isConnected ? 'LIVE' : 'SYNCING'}
          </span>
        </div>

        {/* Alert Bell */}
        <div className="relative">
          <button
            onClick={() => setIsBellOpen((prev) => !prev)}
            aria-label="Thông báo cảnh báo"
            className="w-8 h-8 bg-[#0E131A] border border-[#1E2631] text-[#94A3B8] hover:text-white flex items-center justify-center relative cursor-pointer shrink-0"
          >
            <Bell className="w-4 h-4" />
            {pendingIncidents.length > 0 && (
              <span className="absolute -top-1 -right-1 px-1 bg-[#DC2626] text-white font-mono text-[9px] font-bold">
                {pendingIncidents.length}
              </span>
            )}
          </button>

          {isBellOpen && (
            <div className="absolute right-0 mt-2 w-80 bg-[#0E131A] border border-[#1E2631] shadow-2xl z-50 font-mono text-xs">
              <div className="bg-[#121822] px-3 py-2 border-b border-[#1E2631] flex items-center justify-between">
                <span className="font-bold text-white">CẢNH BÁO CHỜ THẨM ĐỊNH ({pendingIncidents.length})</span>
                <button
                  onClick={() => setIsBellOpen(false)}
                  className="text-slate-400 hover:text-white text-[10px] cursor-pointer"
                >
                  [ĐÓNG]
                </button>
              </div>
              <div className="max-h-64 overflow-y-auto divide-y divide-[#1E2631]">
                {pendingIncidents.length === 0 ? (
                  <div className="p-4 text-center text-slate-500">
                    Không có cảnh báo nào chưa xử lý.
                  </div>
                ) : (
                  pendingIncidents.slice(0, 6).map((inc) => (
                    <div
                      key={inc.id}
                      onClick={() => {
                        setIsBellOpen(false);
                        onSelectIncident?.(inc);
                      }}
                      className="p-2.5 hover:bg-[#161E29] cursor-pointer transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-[#EF4444] flex items-center gap-1">
                          <ShieldAlert className="w-3 h-3" />
                          {inc.actionType || inc.severity}
                        </span>
                        <span className="text-[10px] text-slate-400">{inc.cameraId}</span>
                      </div>
                      <div className="text-slate-200 truncate mt-0.5">{inc.description || inc.title}</div>
                      <div className="text-[10px] text-slate-500 truncate">{inc.location || inc.subTitle}</div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {/* Sign In / Operator Session Button */}
        <button
          onClick={onOpenAuthModal}
          className={`px-2.5 sm:px-3 py-1.5 border font-mono text-xs font-bold flex items-center gap-1.5 transition-colors cursor-pointer whitespace-nowrap shrink-0 ${
            session
              ? 'bg-[#112224] border-[#10B981] text-[#10B981] hover:bg-[#10B981] hover:text-[#080B10]'
              : 'border-[#10B981] text-[#10B981] hover:bg-[#10B981] hover:text-[#080B10]'
          }`}
        >
          {session ? (
            <>
              <UserCheck className="w-3.5 h-3.5" />
              <span>{session.operatorId}</span>
            </>
          ) : (
            <>
              <ArrowRight className="w-3.5 h-3.5" />
              <span>Sign In</span>
            </>
          )}
        </button>
      </div>
    </header>
  );
};
