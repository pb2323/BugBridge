/**
 * Sentiment Distribution Chart Component
 * 
 * Bar chart showing sentiment distribution (positive, neutral, negative).
 */

'use client';

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface SentimentChartProps {
  data: Record<string, number>;
}

const SENTIMENT_COLORS: Record<string, string> = {
  positive: '#10b981', // green
  neutral: '#6b7280', // gray
  negative: '#ef4444', // red
};

export function SentimentChart({ data }: SentimentChartProps) {
  const chartData = Object.entries(data).map(([name, value]) => ({
    name: name.charAt(0).toUpperCase() + name.slice(1),
    value,
    color: SENTIMENT_COLORS[name.toLowerCase()] || '#6b7280',
  }));

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Sentiment Distribution</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="name" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Bar dataKey="value" fill="#6366f1" radius={[8, 8, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

