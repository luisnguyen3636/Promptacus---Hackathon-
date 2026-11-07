import React, { useState } from 'react';
import { Server, CheckCircle2, AlertCircle, Search, RefreshCw, Trash2, Video } from 'lucide-react';
import { ICameraDevice } from '../../types/soc.ts';

interface DeviceManagerViewProps {
  cameras: ICameraDevice[];
  onReboot?: (deviceId: string) => void;
  onRefresh?: () => void;
}

export const DeviceManagerView: React.FC<DeviceManagerViewProps> = ({
  cameras,
  onReboot,
  onRefresh,
}) => {
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'ONLINE' | 'OFFLINE'>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [pingStatus, setPingStatus] = useState<{ [id: string]: string }>({});

  const handlePing = async (id: string) => {
    setPingStatus((prev) => ({ ...prev, [id]: 'Đang đo...' }));
    const start = performance.now();
    try {
      const res = await fetch('/api/v1/health');
      const rtt = Math.max(1, Math.round(performance.now() - start));
      if (res.ok) {
        setPingStatus((prev) => ({ ...prev, [id]: `RTT ${rtt}ms (OK)` }));
      } else {
        setPingStatus((prev) => ({ ...prev, [id]: `HTTP ${res.status}` }));
      }
    } catch {
      setPingStatus((prev) => ({ ...prev, [id]: 'TIMEOUT' }));
    }
  };

  const handleDeleteCamera = async (id: string) => {
    try {
      await fetch(`/api/devices/cameras/${encodeURIComponent(id)}`, {
        method: 'DELETE',
      });
      onRefresh?.();
    } catch {
      // Ignore error
    }
  };

  const filteredCameras = cameras.filter((c) => {
    const matchesStatus = statusFilter === 'ALL' || c.status === statusFilter;
    const q = searchQuery.toLowerCase();
    const matchesQuery =
      !q ||
      c.id.toLowerCase().includes(q) ||
      (c.location || c.name || '').toLowerCase().includes(q) ||
      (c.ip || '').toLowerCase().includes(q);
    return matchesStatus && matchesQuery;
  });

  const onlineCount = cameras.filter((c) => c.status === 'ONLINE').length;
  const offlineCount = cameras.length - onlineCount;

  return (
    <div className="space-y-4 select-none min-w-0">
      {/* Top Header Card */}
      <div className="bg-[#0E131A] border border-[#1E2631] px-4 py-3 flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <Server className="w-4 h-4 text-[#10B981]" />
          <span className="font-bold text-xs uppercase tracking-wider text-white">
            DANH MỤC CAMERA THỰC TẾ TỪ SERVER ({cameras.length} CAMERA)
          </span>
          <span className="bg-[#112224] border border-[#10B981] text-[#10B981] font-mono text-[10px] font-bold px-2 py-0.5">
            {onlineCount} ONLINE / {offlineCount} OFFLINE
          </span>
        </div>

        <button
          onClick={() => onRefresh && onRefresh()}
          className="px-3 py-1 bg-[#161E29] border border-[#2D3748] hover:border-[#10B981] text-white font-mono text-xs font-bold cursor-pointer flex items-center gap-1.5"
        >
          <RefreshCw className="w-3.5 h-3.5 text-[#10B981]" />
          <span>ĐỒNG BỘ TỪ KV</span>
        </button>
      </div>

      {/* Filter Tabs and Search Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-[#0E131A] border border-[#1E2631] p-3">
        <div className="flex flex-wrap gap-1">
          {(['ALL', 'ONLINE', 'OFFLINE'] as const).map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1 text-xs font-mono font-bold transition-colors cursor-pointer border ${
                statusFilter === st
                  ? 'bg-[#10B981] text-[#080B10] border-[#10B981]'
                  : 'bg-[#121822] text-[#94A3B8] border-[#1E2631] hover:text-white'
              }`}
            >
              {st === 'ALL' ? 'TẤT CẢ CAMERA' : st}
            </button>
          ))}
        </div>

        <div className="relative min-w-[240px]">
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Tìm mã camera (LAPTOP_01), vị trí..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-[#05070A] border border-[#1E2631] text-xs font-mono pl-8 pr-3 py-1 text-white placeholder-slate-600 focus:outline-none focus:border-[#10B981]"
          />
        </div>
      </div>

      {/* Real Camera Table from Server Payloads */}
      <div className="bg-[#0E131A] border border-[#1E2631] overflow-hidden">
        <div className="overflow-x-auto min-w-0">
          <table className="w-full text-left font-mono text-xs min-w-[850px]">
            <thead className="bg-[#121822] text-[#64748B] border-b border-[#1E2631]">
              <tr>
                <th className="p-3">CAMERA ID</th>
                <th className="p-3">LOCATION (VỊ TRÍ GIÁM SÁT)</th>
                <th className="p-3">MEASURED FPS</th>
                <th className="p-3">FRAME INDEX</th>
                <th className="p-3">HUMAN COUNT</th>
                <th className="p-3">LAST TIMESTAMP</th>
                <th className="p-3">STATUS</th>
                <th className="p-3 text-center">ACTIONS</th>
              </tr>
            </thead>
            <tbody>
              {filteredCameras.length === 0 ? (
                <tr>
                  <td colSpan={8} className="p-8 text-center text-slate-500 font-mono text-xs">
                    <Video className="w-6 h-6 text-slate-600 mx-auto mb-2" />
                    Chưa có thông tin camera nào được gửi từ Server. Khi Server gửi JSON kèm{' '}
                    <code className="text-slate-300">camera_id</code> và{' '}
                    <code className="text-slate-300">location</code>, thiết bị sẽ tự động hiển thị tại đây.
                  </td>
                </tr>
              ) : (
                filteredCameras.map((c) => {
                  const isOnline = c.status === 'ONLINE';
                  return (
                    <tr key={c.id} className="border-b border-[#1E2631] hover:bg-[#161E29]/50">
                      <td className="p-3 font-bold text-[#38BDF8]">{c.id}</td>
                      <td className="p-3 text-white font-semibold">
                        {c.location || c.address || c.name}
                      </td>
                      <td className="p-3 text-[#10B981] font-bold">
                        {c.measuredFps !== undefined ? `${c.measuredFps} FPS` : `${c.fps} FPS`}
                      </td>
                      <td className="p-3 text-slate-300">
                        #{c.frameIndex !== undefined ? c.frameIndex : 0}
                      </td>
                      <td className="p-3 text-[#F59E0B] font-bold">
                        {c.humanCount !== undefined ? `${c.humanCount} người` : '0 người'}
                      </td>
                      <td className="p-3 text-slate-400 text-[11px]">
                        {c.lastTimestamp || 'Đang đồng bộ'}
                      </td>
                      <td className="p-3">
                        <span
                          className={`px-2 py-0.5 border font-bold text-[10px] inline-flex items-center gap-1 ${
                            isOnline
                              ? 'bg-[#112224] border-[#10B981] text-[#10B981]'
                              : 'bg-[#991B1B]/20 border-[#DC2626] text-[#DC2626]'
                          }`}
                        >
                          {isOnline ? (
                            <CheckCircle2 className="w-3 h-3" />
                          ) : (
                            <AlertCircle className="w-3 h-3" />
                          )}
                          <span>{c.status}</span>
                        </span>
                      </td>
                      <td className="p-3 text-center">
                        <div className="inline-flex items-center gap-1.5">
                          <button
                            onClick={() => handlePing(c.id)}
                            className="px-2 py-1 bg-[#161E29] border border-[#1E2631] hover:border-[#10B981] text-[10px] text-slate-300 cursor-pointer"
                          >
                            {pingStatus[c.id] || 'PING'}
                          </button>
                          <button
                            onClick={() => onReboot && onReboot(c.id)}
                            className="px-2 py-1 bg-[#161E29] border border-[#1E2631] hover:border-[#F59E0B] text-[10px] text-slate-300 cursor-pointer"
                          >
                            REBOOT
                          </button>
                          <button
                            onClick={() => handleDeleteCamera(c.id)}
                            title="Xóa camera khỏi bộ nhớ KV"
                            className="px-2 py-1 bg-[#161E29] border border-[#1E2631] hover:border-[#DC2626] text-[10px] text-slate-400 hover:text-[#DC2626] cursor-pointer"
                          >
                            <Trash2 className="w-3 h-3" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
