/**
 * Feedback Posts Listing Page
 * 
 * Main page for viewing and managing feedback posts with filtering, search, and pagination.
 */

'use client';

import { useMemo, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { DashboardLayout } from '../../components/layout/DashboardLayout';
import { ErrorBoundary } from '../../components/common/ErrorBoundary';
import { FeedbackTable } from '../../components/feedback/FeedbackTable';
import { FeedbackFilters, FeedbackFilters as FeedbackFiltersType } from '../../components/feedback/FeedbackFilters';
import { Pagination } from '../../components/feedback/Pagination';
import { useFeedbackList } from '../../hooks/useFeedback';
import { SkeletonCard } from '../../components/common/SkeletonLoader';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { feedbackApi } from '../../services/api/feedback';

export default function FeedbackPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [sortBy, setSortBy] = useState<string>('collected_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [filters, setFilters] = useState<FeedbackFiltersType>({});

  // Convert filters to API params
  const apiParams = useMemo(() => {
    const params: any = {
      page,
      page_size: pageSize,
      sort_by: sortBy,
      sort_order: sortOrder,
    };

    if (filters.search) params.search = filters.search;
    if (filters.is_bug !== undefined) params.is_bug = filters.is_bug;
    if (filters.sentiment) params.sentiment = filters.sentiment;
    if (filters.min_priority !== undefined) params.min_priority = filters.min_priority;
    if (filters.min_votes !== undefined) params.min_votes = filters.min_votes;
    if (filters.has_jira_ticket !== undefined) params.has_jira_ticket = filters.has_jira_ticket;
    if (filters.status && filters.status.length > 0) params.statuses = filters.status.join(',');
    if (filters.board_ids && filters.board_ids.length > 0) params.board_ids = filters.board_ids.join(',');
    if (filters.tags && filters.tags.length > 0) params.tags = filters.tags.join(',');

    return params;
  }, [page, pageSize, sortBy, sortOrder, filters]);

  const { data, isLoading, error, refetch } = useFeedbackList(apiParams);

  const [refreshStatus, setRefreshStatus] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const refreshMutation = useMutation({
    mutationFn: () => feedbackApi.refresh(),
    onMutate: () => {
      // Set loading state immediately when mutation starts
      setIsRefreshing(true);
      setRefreshStatus('Fetching posts from Canny.io and processing...');
    },
    onSuccess: (data) => {
      // Invalidate feedback list so it refetches with latest data
      queryClient.invalidateQueries({ queryKey: ['feedback', 'list'] });
      
      // Show success message with statistics
      const message = `✅ Successfully refreshed from Canny! Collected: ${data.collected_count} posts, Processed: ${data.processed_count}, Analyzed: ${data.successful_processing}, Jira tickets created: ${data.jira_tickets_created}`;
      setRefreshStatus(message);
      setIsRefreshing(false);
      
      // Clear message after 8 seconds (longer for more data)
      setTimeout(() => setRefreshStatus(null), 8000);
    },
    onError: (error: any) => {
      setRefreshStatus(`❌ Error: ${error?.response?.data?.detail || 'Failed to refresh from Canny'}`);
      setIsRefreshing(false);
      setTimeout(() => setRefreshStatus(null), 8000);
    },
  });

  const [processingPostId, setProcessingPostId] = useState<string | null>(null);

  const processSingleMutation = useMutation({
    mutationFn: (postId: string) => feedbackApi.processSingle(postId),
    onMutate: (postId) => {
      setProcessingPostId(postId);
    },
    onSuccess: (data, postId) => {
      // Invalidate feedback list so it refetches with updated data
      queryClient.invalidateQueries({ queryKey: ['feedback', 'list'] });
      
      // Show success message
      const message = data.jira_tickets_created > 0 
        ? `Post processed successfully! Jira ticket created.`
        : `Post processed successfully! Priority below threshold, no Jira ticket created.`;
      setRefreshStatus(message);
      
      setProcessingPostId(null);
      setTimeout(() => setRefreshStatus(null), 5000);
    },
    onError: (error: any, postId) => {
      setRefreshStatus(`Error: ${error?.response?.data?.detail || 'Failed to process post'}`);
      setProcessingPostId(null);
      setTimeout(() => setRefreshStatus(null), 5000);
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
            <p className="text-red-800">Error loading feedback posts. Please try again.</p>
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
            <div className={`rounded-md p-4 ${refreshStatus.startsWith('Error') ? 'bg-red-50 border border-red-200' : 'bg-green-50 border border-green-200'}`}>
              <p className={refreshStatus.startsWith('Error') ? 'text-red-800 text-sm' : 'text-green-800 text-sm'}>
                {refreshStatus}
              </p>
            </div>
          )}

          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Feedback Posts</h1>
              <p className="mt-1 text-sm text-gray-500">
                Manage and analyze customer feedback from Canny.io
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
                    <span>Fetching & Processing...</span>
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    <span>Refresh from Canny</span>
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
          <FeedbackFilters filters={filters} onFiltersChange={setFilters} />

          {/* Results Summary */}
          {data && (
            <div className="text-sm text-gray-500">
              Showing {data.items.length} of {data.total} feedback posts
            </div>
          )}

          {/* Table */}
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <FeedbackTable
              posts={data?.items || []}
              sortBy={sortBy}
              sortOrder={sortOrder}
              onSort={handleSort}
              onProcess={(postId) => processSingleMutation.mutate(postId)}
              processingPostId={processingPostId}
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
