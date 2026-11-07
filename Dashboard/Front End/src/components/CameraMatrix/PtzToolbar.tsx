import React from 'react';

interface PtzToolbarProps {
  onCommand: (action: 'ZOOM_IN' | 'ZOOM_OUT' | 'PAN' | 'AUTO_FOCUS') => void;
}

export const PtzToolbar: React.FC<PtzToolbarProps> = ({ onCommand }) => {
  return (
    <div className="w-[32px] flex flex-col gap-1 select-none">
      <button
        onClick={() => onCommand('ZOOM_IN')}
        title="Zoom In"
        className="w-[32px] h-[32px] bg-[#161E29] border border-[#1E2631] text-[#94A3B8] hover:text-white hover:border-[#3B82F6] font-mono text-sm font-bold flex items-center justify-center cursor-pointer active:bg-[#3B82F6]"
      >
        +
      </button>
      <button
        onClick={() => onCommand('ZOOM_OUT')}
        title="Zoom Out"
        className="w-[32px] h-[32px] bg-[#161E29] border border-[#1E2631] text-[#94A3B8] hover:text-white hover:border-[#3B82F6] font-mono text-sm font-bold flex items-center justify-center cursor-pointer active:bg-[#3B82F6]"
      >
        -
      </button>
      <button
        onClick={() => onCommand('PAN')}
        title="PTZ Navigation Mode"
        className="w-[32px] h-[32px] bg-[#161E29] border border-[#1E2631] text-[#94A3B8] hover:text-white hover:border-[#3B82F6] font-mono text-[10px] font-bold flex items-center justify-center cursor-pointer active:bg-[#3B82F6]"
      >
        PTZ
      </button>
      <button
        onClick={() => onCommand('AUTO_FOCUS')}
        title="Auto Focus & Scan"
        className="w-[32px] h-[32px] bg-[#161E29] border border-[#1E2631] text-[#94A3B8] hover:text-white hover:border-[#3B82F6] font-mono text-xs flex items-center justify-center cursor-pointer active:bg-[#3B82F6]"
      >
        🔍
      </button>
    </div>
  );
};
