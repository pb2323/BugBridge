/**
 * Dashboard Overview Page
 * 
 * Main dashboard page with key metrics, charts, and visualizations.
 */

'use client';

import { DashboardLayout } from '../../components/layout/DashboardLayout';
import { ErrorBoundary } from '../../components/common/ErrorBoundary';
import { useMetrics } from '../../hooks/useMetrics';
import { MetricCard } from '../../components/metrics/MetricCard';
import { BugsVsFeaturesChart } from '../../components/metrics/BugsVsFeaturesChart';
import { SentimentChart } from '../../components/metrics/SentimentChart';
import { PriorityList } from '../../components/metrics/PriorityList';
import { TimeSeriesChart } from '../../components/metrics/TimeSeriesChart';
import { JiraStatusChart } from '../../components/metrics/JiraStatusChart';
import { PriorityScoreChart } from '../../components/metrics/PriorityScoreChart';
import { BurningIssuesList } from '../../components/metrics/BurningIssuesList';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { SkeletonCard, SkeletonChart } from '../../components/common/SkeletonLoader';
import { formatDistanceToNow } from 'date-fns';
import { useState } from 'react';

export default function DashboardPage() {
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshInterval, setRefreshInterval] = useState(30000); // 30 seconds default

  const { data: metrics, isLoading, error, refetch } = useMetrics({
    refetchInterval: autoRefresh ? refreshInterval : (false as const),
  });

  // Calculate time-based metrics
  const today = new Date();
  const weekAgo = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
  const monthAgo = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);

  if (isLoading && !metrics) {
    return (
      <ErrorBoundary>
        <DashboardLayout>
          <div className="space-y-6">
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
              {[1, 2, 3, 4].map((i) => (
                <SkeletonCard key={i} />
              ))}
            </div>
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <SkeletonChart />
              <SkeletonChart />
            </div>
          </div>
        </DashboardLayout>
      </ErrorBoundary>
    );
  }

  if (error) {
    return (
      <ErrorBoundary>
        <DashboardLayout>
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800">Error loading metrics. Please try again.</p>
            <button
              onClick={() => refetch()}
              className="mt-2 rounded-md bg-red-600 px-3 py-2 text-sm font-semibold text-white hover:bg-red-500"
            >
              Retry
            </button>
          </div>
        </DashboardLayout>
      </ErrorBoundary>
    );
  }

  if (!metrics) {
    return null;
  }

  // Prepare time series data (placeholder - would need historical data from API)
  const timeSeriesData = [
    { date: 'Week 1', posts: metrics.recent_posts || 0, tickets: metrics.recent_tickets || 0 },
    { date: 'Week 2', posts: (metrics.recent_posts || 0) * 0.8, tickets: (metrics.recent_tickets || 0) * 0.9 },
    { date: 'Week 3', posts: (metrics.recent_posts || 0) * 0.9, tickets: (metrics.recent_tickets || 0) * 0.85 },
    { date: 'Week 4', posts: metrics.recent_posts || 0, tickets: metrics.recent_tickets || 0 },
  ];

  // Prepare Jira status data (placeholder - would need from API)
  const jiraStatusData = [
    { status: 'To Do', count: Math.floor((metrics.total_jira_tickets || 0) * 0.3) },
    { status: 'In Progress', count: Math.floor((metrics.total_jira_tickets || 0) * 0.2) },
    { status: 'Done', count: metrics.resolved_tickets || 0 },
  ];

  return (
    <ErrorBoundary>
      <DashboardLayout>
        <div className="space-y-6">
          {/* Header with auto-refresh controls */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Dashboard Overview</h1>
              <p className="mt-1 text-sm text-gray-500">
                Last updated: {metrics ? formatDistanceToNow(new Date(), { addSuffix: true }) : 'Never'}
              </p>
            </div>
            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 text-sm text-gray-700">
                <input
                  type="checkbox"
                  checked={autoRefresh}
                  onChange={(e) => setAutoRefresh(e.target.checked)}
                  className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-600"
                />
                Auto-refresh
              </label>
              <button
                onClick={() => refetch()}
                className="rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500"
              >
                Refresh Now
              </button>
            </div>
          </div>

          {/* Key Metrics Cards */}
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
            <MetricCard
              title="Total Feedback Posts"
              value={metrics.total_feedback_posts || 0}
              subtitle="All time"
            />
            <MetricCard
              title="Bugs"
              value={metrics.total_bugs || 0}
              subtitle={`${metrics.bugs_percentage?.toFixed(1) || 0}% of total`}
            />
            <MetricCard
              title="Jira Tickets"
              value={metrics.total_jira_tickets || 0}
              subtitle={`${metrics.resolved_tickets || 0} resolved`}
            />
            <MetricCard
              title="Resolution Rate"
              value={`${metrics.resolution_rate?.toFixed(1) || 0}%`}
              subtitle={`${metrics.resolved_tickets || 0} / ${metrics.total_jira_tickets || 0}`}
            />
          </div>

          {/* Charts Row 1 */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <BugsVsFeaturesChart
              bugs={metrics.total_bugs || 0}
              features={metrics.total_feature_requests || 0}
            />
            <SentimentChart data={metrics.sentiment_distribution || {}} />
          </div>

          {/* Charts Row 2 */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <TimeSeriesChart
              data={timeSeriesData}
              dataKeys={[
                { key: 'posts', name: 'Feedback Posts', color: '#6366f1' },
                { key: 'tickets', name: 'Jira Tickets', color: '#10b981' },
              ]}
              title="Trends Over Time"
            />
            <JiraStatusChart data={jiraStatusData} />
          </div>

          {/* Priority Score Distribution */}
          {metrics.priority_distribution && Object.keys(metrics.priority_distribution).length > 0 && (
            <div className="grid grid-cols-1 gap-6">
              <PriorityScoreChart data={metrics.priority_distribution} />
            </div>
          )}

          {/* Burning Issues */}
          {metrics.top_priority_items && metrics.top_priority_items.length > 0 && (
            <div className="grid grid-cols-1 gap-6">
              <BurningIssuesList
                items={metrics.top_priority_items
                  .filter((item) => item.priority_score >= 8.0)
                  .map((item) => ({
                    ...item,
                    votes: 0, // Would come from API
                    sentiment: 'negative', // Would come from API
                  }))}
                maxItems={5}
              />
            </div>
          )}

          {/* Priority Items and Additional Metrics */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <PriorityList items={metrics.top_priority_items || []} maxItems={10} />
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Performance Metrics</h3>
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Average Response Time</span>
                  <span className="text-sm font-semibold text-gray-900">
                    {metrics.average_response_time_hours
                      ? `${metrics.average_response_time_hours.toFixed(1)} hours`
                      : 'N/A'}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Average Resolution Time</span>
                  <span className="text-sm font-semibold text-gray-900">
                    {metrics.average_resolution_time_hours
                      ? `${metrics.average_resolution_time_hours.toFixed(1)} hours`
                      : 'N/A'}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Recent Posts (7 days)</span>
                  <span className="text-sm font-semibold text-gray-900">{metrics.recent_posts || 0}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Recent Tickets</span>
                  <span className="text-sm font-semibold text-gray-900">{metrics.recent_tickets || 0}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Recent Resolutions</span>
                  <span className="text-sm font-semibold text-gray-900">{metrics.recent_resolutions || 0}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </DashboardLayout>
    </ErrorBoundary>
  );
}
