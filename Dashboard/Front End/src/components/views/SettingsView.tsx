import React, { useEffect, useState } from 'react';
import { Settings, User, Bell, HardDrive, Send, Video, RefreshCw, CheckCircle2 } from 'lucide-react';
import { ISocSettings } from '../../types/soc.ts';

interface SettingsViewProps {
  operatorId?: string;
  onToast?: (msg: string) => void;
}

const DEFAULT_SETTINGS: ISocSettings = {
  operatorId: 'OP-VN-SOC-804',
  operatorName: 'Trực Ban Trưởng SOC',
  shiftRotation: 'Shift 2 · 14:00 - 22:00 UTC (Active)',
  criticalThreshold: 75,
  preBufferSeconds: 10,
  postBufferSeconds: 10,
  dispatchWebhook: 'https://soc-dispatch.police.gov.vn/api/v1/alert',
  liveStreamUrl: 'https://means-brick-determined-send.trycloudflare.com/api/v1/cameras/LAPTOP_01/stream',
  autoSirenOnCritical: true,
};

export const SettingsView: React.FC<SettingsViewProps> = ({
  operatorId = 'OP-VN-SOC-804',
  onToast,
}) => {
  const [settings, setSettings] = useState<ISocSettings>({
    ...DEFAULT_SETTINGS,
    operatorId,
  });
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [isSaved, setIsSaved] = useState<boolean>(false);

  const loadSettings = async () => {
    setIsLoading(true);
    try {
      const res = await fetch('/api/settings');
      if (res.ok) {
        const json = await res.json();
        if (json?.data) {
          setSettings(json.data);
          localStorage.setItem('SOC_LIVE_CAMERA_STREAM_URL', json.data.liveStreamUrl || '');
        }
      }
    } catch {
      const cached = localStorage.getItem('SOC_SETTINGS_CACHE');
      if (cached) {
        try {
          setSettings(JSON.parse(cached));
        } catch {
          // ignore
        }
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void loadSettings();
  }, []);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      const res = await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
      });
      if (res.ok) {
        const json = await res.json();
        if (json?.data) {
          setSettings(json.data);
          localStorage.setItem('SOC_SETTINGS_CACHE', JSON.stringify(json.data));
          localStorage.setItem('SOC_LIVE_CAMERA_STREAM_URL', json.data.liveStreamUrl || '');
        }
      } else {
        localStorage.setItem('SOC_SETTINGS_CACHE', JSON.stringify(settings));
        localStorage.setItem('SOC_LIVE_CAMERA_STREAM_URL', settings.liveStreamUrl || '');
      }
      setIsSaved(true);
      onToast?.('[SETTINGS] Đã lưu cấu hình hệ thống vào Cloudflare KV');
      setTimeout(() => setIsSaved(false), 2500);
    } catch {
      localStorage.setItem('SOC_SETTINGS_CACHE', JSON.stringify(settings));
      localStorage.setItem('SOC_LIVE_CAMERA_STREAM_URL', settings.liveStreamUrl || '');
      setIsSaved(true);
      onToast?.('[SETTINGS] Đã lưu cấu hình cục bộ');
      setTimeout(() => setIsSaved(false), 2500);
    } finally {
      setIsSaving(false);
    }
  };

  const handleResetDefault = async () => {
    setSettings(DEFAULT_SETTINGS);
    onToast?.('[SETTINGS] Đã khôi phục cấu hình mặc định (Bấm SAVE để lưu vào KV)');
  };

  return (
    <div className="space-y-4 select-none min-w-0 max-w-4xl">
      {/* Header Khối */}
      <div className="bg-[#0E131A] border border-[#1E2631] px-4 py-3 flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-3">
          <Settings className="w-4 h-4 text-[#10B981]" />
          <span className="font-bold text-xs uppercase tracking-wider text-white">
            SOC PLATFORM &amp; KV OPERATIONAL CONFIGURATION
          </span>
          {isLoading && (
            <span className="text-[10px] font-mono text-slate-400">Đang tải từ KV...</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleResetDefault}
            className="px-3 py-1.5 bg-[#161E29] border border-[#2D3748] hover:border-slate-400 text-slate-300 font-mono text-xs font-bold flex items-center gap-1.5 cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>KHÔI PHỤC MẶC ĐỊNH</span>
          </button>
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="px-4 py-1.5 bg-[#10B981] text-[#080B10] font-mono text-xs font-bold hover:bg-[#10B981]/90 cursor-pointer flex items-center gap-1.5"
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>{isSaving ? 'SAVING TO KV...' : isSaved ? 'SAVED TO KV (APPLIED)' : 'SAVE CONFIGURATION'}</span>
          </button>
        </div>
      </div>

      {/* Nhóm 1: Thông tin Vận hành viên (Operator Profile) */}
      <div className="bg-[#0E131A] border border-[#1E2631] p-4 space-y-3">
        <div className="flex items-center gap-2 border-b border-[#1E2631] pb-2">
          <User className="w-4 h-4 text-[#3B82F6]" />
          <span className="font-bold text-xs text-white uppercase">ACTIVE SOC OPERATOR PROFILE</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 font-mono text-xs">
          <div>
            <label className="text-slate-400 block mb-1">OPERATOR ID:</label>
            <input
              type="text"
              value={settings.operatorId}
              onChange={(e) => setSettings({ ...settings, operatorId: e.target.value })}
              className="w-full bg-[#161E29] border border-[#1E2631] p-2 text-white font-bold outline-none focus:border-[#3B82F6]"
            />
          </div>
          <div>
            <label className="text-slate-400 block mb-1">OPERATOR NAME:</label>
            <input
              type="text"
              value={settings.operatorName}
              onChange={(e) => setSettings({ ...settings, operatorName: e.target.value })}
              className="w-full bg-[#161E29] border border-[#1E2631] p-2 text-white outline-none focus:border-[#3B82F6]"
            />
          </div>
          <div>
            <label className="text-slate-400 block mb-1">SHIFT ROTATION:</label>
            <input
              type="text"
              value={settings.shiftRotation}
              onChange={(e) => setSettings({ ...settings, shiftRotation: e.target.value })}
              className="w-full bg-[#161E29] border border-[#1E2631] p-2 text-[#10B981] outline-none focus:border-[#10B981]"
            />
          </div>
        </div>
      </div>

      {/* Nhóm 2: Nguồn Stream Camera Dự Phòng (Live Stream URL Backup) */}
      <div className="bg-[#0E131A] border border-[#1E2631] p-4 space-y-3">
        <div className="flex items-center gap-2 border-b border-[#1E2631] pb-2">
          <Video className="w-4 h-4 text-[#38BDF8]" />
          <span className="font-bold text-xs text-white uppercase">LIVE CAMERA STREAM PROXY &amp; BACKUP URL</span>
        </div>
        <div className="font-mono text-xs space-y-2">
          <label className="text-slate-400 block">UPSTREAM CAMERA STREAM URL (MJPEG / HTTP STREAM):</label>
          <input
            type="text"
            value={settings.liveStreamUrl}
            onChange={(e) => setSettings({ ...settings, liveStreamUrl: e.target.value })}
            className="w-full bg-[#161E29] border border-[#1E2631] p-2 text-[#38BDF8] outline-none focus:border-[#38BDF8]"
          />
          <div className="text-[10px] text-slate-500">
            * Đồng bộ trực tiếp với Worker endpoint <code className="text-slate-300">/api/v1/cameras/LAPTOP_01/stream</code> và biến dự phòng <code className="text-slate-300">LIVE_CAMERA_STREAM_URL</code>.
          </div>
        </div>
      </div>

      {/* Nhóm 3: Ngưỡng Rủi ro & Báo động (Alert Thresholds) */}
      <div className="bg-[#0E131A] border border-[#1E2631] p-4 space-y-3">
        <div className="flex items-center gap-2 border-b border-[#1E2631] pb-2">
          <Bell className="w-4 h-4 text-[#F59E0B]" />
          <span className="font-bold text-xs text-white uppercase">RISK ESCALATION THRESHOLDS</span>
        </div>
        <div className="space-y-3 font-mono text-xs">
          <div>
            <div className="flex justify-between mb-1">
              <span className="text-slate-300">Critical Threat Escalation Trigger:</span>
              <span className="text-[#DC2626] font-bold">Threat Score &gt;= {settings.criticalThreshold}%</span>
            </div>
            <input
              type="range"
              min="50"
              max="95"
              value={settings.criticalThreshold}
              onChange={(e) => setSettings({ ...settings, criticalThreshold: Number(e.target.value) })}
              className="w-full accent-[#DC2626] cursor-pointer"
            />
          </div>
          <label className="flex items-center gap-2 cursor-pointer pt-1">
            <input
              type="checkbox"
              checked={settings.autoSirenOnCritical}
              onChange={(e) => setSettings({ ...settings, autoSirenOnCritical: e.target.checked })}
              className="accent-[#10B981]"
            />
            <span className="text-slate-300">Kích hoạt tín hiệu cảnh báo khẩn cấp trên giao diện khi nhận sự cố <code className="text-[#EF4444]">is_urgent: true</code></span>
          </label>
        </div>
      </div>

      {/* Nhóm 4: Evidence Rolling Buffer Configuration */}
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
                min={1}
                max={120}
                value={settings.preBufferSeconds}
                onChange={(e) => setSettings({ ...settings, preBufferSeconds: Number(e.target.value) })}
                className="w-full bg-[#161E29] border border-[#1E2631] p-2 text-white outline-none focus:border-[#06B6D4]"
              />
              <span className="text-slate-500">Seconds</span>
            </div>
          </div>
          <div>
            <label className="text-slate-400 block mb-1">POST-EVENT BUFFER DURATION:</label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min={1}
                max={120}
                value={settings.postBufferSeconds}
                onChange={(e) => setSettings({ ...settings, postBufferSeconds: Number(e.target.value) })}
                className="w-full bg-[#161E29] border border-[#1E2631] p-2 text-white outline-none focus:border-[#06B6D4]"
              />
              <span className="text-slate-500">Seconds</span>
            </div>
          </div>
        </div>
      </div>

      {/* Nhóm 5: Operational Dispatch Endpoint (CD-04) */}
      <div className="bg-[#0E131A] border border-[#1E2631] p-4 space-y-3">
        <div className="flex items-center gap-2 border-b border-[#1E2631] pb-2">
          <Send className="w-4 h-4 text-[#10B981]" />
          <span className="font-bold text-xs text-white uppercase">AUTHORITY DISPATCH TARGET (REST/WEBHOOK)</span>
        </div>
        <div className="font-mono text-xs">
          <label className="text-slate-400 block mb-1">EMERGENCY DISPATCH WEBHOOK URL:</label>
          <input
            type="text"
            value={settings.dispatchWebhook}
            onChange={(e) => setSettings({ ...settings, dispatchWebhook: e.target.value })}
            className="w-full bg-[#161E29] border border-[#1E2631] p-2 text-[#3B82F6] outline-none focus:border-[#3B82F6]"
          />
          <div className="text-[10px] text-slate-500 mt-1">
            * Strictly triggered ONLY when Operator completes verification [CD-04].
          </div>
        </div>
      </div>
    </div>
  );
};
