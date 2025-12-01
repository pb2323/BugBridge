/**
 * Bugs vs Features Chart Component
 * 
 * Pie chart showing the breakdown of bugs vs feature requests.
 */

'use client';

import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import { useState } from 'react';
import { ChartDrillDown } from './ChartDrillDown';

interface BugsVsFeaturesChartProps {
  bugs: number;
  features: number;
  onDrillDown?: (type: 'bugs' | 'features') => void;
}

const COLORS = ['#ef4444', '#10b981']; // red for bugs, green for features

export function BugsVsFeaturesChart({ bugs, features, onDrillDown }: BugsVsFeaturesChartProps) {
  const [isDrillDownOpen, setIsDrillDownOpen] = useState(false);
  const [drillDownData, setDrillDownData] = useState<Array<Record<string, any>>>([]);
  const [drillDownTitle, setDrillDownTitle] = useState('');

  const data = [
    { name: 'Bugs', value: bugs },
    { name: 'Feature Requests', value: features },
  ];

  const handlePieClick = (entry: any) => {
    if (onDrillDown) {
      onDrillDown(entry.name === 'Bugs' ? 'bugs' : 'features');
    } else {
      // Default drill-down behavior
      setDrillDownTitle(`${entry.name} Details`);
      setDrillDownData([
        { Type: entry.name, Count: entry.value, Percentage: `${((entry.value / (bugs + features)) * 100).toFixed(1)}%` },
      ]);
      setIsDrillDownOpen(true);
    }
  };

  return (
    <>
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Bugs vs Feature Requests</h3>
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={({ name, percent }) => `${name}: ${((percent || 0) * 100).toFixed(0)}%`}
              outerRadius={80}
              fill="#8884d8"
              dataKey="value"
              onClick={handlePieClick}
              style={{ cursor: 'pointer' }}
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
        <p className="mt-2 text-xs text-gray-500 text-center">Click on a segment to view details</p>
      </div>
      <ChartDrillDown
        isOpen={isDrillDownOpen}
        onClose={() => setIsDrillDownOpen(false)}
        title={drillDownTitle}
        data={drillDownData}
        columns={[
          { key: 'Type', label: 'Type' },
          { key: 'Count', label: 'Count' },
          { key: 'Percentage', label: 'Percentage' },
        ]}
      />
    </>
  );
}

