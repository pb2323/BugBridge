/**
 * Metrics & Analytics Page
 * 
 * Detailed metrics and analytics page with date filtering and drill-down capabilities.
 */

'use client';

import { useState } from 'react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { ErrorBoundary } from '@/components/common/ErrorBoundary';
import { useMetrics } from '@/hooks/useMetrics';
import { MetricCard } from '@/components/metrics/MetricCard';
import { BugsVsFeaturesChart } from '@/components/metrics/BugsVsFeaturesChart';
import { SentimentChart } from '@/components/metrics/SentimentChart';
import { PriorityList } from '@/components/metrics/PriorityList';
import { TimeSeriesChart } from '@/components/metrics/TimeSeriesChart';
import { JiraStatusChart } from '@/components/metrics/JiraStatusChart';
import { PriorityScoreChart } from '@/components/metrics/PriorityScoreChart';
import { BurningIssuesList } from '@/components/metrics/BurningIssuesList';
import { LoadingSpinner } from '@/components/common/LoadingSpinner';
import { SkeletonCard, SkeletonChart } from '@/components/common/SkeletonLoader';
import { formatDistanceToNow } from 'date-fns';

export default function MetricsPage() {
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [refreshInterval, setRefreshInterval] = useState(60000); // 60 seconds default
  const [dateRange, setDateRange] = useState<'all' | '7d' | '30d' | '90d' | 'custom'>('all');
  const [customStartDate, setCustomStartDate] = useState<string>('');
  const [customEndDate, setCustomEndDate] = useState<string>('');

  // Calculate date range
  const getDateRange = () => {
    const today = new Date();
    today.setHours(23, 59, 59, 999); // End of today
    
    switch (dateRange) {
      case '7d':
        const weekAgo = new Date(today);
        weekAgo.setDate(weekAgo.getDate() - 7);
        weekAgo.setHours(0, 0, 0, 0);
        return {
          startDate: weekAgo.toISOString().split('T')[0],
          endDate: today.toISOString().split('T')[0],
        };
      case '30d':
        const monthAgo = new Date(today);
        monthAgo.setDate(monthAgo.getDate() - 30);
        monthAgo.setHours(0, 0, 0, 0);
        return {
          startDate: monthAgo.toISOString().split('T')[0],
          endDate: today.toISOString().split('T')[0],
        };
      case '90d':
        const quarterAgo = new Date(today);
        quarterAgo.setDate(quarterAgo.getDate() - 90);
        quarterAgo.setHours(0, 0, 0, 0);
        return {
          startDate: quarterAgo.toISOString().split('T')[0],
          endDate: today.toISOString().split('T')[0],
        };
      case 'custom':
        return {
          startDate: customStartDate || undefined,
          endDate: customEndDate || undefined,
        };
      default:
        return {
          startDate: undefined,
          endDate: undefined,
        };
    }
  };

  const { startDate, endDate } = getDateRange();

  const { data: metrics, isLoading, error, refetch } = useMetrics({
    startDate,
    endDate,
    refetchInterval: autoRefresh ? refreshInterval : (false as const),
  });

  if (isLoading && !metrics) {
    return (
      <ErrorBoundary>
        <DashboardLayout>
          <div className="space-y-6">
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
              {[1, 2, 3, 4, 5, 6].map((i) => (
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
          {/* Header with filters and controls */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Metrics & Analytics</h1>
              <p className="mt-1 text-sm text-gray-500">
                Detailed analytics and insights into your feedback and tickets
                {startDate && endDate && (
                  <span>
                    {' '}
                    ({new Date(startDate).toLocaleDateString()} - {new Date(endDate).toLocaleDateString()})
                  </span>
                )}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-4">
              {/* Date Range Filter */}
              <div className="flex items-center gap-2">
                <label htmlFor="dateRange" className="text-sm font-medium text-gray-700">
                  Period:
                </label>
                <select
                  id="dateRange"
                  value={dateRange}
                  onChange={(e) => setDateRange(e.target.value as any)}
                  className="rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                >
                  <option value="all">All Time</option>
                  <option value="7d">Last 7 Days</option>
                  <option value="30d">Last 30 Days</option>
                  <option value="90d">Last 90 Days</option>
                  <option value="custom">Custom Range</option>
                </select>
              </div>

              {/* Custom Date Range */}
              {dateRange === 'custom' && (
                <div className="flex items-center gap-2">
                  <input
                    type="date"
                    value={customStartDate}
                    onChange={(e) => setCustomStartDate(e.target.value)}
                    className="rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                  />
                  <span className="text-sm text-gray-500">to</span>
                  <input
                    type="date"
                    value={customEndDate}
                    onChange={(e) => setCustomEndDate(e.target.value)}
                    className="rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                  />
                </div>
              )}

              {/* Auto-refresh Toggle */}
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
              subtitle={dateRange !== 'all' ? `Selected period` : 'All time'}
            />
            <MetricCard
              title="Bugs Identified"
              value={metrics.total_bugs || 0}
              subtitle={`${metrics.bugs_percentage?.toFixed(1) || 0}% of total`}
            />
            <MetricCard
              title="Feature Requests"
              value={metrics.total_feature_requests || 0}
              subtitle={`${(100 - (metrics.bugs_percentage || 0)).toFixed(1)}% of total`}
            />
            <MetricCard
              title="Jira Tickets Created"
              value={metrics.total_jira_tickets || 0}
              subtitle={`${metrics.resolved_tickets || 0} resolved`}
            />
          </div>

          {/* Secondary Metrics Cards */}
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
            <MetricCard
              title="Resolution Rate"
              value={`${metrics.resolution_rate?.toFixed(1) || 0}%`}
              subtitle={`${metrics.resolved_tickets || 0} / ${metrics.total_jira_tickets || 0}`}
            />
            <MetricCard
              title="Avg Response Time"
              value={
                metrics.average_response_time_hours
                  ? `${metrics.average_response_time_hours.toFixed(1)}h`
                  : 'N/A'
              }
              subtitle="Feedback to ticket"
            />
            <MetricCard
              title="Avg Resolution Time"
              value={
                metrics.average_resolution_time_hours
                  ? `${metrics.average_resolution_time_hours.toFixed(1)}h`
                  : 'N/A'
              }
              subtitle="Ticket creation to resolution"
            />
            <MetricCard
              title="Recent Activity (7d)"
              value={metrics.recent_posts || 0}
              subtitle={`${metrics.recent_tickets || 0} tickets, ${metrics.recent_resolutions || 0} resolved`}
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
                maxItems={10}
              />
            </div>
          )}

          {/* Priority Items */}
          {metrics.top_priority_items && metrics.top_priority_items.length > 0 && (
            <div className="grid grid-cols-1 gap-6">
              <PriorityList items={metrics.top_priority_items || []} maxItems={20} />
            </div>
          )}
        </div>
      </DashboardLayout>
    </ErrorBoundary>
  );
}
