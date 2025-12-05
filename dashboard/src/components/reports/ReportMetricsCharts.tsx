/**
 * Report Metrics Charts Component
 * 
 * Visual charts and graphs for report metrics overview.
 */

'use client';

import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface DailyMetrics {
  date: string;
  new_issues_count: number;
  bugs_count: number;
  feature_requests_count: number;
  bugs_percentage: number;
  sentiment_distribution: Record<string, number>;
  priority_items: Array<{ title: string; priority: string }>;
  tickets_created: number;
  tickets_resolved: number;
  average_response_time_hours?: number;
  resolution_rate: number;
  average_resolution_time_hours?: number;
}

interface ReportMetricsChartsProps {
  metrics: DailyMetrics;
}

const COLORS = {
  bugs: '#EF4444',
  features: '#10B981',
  positive: '#10B981',
  neutral: '#6B7280',
  negative: '#EF4444',
  frustrated: '#DC2626',
  created: '#3B82F6',
  resolved: '#10B981',
};

export function ReportMetricsCharts({ metrics }: ReportMetricsChartsProps) {
  // Prepare bugs vs features data
  const bugsVsFeaturesData = [
    { name: 'Bugs', value: metrics.bugs_count, color: COLORS.bugs },
    { name: 'Features', value: metrics.feature_requests_count, color: COLORS.features },
  ];

  // Prepare sentiment distribution data
  const sentimentData = Object.entries(metrics.sentiment_distribution || {}).map(([sentiment, count]) => ({
    sentiment: sentiment.charAt(0).toUpperCase() + sentiment.slice(1),
    count,
    fill: COLORS[sentiment as keyof typeof COLORS] || COLORS.neutral,
  }));

  // Prepare ticket stats data
  const ticketStatsData = [
    { name: 'Created', value: metrics.tickets_created, fill: COLORS.created },
    { name: 'Resolved', value: metrics.tickets_resolved, fill: COLORS.resolved },
  ];

  // Prepare time metrics data
  const timeMetricsData = [];
  if (metrics.average_response_time_hours !== undefined && metrics.average_response_time_hours !== null) {
    timeMetricsData.push({
      name: 'Avg Response Time',
      hours: Number(metrics.average_response_time_hours.toFixed(2)),
    });
  }
  if (metrics.average_resolution_time_hours !== undefined && metrics.average_resolution_time_hours !== null) {
    timeMetricsData.push({
      name: 'Avg Resolution Time',
      hours: Number(metrics.average_resolution_time_hours.toFixed(2)),
    });
  }

  return (
    <div className="space-y-6">
      {/* Key Metrics Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="flex items-center justify-center h-12 w-12 rounded-md bg-indigo-500 text-white text-xl font-bold">
                  {metrics.new_issues_count}
                </div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">New Issues</dt>
                  <dd className="text-lg font-semibold text-gray-900">Total Reported</dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="flex items-center justify-center h-12 w-12 rounded-md bg-red-500 text-white text-xl font-bold">
                  {metrics.bugs_count}
                </div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Bugs</dt>
                  <dd className="text-lg font-semibold text-gray-900">{metrics.bugs_percentage.toFixed(1)}%</dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="flex items-center justify-center h-12 w-12 rounded-md bg-green-500 text-white text-xl font-bold">
                  {metrics.tickets_resolved}
                </div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Resolved</dt>
                  <dd className="text-lg font-semibold text-gray-900">{metrics.resolution_rate.toFixed(1)}%</dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="flex items-center justify-center h-12 w-12 rounded-md bg-blue-500 text-white text-xl font-bold">
                  {metrics.tickets_created}
                </div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Jira Tickets</dt>
                  <dd className="text-lg font-semibold text-gray-900">Created</dd>
                </dl>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Bugs vs Features Chart */}
        <div className="bg-white shadow rounded-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Bugs vs Feature Requests</h3>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={bugsVsFeaturesData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, value, percent }) => `${name}: ${value} (${(percent * 100).toFixed(0)}%)`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {bugsVsFeaturesData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Sentiment Distribution Chart */}
        {sentimentData.length > 0 && (
          <div className="bg-white shadow rounded-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Sentiment Distribution</h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={sentimentData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="sentiment" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#8884d8">
                  {sentimentData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Ticket Status Chart */}
        <div className="bg-white shadow rounded-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Ticket Status</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={ticketStatsData} layout="horizontal">
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="value" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Time Metrics Chart */}
        {timeMetricsData.length > 0 && (
          <div className="bg-white shadow rounded-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Performance Metrics</h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={timeMetricsData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" angle={-15} textAnchor="end" height={80} />
                <YAxis label={{ value: 'Hours', angle: -90, position: 'insideLeft' }} />
                <Tooltip />
                <Bar dataKey="hours" fill="#8B5CF6" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  );
}

