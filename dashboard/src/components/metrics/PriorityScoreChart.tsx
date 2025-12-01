/**
 * Priority Score Distribution Chart Component
 * 
 * Chart showing the distribution of priority scores.
 */

'use client';

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface PriorityScoreChartProps {
  data: Record<string, number>;
}

export function PriorityScoreChart({ data }: PriorityScoreChartProps) {
  const chartData = Object.entries(data).map(([range, count]) => ({
    range,
    count,
  }));

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Priority Score Distribution</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="range" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Bar dataKey="count" fill="#6366f1" radius={[8, 8, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

