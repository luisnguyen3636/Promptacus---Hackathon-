import React from 'react';
import { ISocMetrics } from '../../types/soc.ts';
import { SegmentedBar } from './SegmentedBar.tsx';
import { TechSpecGrid } from './TechSpecGrid.tsx';

interface ThreatScoreModuleProps {
  score: number;
  status: string;
  metrics: ISocMetrics;
}

export const ThreatScoreModule: React.FC<ThreatScoreModuleProps> = ({
  score,
  status,
  metrics,
}) => {
  let scoreColor = 'text-[#10B981]';
  if (score > 75) scoreColor = 'text-[#DC2626]';
  else if (score > 50) scoreColor = 'text-[#F59E0B]';
  else if (score > 25) scoreColor = 'text-[#06B6D4]';

  return (
    <div className="bg-[#0E131A] border border-[#1E2631] flex flex-col justify-between h-full select-none">
      {/* Phần trên: Điểm rủi ro hệ thống */}
      <div className="p-5 text-center flex-1 flex flex-col justify-center">
        <h3 className="font-bold text-sm uppercase tracking-wider text-[#E2E8F0]">
          Threat Score
        </h3>
        <p className="text-xs text-[#64748B] mt-0.5">System Risk Level</p>

        {/* Thanh Segmented Bar (16 ô chữ nhật) */}
        <SegmentedBar score={score} />

        {/* Con số trung tâm */}
        <div className="flex items-baseline justify-center gap-1.5 my-1">
          <span className={`font-mono text-4xl font-extrabold ${scoreColor}`}>
            {score}
          </span>
          <span className="font-mono text-base text-slate-500 font-semibold">/ 100</span>
        </div>

        {/* Nhãn trạng thái */}
        <div className={`font-mono text-sm font-bold tracking-widest uppercase ${scoreColor}`}>
          {status}
        </div>
      </div>

      {/* Phần dưới: Bảng lưới 2x2 Thông số Kỹ thuật Hạ tầng */}
      <TechSpecGrid metrics={metrics} />
    </div>
  );
};
