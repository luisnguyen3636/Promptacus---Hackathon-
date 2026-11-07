import React from 'react';
import { Bell, ArrowRight } from 'lucide-react';
import { useUtcClock } from '../hooks/useUtcClock.ts';

interface TopHeaderProps {
  activeTab?: string;
  threatScore?: number;
  threatLevel?: string;
  isConnected?: boolean;
}

export const TopHeader: React.FC<TopHeaderProps> = ({
  activeTab = 'SOC Dashboard',
  threatScore = 12,
  threatLevel = 'LOW',
  isConnected = true,
}) => {
  const utcTime = useUtcClock();

  let threatColorClass = 'text-[#10B981] border-[#10B981]/30';
  if (threatScore > 75) threatColorClass = 'text-[#DC2626] border-[#DC2626]/40';
  else if (threatScore > 50) threatColorClass = 'text-[#F59E0B] border-[#F59E0B]/40';
  else if (threatScore > 25) threatColorClass = 'text-[#06B6D4] border-[#06B6D4]/30';

  return (
    <header className="h-[52px] bg-[#080B10] border-b border-[#1E2631] flex items-center justify-between px-6 sticky top-0 z-30 select-none overflow-hidden min-w-0">
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
      <div className="flex items-center gap-2 sm:gap-3 shrink-0">
        {/* Threat Level Badge */}
        <div
          className={`px-2.5 sm:px-3 py-1 bg-[#0E131A] border font-mono text-[11px] sm:text-xs font-semibold whitespace-nowrap shrink-0 ${threatColorClass}`}
        >
          ● THREAT LEVEL: {threatLevel} ({threatScore})
        </div>

        {/* Live Wave Indicator */}
        <div className="flex items-center gap-1.5 px-2 sm:px-2.5 py-1 bg-[#0E131A] border border-[#1E2631] shrink-0">
          <span className="w-2 h-2 bg-[#10B981] animate-ping shrink-0"></span>
          <span className="font-mono text-xs font-bold text-[#10B981] whitespace-nowrap">
            {isConnected ? 'LIVE' : 'SYNCING'}
          </span>
        </div>

        {/* Alert Bell */}
        <button
          aria-label="Thông báo"
          className="w-8 h-8 bg-[#0E131A] border border-[#1E2631] text-[#94A3B8] hover:text-white flex items-center justify-center relative cursor-pointer shrink-0"
        >
          <Bell className="w-4 h-4" />
          <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 bg-[#DC2626]"></span>
        </button>

        {/* Sign In Button */}
        <button className="px-2.5 sm:px-3 py-1.5 border border-[#10B981] text-[#10B981] hover:bg-[#10B981] hover:text-[#080B10] font-mono text-xs font-bold flex items-center gap-1.5 transition-colors cursor-pointer whitespace-nowrap shrink-0">
          <ArrowRight className="w-3.5 h-3.5" />
          <span>Sign In</span>
        </button>
      </div>
    </header>
  );
};
