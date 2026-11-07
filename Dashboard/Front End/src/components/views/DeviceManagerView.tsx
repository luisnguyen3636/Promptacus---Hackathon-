import React, { useState } from 'react';
import { Server, CheckCircle2, AlertCircle, Plus, X, Search } from 'lucide-react';
import { ICameraDevice } from '../../types/soc.ts';

interface DeviceItem {
  id: string;
  name: string;
  type: string;
  category: 'PTZ CAMERAS' | 'BULLET CAMERAS' | 'SWITCHES' | 'STORAGE & SERVERS';
  ip: string;
  mac: string;
  poe: string;
  firmware: string;
  status: 'ONLINE' | 'OFFLINE' | 'DEGRADED';
}

interface DeviceManagerViewProps {
  cameras: ICameraDevice[];
  onReboot?: (deviceId: string) => void;
}

export const DeviceManagerView: React.FC<DeviceManagerViewProps> = ({ cameras, onReboot }) => {
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [pingStatus, setPingStatus] = useState<{ [id: string]: string }>({});
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);

  // New device form state
  const [newDevName, setNewDevName] = useState<string>('');
  const [newDevType, setNewDevType] = useState<string>('PTZ CAMERA');
  const [newDevIp, setNewDevIp] = useState<string>('');
  const [newDevMac, setNewDevMac] = useState<string>('');
  const [newDevPoe, setNewDevPoe] = useState<string>('15W');

  const [deviceList, setDeviceList] = useState<DeviceItem[]>([
    ...cameras.map((c, i) => ({
      id: c.id,
      name: c.name,
      type: 'PTZ 4K AI Camera',
      category: 'PTZ CAMERAS' as const,
      ip: c.ip,
      mac: `00:1A:2B:3C:4D:0${i + 1}`,
      poe: `${12 + i * 2.5}W`,
      firmware: 'v4.2.1-sec',
      status: c.status
    })),
    {
      id: 'sw_core_01',
      name: 'PoE Core Switch 48P',
      type: 'Managed PoE+ Switch',
      category: 'SWITCHES' as const,
      ip: '10.0.1.2',
      mac: '00:1A:2B:3C:88:FF',
      poe: '410W',
      firmware: 'v6.1.0-build',
      status: 'ONLINE'
    },
    {
      id: 'nvr_primary_01',
      name: 'SAN NVR Storage RAID-6',
      type: 'Hardware Storage Array',
      category: 'STORAGE & SERVERS' as const,
      ip: '10.0.3.5',
      mac: '00:1A:2B:3C:99:AA',
      poe: 'N/A',
      firmware: 'v2.8.4-firm',
      status: 'ONLINE'
    },
    {
      id: 'cam_offline_01',
      name: 'North Gate Backup',
      type: 'Fixed 4K Bullet IR',
      category: 'BULLET CAMERAS' as const,
      ip: '192.168.16.205',
      mac: '00:1A:2B:3C:77:11',
      poe: '0W',
      firmware: 'v4.1.9-sec',
      status: 'OFFLINE'
    }
  ]);

  const handlePing = (id: string) => {
    setPingStatus(prev => ({ ...prev, [id]: 'Pinging...' }));
    setTimeout(() => {
      setPingStatus(prev => ({ ...prev, [id]: 'RTT 1.4ms (OK)' }));
    }, 400);
  };

  const handleAddDevice = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDevName || !newDevIp) return;

    let cat: DeviceItem['category'] = 'PTZ CAMERAS';
    if (newDevType.includes('Bullet')) cat = 'BULLET CAMERAS';
    else if (newDevType.includes('Switch')) cat = 'SWITCHES';
    else if (newDevType.includes('Storage') || newDevType.includes('Server')) cat = 'STORAGE & SERVERS';

    const newDevice: DeviceItem = {
      id: `dev_${Date.now().toString().slice(-4)}`,
      name: newDevName,
      type: newDevType,
      category: cat,
      ip: newDevIp,
      mac: newDevMac || `00:1A:2B:3C:${Math.floor(10 + Math.random() * 89)}:${Math.floor(10 + Math.random() * 89)}`,
      poe: newDevPoe,
      firmware: 'v1.0.0-std',
      status: 'ONLINE'
    };

    setDeviceList(prev => [newDevice, ...prev]);
    setIsModalOpen(false);
    setNewDevName('');
    setNewDevIp('');
    setNewDevMac('');
  };

  const filteredDevices = deviceList.filter(d => {
    const matchesCategory = selectedCategory === 'ALL' || d.category === selectedCategory;
    const matchesQuery = !searchQuery || 
      d.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      d.ip.includes(searchQuery) ||
      d.id.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesQuery;
  });

  const categories = ['ALL', 'PTZ CAMERAS', 'BULLET CAMERAS', 'SWITCHES', 'STORAGE & SERVERS'];

  const onlineCount = deviceList.filter(d => d.status === 'ONLINE').length;
  const offlineCount = deviceList.length - onlineCount;

  return (
    <div className="space-y-4 select-none min-w-0">
      {/* Top Header Card */}
      <div className="bg-[#0E131A] border border-[#1E2631] px-4 py-3 flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <Server className="w-4 h-4 text-[#10B981]" />
          <span className="font-bold text-xs uppercase tracking-wider text-white">
            PHYSICAL & EDGE HARDWARE INVENTORY ({deviceList.length} TOTAL DEVICES)
          </span>
          <span className="bg-[#112224] border border-[#10B981] text-[#10B981] font-mono text-[10px] font-bold px-2 py-0.5">
            {onlineCount} ONLINE / {offlineCount} OFFLINE
          </span>
        </div>

        <button
          onClick={() => setIsModalOpen(true)}
          className="px-3 py-1 bg-[#10B981] text-[#080B10] font-mono text-xs font-bold hover:bg-[#10B981]/90 cursor-pointer flex items-center gap-1.5"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>+ ADD NEW DEVICE</span>
        </button>
      </div>

      {/* Filter Tabs and Search Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-[#0E131A] border border-[#1E2631] p-3">
        {/* Category Tabs */}
        <div className="flex flex-wrap gap-1">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-3 py-1 text-xs font-mono font-bold transition-colors cursor-pointer border ${
                selectedCategory === cat
                  ? 'bg-[#10B981] text-[#080B10] border-[#10B981]'
                  : 'bg-[#121822] text-[#94A3B8] border-[#1E2631] hover:text-white'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* Search Field */}
        <div className="relative min-w-[220px]">
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search device name, IP, ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-[#05070A] border border-[#1E2631] text-xs font-mono pl-8 pr-3 py-1 text-white placeholder-slate-600 focus:outline-none focus:border-[#10B981]"
          />
        </div>
      </div>

      {/* Device Table */}
      <div className="bg-[#0E131A] border border-[#1E2631] overflow-hidden">
        <div className="overflow-x-auto min-w-0">
          <table className="w-full text-left font-mono text-xs min-w-[800px]">
            <thead className="bg-[#121822] text-[#64748B] border-b border-[#1E2631]">
              <tr>
                <th className="p-3">ID</th>
                <th className="p-3">DEVICE NAME</th>
                <th className="p-3">CATEGORY / TYPE</th>
                <th className="p-3">IP ADDRESS</th>
                <th className="p-3">MAC ADDRESS</th>
                <th className="p-3">PoE</th>
                <th className="p-3">STATUS</th>
                <th className="p-3 text-center">ACTIONS</th>
              </tr>
            </thead>
            <tbody>
              {filteredDevices.length === 0 ? (
                <tr>
                  <td colSpan={8} className="p-6 text-center text-slate-500 font-mono text-xs">
                    No devices match the selected category or search query.
                  </td>
                </tr>
              ) : (
                filteredDevices.map((d) => {
                  const isOnline = d.status === 'ONLINE';
                  const isDegraded = d.status === 'DEGRADED';
                  return (
                    <tr key={d.id} className="border-b border-[#1E2631] hover:bg-[#161E29]/50">
                      <td className="p-3 font-bold text-slate-300">{d.id}</td>
                      <td className="p-3 text-white font-semibold">{d.name}</td>
                      <td className="p-3">
                        <div className="text-slate-300 text-[11px] font-bold">{d.category}</div>
                        <div className="text-slate-500 text-[10px]">{d.type}</div>
                      </td>
                      <td className="p-3 text-[#3B82F6]">{d.ip}</td>
                      <td className="p-3 text-slate-400">{d.mac}</td>
                      <td className="p-3 text-slate-300">{d.poe}</td>
                      <td className="p-3">
                        <span className={`px-2 py-0.5 border font-bold text-[10px] inline-flex items-center gap-1 ${
                          isOnline
                            ? 'bg-[#112224] border-[#10B981] text-[#10B981]'
                            : isDegraded
                            ? 'bg-[#78350F]/20 border-[#F59E0B] text-[#F59E0B]'
                            : 'bg-[#991B1B]/20 border-[#DC2626] text-[#DC2626]'
                        }`}>
                          {isOnline ? <CheckCircle2 className="w-3 h-3" /> : <AlertCircle className="w-3 h-3" />}
                          <span>{d.status}</span>
                        </span>
                      </td>
                      <td className="p-3 text-center">
                        <div className="inline-flex items-center gap-2">
                          <button
                            onClick={() => handlePing(d.id)}
                            className="px-2 py-1 bg-[#161E29] border border-[#1E2631] hover:border-[#10B981] text-[10px] text-slate-300 cursor-pointer"
                          >
                            {pingStatus[d.id] || 'PING'}
                          </button>
                          <button
                            onClick={() => onReboot && onReboot(d.id)}
                            className="px-2 py-1 bg-[#161E29] border border-[#1E2631] hover:border-[#F59E0B] text-[10px] text-slate-300 cursor-pointer"
                          >
                            REBOOT
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

      {/* Modal Add New Device */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
          <div className="bg-[#0E131A] border-2 border-[#10B981] w-full max-w-md p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-[#1E2631] pb-3">
              <div className="flex items-center gap-2 text-white font-bold text-xs uppercase">
                <Server className="w-4 h-4 text-[#10B981]" />
                <span>ENROLL NEW PHYSICAL / EDGE HARDWARE</span>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-slate-400 hover:text-white cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleAddDevice} className="space-y-3 font-mono text-xs">
              <div>
                <label className="block text-slate-400 mb-1 text-[11px]">DEVICE NAME</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. South Perimeter PTZ 05"
                  value={newDevName}
                  onChange={(e) => setNewDevName(e.target.value)}
                  className="w-full bg-[#05070A] border border-[#1E2631] p-2 text-white focus:outline-none focus:border-[#10B981]"
                />
              </div>

              <div>
                <label className="block text-slate-400 mb-1 text-[11px]">HARDWARE TYPE</label>
                <select
                  value={newDevType}
                  onChange={(e) => setNewDevType(e.target.value)}
                  className="w-full bg-[#05070A] border border-[#1E2631] p-2 text-white focus:outline-none focus:border-[#10B981]"
                >
                  <option value="PTZ 4K AI Camera">PTZ 4K AI Camera</option>
                  <option value="Fixed 4K Bullet IR">Fixed 4K Bullet IR</option>
                  <option value="PoE+ Managed Switch 24P">PoE+ Managed Switch 24P</option>
                  <option value="Edge AI Inference Box (Orin)">Edge AI Inference Box (Orin)</option>
                  <option value="SAN NVR Storage RAID-6">SAN NVR Storage RAID-6</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-400 mb-1 text-[11px]">IP ADDRESS (STATIC / DHCP)</label>
                <input
                  type="text"
                  required
                  placeholder="192.168.16.155"
                  value={newDevIp}
                  onChange={(e) => setNewDevIp(e.target.value)}
                  className="w-full bg-[#05070A] border border-[#1E2631] p-2 text-white focus:outline-none focus:border-[#10B981]"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-400 mb-1 text-[11px]">MAC ADDRESS</label>
                  <input
                    type="text"
                    placeholder="00:1A:2B:3C:D4:5E"
                    value={newDevMac}
                    onChange={(e) => setNewDevMac(e.target.value)}
                    className="w-full bg-[#05070A] border border-[#1E2631] p-2 text-white focus:outline-none focus:border-[#10B981]"
                  />
                </div>
                <div>
                  <label className="block text-slate-400 mb-1 text-[11px]">PoE DRAW</label>
                  <input
                    type="text"
                    value={newDevPoe}
                    onChange={(e) => setNewDevPoe(e.target.value)}
                    className="w-full bg-[#05070A] border border-[#1E2631] p-2 text-white focus:outline-none focus:border-[#10B981]"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-[#1E2631]">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-3 py-1.5 bg-[#121822] border border-[#1E2631] text-slate-300 text-xs font-mono cursor-pointer hover:bg-[#161E29]"
                >
                  CANCEL
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 bg-[#10B981] text-[#080B10] text-xs font-mono font-bold cursor-pointer hover:bg-[#10B981]/90"
                >
                  PROVISION & ENROLL
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
