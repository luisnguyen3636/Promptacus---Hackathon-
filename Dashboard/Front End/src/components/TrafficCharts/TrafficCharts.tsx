import React from 'react';
import { LinearTrafficChart } from './LinearTrafficChart.tsx';
import { MOCK_TRAFFIC_SERIES } from '../../data/mockData.ts';

interface TrafficChartsProps {
  ingressVal?: number;
  egressVal?: number;
}

export const TrafficCharts: React.FC<TrafficChartsProps> = ({
  ingressVal = 9744.0,
  egressVal = 4822.2,
}) => {
  return (
    <section className="grid grid-cols-2 gap-4">
      {/* Khối Trái: Ingress Video Traffic */}
      <div className="bg-[#0E131A] border border-[#1E2631] p-4 flex flex-col select-none">
        <div className="flex items-center justify-between mb-3">
          <div>
            <span className="font-bold text-xs uppercase text-[#E2E8F0]">
              Ingress Video Traffic
            </span>
            <span className="text-[11px] text-[#64748B] ml-2">Ingress traffic</span>
          </div>
          <div className="font-mono font-bold text-sm text-[#3B82F6]">
            {Number(ingressVal).toFixed(1)} Mbps
          </div>
        </div>
        <LinearTrafficChart
          labels={MOCK_TRAFFIC_SERIES.labels}
          data={MOCK_TRAFFIC_SERIES.ingress}
          color="#3B82F6"
          maxVal={12000}
        />
      </div>

      {/* Khối Phải: Egress Traffic */}
      <div className="bg-[#0E131A] border border-[#1E2631] p-4 flex flex-col select-none">
        <div className="flex items-center justify-between mb-3">
          <div>
            <span className="font-bold text-xs uppercase text-[#E2E8F0]">Egress Traffic</span>
          </div>
          <div className="font-mono font-bold text-sm text-[#10B981]">
            {Number(egressVal).toFixed(1)} Mbps
          </div>
        </div>
        <LinearTrafficChart
          labels={MOCK_TRAFFIC_SERIES.labels}
          data={MOCK_TRAFFIC_SERIES.egress}
          color="#10B981"
          maxVal={6000}
        />
      </div>
    </section>
  );
};
