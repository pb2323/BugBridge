/**
 * Jira Tickets Listing Page
 * 
 * Main page for viewing and managing Jira tickets with filtering, search, and pagination.
 */

'use client';

import { useState, useMemo } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { DashboardLayout } from '../../components/layout/DashboardLayout';
import { ErrorBoundary } from '../../components/common/ErrorBoundary';
import { JiraTicketsTable } from '../../components/jira/JiraTicketsTable';
import { JiraTicketFilters, JiraTicketFilters as JiraTicketFiltersType } from '../../components/jira/JiraTicketFilters';
import { Pagination } from '../../components/feedback/Pagination';
import { useJiraList } from '../../hooks/useJira';
import { SkeletonCard } from '../../components/common/SkeletonLoader';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { jiraApi } from '../../services/api/jira';

export default function JiraTicketsPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [sortBy, setSortBy] = useState<string>('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [filters, setFilters] = useState<JiraTicketFiltersType>({});
  const [refreshStatus, setRefreshStatus] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Convert filters to API params
  const apiParams = useMemo(() => {
    const params: any = {
      page,
      page_size: pageSize,
      sort_by: sortBy,
      sort_order: sortOrder,
    };

    if (filters.project_keys && filters.project_keys.length > 0) {
      params.project_keys = filters.project_keys.join(',');
    }
    if (filters.statuses && filters.statuses.length > 0) {
      params.statuses = filters.statuses.join(',');
    }
    if (filters.priorities && filters.priorities.length > 0) {
      params.priorities = filters.priorities.join(',');
    }
    if (filters.assignee) {
      params.assignee = filters.assignee;
    }
    if (filters.resolved_only) {
      params.resolved_only = true;
    }
    if (filters.unresolved_only) {
      params.unresolved_only = true;
    }
    if (filters.has_feedback !== undefined) {
      params.has_feedback = filters.has_feedback;
    }

    return params;
  }, [page, pageSize, sortBy, sortOrder, filters]);

  const { data, isLoading, error, refetch } = useJiraList(apiParams);

  const refreshMutation = useMutation({
    mutationFn: () => jiraApi.refresh(),
    onMutate: () => {
      setIsRefreshing(true);
      setRefreshStatus('Fetching latest ticket updates from Jira...');
    },
    onSuccess: (data) => {
      // Invalidate Jira tickets list so it refetches with updated data
      queryClient.invalidateQueries({ queryKey: ['jira-tickets'] });
      
      // Show success message with statistics
      const message = `✅ Successfully refreshed! Updated: ${data.tickets_updated} tickets, Failed: ${data.tickets_failed} out of ${data.total_tickets} total`;
      setRefreshStatus(message);
      setIsRefreshing(false);
      
      // Clear message after 8 seconds
      setTimeout(() => setRefreshStatus(null), 8000);
    },
    onError: (error: any) => {
      setRefreshStatus(`❌ Error: ${error?.response?.data?.detail || 'Failed to refresh Jira tickets'}`);
      setIsRefreshing(false);
      setTimeout(() => setRefreshStatus(null), 8000);
    },
  });

  const handleSort = (field: string) => {
    if (sortBy === field) {
      // Toggle sort order
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      // New field, default to descending
      setSortBy(field);
      setSortOrder('desc');
    }
  };

  const handlePageChange = (newPage: number) => {
    setPage(newPage);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handlePageSizeChange = (newPageSize: number) => {
    setPageSize(newPageSize);
    setPage(1); // Reset to first page
  };

  if (isLoading && !data) {
    return (
      <ErrorBoundary>
        <DashboardLayout>
          <div className="space-y-6">
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
              {[1, 2, 3, 4].map((i) => (
                <SkeletonCard key={i} />
              ))}
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
            <p className="text-red-800">Error loading Jira tickets. Please try again.</p>
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

  return (
    <ErrorBoundary>
      <DashboardLayout>
        <div className="space-y-6">
          {/* Refresh Status Message */}
          {refreshStatus && (
            <div className={`rounded-md p-4 ${refreshStatus.startsWith('❌') ? 'bg-red-50 border border-red-200' : 'bg-green-50 border border-green-200'}`}>
              <p className={refreshStatus.startsWith('❌') ? 'text-red-800 text-sm' : 'text-green-800 text-sm'}>
                {refreshStatus}
              </p>
            </div>
          )}

          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Jira Tickets</h1>
              <p className="mt-1 text-sm text-gray-500">
                View and manage Jira tickets linked to feedback posts
              </p>
            </div>
            <div className="flex items-center gap-4">
              <button
                onClick={() => refreshMutation.mutate()}
                disabled={isRefreshing || refreshMutation.isPending || refreshMutation.isLoading}
                className="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-indigo-600 transition-all"
              >
                {isRefreshing || refreshMutation.isPending || refreshMutation.isLoading ? (
                  <>
                    <LoadingSpinner size="sm" />
                    <span>Refreshing from Jira...</span>
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    <span>Refresh from Jira</span>
                  </>
                )}
              </button>
              <select
                value={pageSize}
                onChange={(e) => handlePageSizeChange(parseInt(e.target.value))}
                className="rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
              >
                <option value={10}>10 per page</option>
                <option value={20}>20 per page</option>
                <option value={50}>50 per page</option>
                <option value={100}>100 per page</option>
              </select>
            </div>
          </div>

          {/* Filters */}
          <JiraTicketFilters filters={filters} onFiltersChange={setFilters} />

          {/* Results Summary */}
          {data && (
            <div className="text-sm text-gray-500">
              Showing {data.items.length} of {data.total} Jira tickets
            </div>
          )}

          {/* Table */}
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <JiraTicketsTable
              tickets={data?.items || []}
              sortBy={sortBy}
              sortOrder={sortOrder}
              onSort={handleSort}
            />
          </div>

          {/* Pagination */}
          {data && data.total_pages > 1 && (
            <Pagination
              currentPage={data.page}
              totalPages={data.total_pages}
              totalItems={data.total}
              pageSize={data.page_size}
              onPageChange={handlePageChange}
            />
          )}
        </div>
      </DashboardLayout>
    </ErrorBoundary>
  );
}
