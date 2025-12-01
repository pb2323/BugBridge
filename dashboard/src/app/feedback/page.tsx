/**
 * Feedback Posts Listing Page
 * 
 * Main page for viewing and managing feedback posts with filtering, search, and pagination.
 */

'use client';

import { useState, useMemo } from 'react';
import { DashboardLayout } from '../../components/layout/DashboardLayout';
import { ErrorBoundary } from '../../components/common/ErrorBoundary';
import { FeedbackTable, FeedbackPost } from '../../components/feedback/FeedbackTable';
import { FeedbackFilters, FeedbackFilters as FeedbackFiltersType } from '../../components/feedback/FeedbackFilters';
import { Pagination } from '../../components/feedback/Pagination';
import { useFeedbackList } from '../../hooks/useFeedback';
import { SkeletonCard } from '../../components/common/SkeletonLoader';

export default function FeedbackPage() {
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
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Feedback Posts</h1>
              <p className="mt-1 text-sm text-gray-500">
                Manage and analyze customer feedback from Canny.io
              </p>
            </div>
            <div className="flex items-center gap-4">
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
