import React, { useState } from 'react';
import { Settings, Shield, User, Bell, HardDrive, Send } from 'lucide-react';

interface SettingsViewProps {
  operatorId?: string;
}

export const SettingsView: React.FC<SettingsViewProps> = ({
  operatorId = 'OP-VN-PSOC-804',
}) => {
  const [criticalThreshold, setCriticalThreshold] = useState<number>(75);
  const [dispatchWebhook, setDispatchWebhook] = useState<string>(
    'https://soc-dispatch.police.gov.vn/api/v1/alert'
  );
  const [preBufferSeconds, setPreBufferSeconds] = useState<number>(10);
  const [postBufferSeconds, setPostBufferSeconds] = useState<number>(10);
  const [isSaved, setIsSaved] = useState<boolean>(false);

  const handleSave = () => {
    setIsSaved(true);
    setTimeout(() => setIsSaved(false), 2500);
  };

  return (
    <div className="space-y-4 select-none min-w-0 max-w-4xl">
      {/* Header Khối */}
      <div className="bg-[#0E131A] border border-[#1E2631] px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Settings className="w-4 h-4 text-[#10B981]" />
          <span className="font-bold text-xs uppercase tracking-wider text-white">
            PSOC PLATFORM & OPERATIONAL CONFIGURATION
          </span>
        </div>
        <button
          onClick={handleSave}
          className="px-4 py-1.5 bg-[#10B981] text-[#080B10] font-mono text-xs font-bold hover:bg-[#10B981]/90 cursor-pointer"
        >
          {isSaved ? 'SAVED (APPLIED)' : 'SAVE CONFIGURATION'}
        </button>
      </div>

      {/* Nhóm 1: Thông tin Vận hành viên (Operator Profile) */}
      <div className="bg-[#0E131A] border border-[#1E2631] p-4 space-y-3">
        <div className="flex items-center gap-2 border-b border-[#1E2631] pb-2">
          <User className="w-4 h-4 text-[#3B82F6]" />
          <span className="font-bold text-xs text-white uppercase">ACTIVE PSOC OPERATOR PROFILE</span>
        </div>
        <div className="grid grid-cols-2 gap-4 font-mono text-xs">
          <div>
            <label className="text-slate-400 block mb-1">OPERATOR ID:</label>
            <input
              type="text"
              readOnly
              value={operatorId}
              className="w-full bg-[#161E29] border border-[#1E2631] p-2 text-white font-bold"
            />
          </div>
          <div>
            <label className="text-slate-400 block mb-1">SHIFT ROTATION:</label>
            <input
              type="text"
              readOnly
              value="Shift 2 · 14:00 - 22:00 UTC (Active)"
              className="w-full bg-[#161E29] border border-[#1E2631] p-2 text-[#10B981]"
            />
          </div>
        </div>
      </div>

      {/* Nhóm 2: Ngưỡng Rủi ro & Báo động (Alert Thresholds) */}
      <div className="bg-[#0E131A] border border-[#1E2631] p-4 space-y-3">
        <div className="flex items-center gap-2 border-b border-[#1E2631] pb-2">
          <Bell className="w-4 h-4 text-[#F59E0B]" />
          <span className="font-bold text-xs text-white uppercase">RISK ESCALATION THRESHOLDS</span>
        </div>
        <div className="space-y-3 font-mono text-xs">
          <div>
            <div className="flex justify-between mb-1">
              <span className="text-slate-300">Critical Threat Escalation Trigger:</span>
              <span className="text-[#DC2626] font-bold">Threat Score &gt;= {criticalThreshold}</span>
            </div>
            <input
              type="range"
              min="50"
              max="95"
              value={criticalThreshold}
              onChange={(e) => setCriticalThreshold(Number(e.target.value))}
              className="w-full accent-[#DC2626] cursor-pointer"
            />
          </div>
        </div>
      </div>

      {/* Nhóm 3: Evidence Rolling Buffer Configuration */}
      <div className="bg-[#0E131A] border border-[#1E2631] p-4 space-y-3">
        <div className="flex items-center gap-2 border-b border-[#1E2631] pb-2">
          <HardDrive className="w-4 h-4 text-[#06B6D4]" />
          <span className="font-bold text-xs text-white uppercase">EVIDENCE ROLLING BUFFER LIMITS</span>
        </div>
        <div className="grid grid-cols-2 gap-4 font-mono text-xs">
          <div>
            <label className="text-slate-400 block mb-1">PRE-EVENT BUFFER DURATION:</label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                value={preBufferSeconds}
                onChange={(e) => setPreBufferSeconds(Number(e.target.value))}
                className="w-full bg-[#161E29] border border-[#1E2631] p-2 text-white"
              />
              <span className="text-slate-500">Seconds</span>
            </div>
          </div>
          <div>
            <label className="text-slate-400 block mb-1">POST-EVENT BUFFER DURATION:</label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                value={postBufferSeconds}
                onChange={(e) => setPostBufferSeconds(Number(e.target.value))}
                className="w-full bg-[#161E29] border border-[#1E2631] p-2 text-white"
              />
              <span className="text-slate-500">Seconds</span>
            </div>
          </div>
        </div>
      </div>

      {/* Nhóm 4: Operational Dispatch Endpoint (CD-04) */}
      <div className="bg-[#0E131A] border border-[#1E2631] p-4 space-y-3">
        <div className="flex items-center gap-2 border-b border-[#1E2631] pb-2">
          <Send className="w-4 h-4 text-[#10B981]" />
          <span className="font-bold text-xs text-white uppercase">AUTHORITY DISPATCH TARGET (REST/WEBHOOK)</span>
        </div>
        <div className="font-mono text-xs">
          <label className="text-slate-400 block mb-1">EMERGENCY DISPATCH WEBHOOK URL:</label>
          <input
            type="text"
            value={dispatchWebhook}
            onChange={(e) => setDispatchWebhook(e.target.value)}
            className="w-full bg-[#161E29] border border-[#1E2631] p-2 text-[#3B82F6]"
          />
          <div className="text-[10px] text-slate-500 mt-1">
            * Strictly triggered ONLY when Operator completes verification [CD-04].
          </div>
        </div>
      </div>
    </div>
  );
};
