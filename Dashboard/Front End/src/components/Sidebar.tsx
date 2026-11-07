import React from 'react';
import {
  Shield,
  LayoutDashboard,
  AlertTriangle,
  Activity,
  Server,
  Settings
} from 'lucide-react';

interface SidebarProps {
  activeTab?: string;
  onSelectTab?: (tab: string) => void;
  activeThreatCount?: number;
  cameraCount?: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab = 'SOC Dashboard',
  onSelectTab,
  activeThreatCount = 0,
  cameraCount = 0
}) => {
  const operations = [
    { name: 'SOC Dashboard', icon: LayoutDashboard },
    {
      name: 'Threat Intelligence',
      icon: AlertTriangle,
      badge: activeThreatCount > 0 ? String(activeThreatCount) : undefined
    },
    {
      name: 'Incident Feed',
      icon: Activity,
      badge: activeThreatCount > 0 ? String(activeThreatCount) : undefined
    },
    {
      name: 'Device Manager',
      icon: Server,
      badge: cameraCount > 0 ? String(cameraCount) : undefined,
      isInfoBadge: true
    }
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
          <div className="text-[10px] text-[#64748B] font-mono tracking-wider truncate">SOC DASHBOARD v2.1</div>
        </div>
      </div>

      {/* Nhóm OPERATIONS */}
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
              className={`w-full flex items-center gap-3 px-4 py-2.5 text-left text-xs transition-colors duration-150 min-w-0 cursor-pointer ${
                isActive
                  ? 'bg-[#112224] text-[#10B981] font-semibold border-l-[3px] border-[#10B981]'
                  : 'text-[#94A3B8] hover:bg-[#0E131A] hover:text-white border-l-[3px] border-transparent'
              }`}
            >
              <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-[#10B981]' : 'text-slate-400'}`} />
              <span className="flex-1 truncate" title={item.name}>{item.name}</span>
              {item.badge && (
                <span
                  className={`${
                    item.isInfoBadge
                      ? 'bg-[#112224] border border-[#10B981] text-[#10B981]'
                      : 'bg-[#991B1B] border border-[#DC2626] text-white'
                  } font-mono text-[10px] font-bold px-1.5 py-0.2 shrink-0 ml-auto`}
                >
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
          className={`w-full flex items-center gap-3 px-4 py-2.5 text-left text-xs transition-colors min-w-0 cursor-pointer ${
            activeTab === 'Settings'
              ? 'bg-[#112224] text-[#10B981] font-semibold border-l-[3px] border-[#10B981]'
              : 'text-[#94A3B8] hover:bg-[#0E131A] hover:text-white border-l-[3px] border-transparent'
          }`}
        >
          <Settings
            className={`w-4 h-4 shrink-0 ${
              activeTab === 'Settings' ? 'text-[#10B981]' : 'text-slate-400'
            }`}
          />
          <span className="truncate">Settings</span>
        </button>
      </nav>
    </aside>
  );
};
