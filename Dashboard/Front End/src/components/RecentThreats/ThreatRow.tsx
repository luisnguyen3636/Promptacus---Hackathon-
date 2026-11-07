import React from 'react';
import { Play } from 'lucide-react';
import { IIncidentItem } from '../../types/soc.ts';

interface ThreatRowProps {
  incident: IIncidentItem;
  onPlayback: (incident: IIncidentItem) => void;
}

export const ThreatRow: React.FC<ThreatRowProps> = ({ incident, onPlayback }) => {
  const isMedium = incident.severity === 'MEDIUM';
  const isCritical = incident.severity === 'CRITICAL';
  const isHigh = incident.severity === 'HIGH';

  let sqColor = 'bg-[#10B981]';
  if (isCritical) sqColor = 'bg-[#DC2626]';
  else if (isHigh) sqColor = 'bg-[#F97316]';
  else if (isMedium) sqColor = 'bg-[#EAB308]';

  let badgeStyle = 'border-[#10B981] text-[#10B981] bg-[#10B981]/10';
  if (isCritical) {
    badgeStyle = 'border-[#DC2626] text-[#DC2626] bg-[#DC2626]/15';
  } else if (isHigh) {
    badgeStyle = 'border-[#F97316] text-[#F97316] bg-[#F97316]/10';
  } else if (isMedium) {
    badgeStyle = 'border-[#EAB308] text-[#EAB308] bg-[#EAB308]/10';
  }

  const displayTime =
    incident.timestamp && incident.timestamp.includes('T')
      ? incident.timestamp.split('T')[1].substring(0, 8)
      : incident.timestamp || '--:--:--';

  const secondaryDesc = incident.location || incident.reasoning || incident.subTitle || incident.category;
  const scorePct =
    incident.threatScore !== undefined
      ? incident.threatScore <= 1
        ? Math.round(incident.threatScore * 100)
        : Math.round(incident.threatScore)
      : 0;

  return (
    <div className="grid grid-cols-[20px_65px_minmax(160px,1fr)_120px_120px_90px_105px] items-center gap-2.5 px-3 py-2 border-b border-[#1E2631] hover:bg-[#161E29]/60 transition-colors select-none min-w-[680px]">
      {/* 1. Status Square */}
      <div className="flex items-center justify-center min-w-0">
        <span className={`w-2 h-2 shrink-0 ${sqColor}`} />
      </div>

      {/* 2. Time */}
      <div className="font-mono text-slate-400 text-xs min-w-0 truncate" title={incident.timestamp}>
        {displayTime}
      </div>

      {/* 3. Event Title & Location */}
      <div className="min-w-0 overflow-hidden pr-2">
        <div
          className="font-bold text-slate-100 text-xs truncate"
          title={`[${incident.actionType || 'EVENT'}] ${incident.description || incident.title}`}
        >
          {incident.actionType ? `[${incident.actionType}] ` : ''}
          {incident.description || incident.title}
        </div>
        <div
          className="text-[10px] text-slate-500 font-mono truncate"
          title={secondaryDesc}
        >
          {secondaryDesc}
        </div>
      </div>

      {/* 4. Camera ID */}
      <div
        className="font-mono text-[#38BDF8] text-xs text-center font-bold min-w-0 truncate"
        title={incident.cameraId || incident.sourceIp}
      >
        {incident.cameraId || incident.sourceIp}
      </div>

      {/* 5. Telemetry / Snapshot Info */}
      <div className="min-w-0 shrink-0">
        {incident.cameraSnapshots?.eventPeakSnapshotUrl || incident.cameraSnapshots?.preEventSnapshotUrl ? (
          <div className="flex gap-1 items-center">
            {incident.cameraSnapshots.preEventSnapshotUrl && (
              <img
                src={incident.cameraSnapshots.preEventSnapshotUrl}
                alt="Subject"
                title="Subject Detection Snapshot"
                className="w-[52px] h-[30px] object-cover border border-[#1E2631] bg-[#05070A] shrink-0"
              />
            )}
            {incident.cameraSnapshots.eventPeakSnapshotUrl && (
              <img
                src={incident.cameraSnapshots.eventPeakSnapshotUrl}
                alt="Peak"
                title="Full CCTV Event Snapshot"
                className="w-[52px] h-[30px] object-cover border border-[#EF4444] bg-[#05070A] shrink-0"
              />
            )}
          </div>
        ) : (
          <div className="px-2 py-1 bg-[#121822] border border-[#1E2631] text-slate-300 font-mono text-[10px] shrink-0 text-center">
            SCORE: <span className="text-[#10B981] font-bold">{scorePct}%</span>
            {incident.humanCount !== undefined ? ` • ${incident.humanCount}P` : ''}
          </div>
        )}
      </div>

      {/* 6. Severity Badge */}
      <div className="text-center min-w-0 shrink-0">
        <span className={`font-mono text-[10px] font-bold px-1.5 py-0.5 border inline-block whitespace-nowrap ${badgeStyle}`}>
          [ {incident.severity} ]
        </span>
      </div>

      {/* 7. Action Button */}
      <div className="text-center min-w-0 shrink-0">
        <button
          onClick={() => onPlayback(incident)}
          className="bg-[#161E29] border border-[#2D3748] text-white hover:bg-[#1E2631] hover:border-[#10B981] hover:text-[#10B981] font-mono text-[10px] font-bold px-2 py-1 inline-flex items-center gap-1 cursor-pointer transition-colors whitespace-nowrap"
        >
          <span>CHI TIẾT</span>
          <Play className="w-2.5 h-2.5 fill-current" />
        </button>
      </div>
    </div>
  );
};
