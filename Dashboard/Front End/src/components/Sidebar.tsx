import React from 'react';
import {
  Shield,
  LayoutDashboard,
  Video,
  Network,
  AlertTriangle,
  Activity,
  Cpu,
  Server,
  Settings
} from 'lucide-react';

interface SidebarProps {
  activeTab?: string;
  onSelectTab?: (tab: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab = 'SOC Dashboard',
  onSelectTab
}) => {
  const operations = [
    { name: 'SOC Dashboard', icon: LayoutDashboard },
    { name: 'Live Video Wall', icon: Video },
    { name: 'Threat Intelligence', icon: AlertTriangle, badge: '5' },
    { name: 'Incident Feed', icon: Activity },
    { name: 'AI Analyzer', icon: Cpu },
    { name: 'Device Manager', icon: Server },
  ];

  return (
    <aside className="w-[240px] bg-[#080B10] border-r border-[#1E2631] h-screen fixed top-0 left-0 z-40 flex flex-col select-none overflow-hidden">
      {/* Cụm Logo */}
      <div className="h-[52px] flex items-center px-4 border-b border-[#1E2631] shrink-0">
        <div className="w-6 h-6 border-2 border-[#10B981] flex items-center justify-center mr-3 bg-[#0A1A17] shrink-0">
          <Shield className="w-3.5 h-3.5 text-[#10B981]" />
        </div>
        <div className="min-w-0 truncate">
          <div className="font-bold text-sm tracking-wide text-[#10B981] truncate">CYBERGUARD</div>
          <div className="text-[10px] text-[#64748B] font-mono tracking-wider truncate">AI · SOC v2.1</div>
        </div>
      </div>

      {/* Nhóm OPERATIONS (7 mục chuẩn xác theo SPEC) */}
      <div className="px-4 pt-4 pb-2 text-[10px] font-mono text-[#64748B] tracking-wider uppercase shrink-0">
        OPERATIONS
      </div>
      <nav className="flex-1 space-y-0.5 overflow-y-auto px-0">
        {operations.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.name;

          return (
            <button
              key={item.name}
              onClick={() => onSelectTab && onSelectTab(item.name)}
              className={`w-full flex items-center gap-3 px-4 py-2.5 text-left text-xs transition-colors duration-150 min-w-0 ${
                isActive
                  ? 'bg-[#112224] text-[#10B981] font-semibold border-l-[3px] border-[#10B981]'
                  : 'text-[#94A3B8] hover:bg-[#0E131A] hover:text-white border-l-[3px] border-transparent'
              }`}
            >
              <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-[#10B981]' : 'text-slate-400'}`} />
              <span className="flex-1 truncate" title={item.name}>{item.name}</span>
              {item.badge && (
                <span className="bg-[#991B1B] border border-[#DC2626] text-white font-mono text-[10px] font-bold px-1.5 py-0.2 shrink-0 ml-auto">
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}

        {/* Phân cách nhóm SYSTEM */}
        <div className="pt-3 pb-1 border-t border-[#1E2631] my-2 mx-4">
          <span className="text-[10px] font-mono text-[#64748B] uppercase tracking-wider">
            SYSTEM
          </span>
        </div>

        {/* Settings */}
        <button
          onClick={() => onSelectTab && onSelectTab('Settings')}
          className="w-full flex items-center gap-3 px-4 py-2.5 text-left text-xs text-[#94A3B8] hover:bg-[#0E131A] hover:text-white border-l-[3px] border-transparent transition-colors min-w-0"
        >
          <Settings className="w-4 h-4 text-slate-400 shrink-0" />
          <span className="truncate">Settings</span>
        </button>
      </nav>

      {/* Hộp Trạng thái Đáy (SYSTEM ACTIVE) */}
      <div className="m-4 p-3 bg-[#0E131A] border border-[#1E2631] shrink-0">
        <div className="flex items-center gap-2 mb-1.5">
          <span className="w-2 h-2 bg-[#10B981] animate-pulse shrink-0"></span>
          <span className="font-bold text-[11px] text-[#10B981] tracking-wide truncate">SYSTEM ACTIVE</span>
        </div>
        <div className="text-[10px] font-mono text-[#94A3B8] truncate">
          Threat DB: <span className="text-slate-300">v2024.12</span>
        </div>
        <div className="text-[10px] font-mono text-white font-bold truncate">Engine: Online</div>
      </div>
    </aside>
  );
};
