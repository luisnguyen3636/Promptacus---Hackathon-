import React from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Filler
} from 'chart.js';
import { Line } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Filler
);

interface LinearTrafficChartProps {
  labels: string[];
  data: number[];
  color: string;
  maxVal: number;
}

export const LinearTrafficChart: React.FC<LinearTrafficChartProps> = ({
  labels,
  data,
  color,
  maxVal,
}) => {
  const chartData = {
    labels,
    datasets: [
      {
        data,
        borderColor: color,
        borderWidth: 2,
        fill: true,
        backgroundColor: (context: { chart: { ctx: CanvasRenderingContext2D } }) => {
          const ctx = context.chart.ctx;
          const gradient = ctx.createLinearGradient(0, 0, 0, 150);
          gradient.addColorStop(0, color === '#3B82F6' ? 'rgba(59, 130, 246, 0.25)' : 'rgba(16, 185, 129, 0.25)');
          gradient.addColorStop(1, 'rgba(0, 0, 0, 0)');
          return gradient;
        },
        tension: 0, // Đường thẳng góc cạnh công nghiệp
        pointRadius: 0,
        pointHoverRadius: 4,
        pointHoverBackgroundColor: color,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 400 },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: '#0E131A',
        borderColor: '#1E2631',
        borderWidth: 1,
        titleFont: { family: 'JetBrains Mono', size: 10 },
        bodyFont: { family: 'JetBrains Mono', size: 11 },
        cornerRadius: 0,
        displayColors: false,
      },
    },
    scales: {
      x: {
        grid: { color: 'rgba(30, 38, 49, 0.4)', drawBorder: false },
        ticks: { color: '#64748B', font: { family: 'JetBrains Mono', size: 10 } },
      },
      y: {
        min: 0,
        max: maxVal,
        grid: { color: 'rgba(30, 38, 49, 0.4)', drawBorder: false },
        ticks: { color: '#64748B', font: { family: 'JetBrains Mono', size: 10 }, stepSize: maxVal / 2 },
      },
    },
  };

  return (
    <div className="h-40 w-full">
      <Line data={chartData} options={options} />
    </div>
  );
};
