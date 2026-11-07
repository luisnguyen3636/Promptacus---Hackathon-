import React from 'react';

interface SegmentedBarProps {
  score: number;
}

export const SegmentedBar: React.FC<SegmentedBarProps> = ({ score }) => {
  const activeSegmentsCount = Math.max(1, Math.round((score / 100) * 16));

  let activeBg = 'bg-[#10B981]';
  if (score > 75) activeBg = 'bg-[#DC2626]';
  else if (score > 50) activeBg = 'bg-[#F59E0B]';
  else if (score > 25) activeBg = 'bg-[#06B6D4]';

  return (
    <div className="grid grid-cols-16 gap-[2px] sm:gap-1 h-[18px] my-3 select-none w-full min-w-0 overflow-hidden">
      {Array.from({ length: 16 }).map((_, index) => {
        const isActive = index < activeSegmentsCount;
        return (
          <div
            key={index}
            className={`h-full min-w-0 w-full transition-colors duration-200 ${
              isActive ? activeBg : 'bg-[#1E2631]'
            }`}
          />
        );
      })}
    </div>
  );
};
