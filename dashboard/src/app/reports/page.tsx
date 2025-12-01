/**
 * Reports Listing Page
 * 
 * Main page for viewing and managing generated reports.
 */

'use client';

import { useState, useMemo } from 'react';
import { DashboardLayout } from '../../components/layout/DashboardLayout';
import { ErrorBoundary } from '../../components/common/ErrorBoundary';
import { ReportCard } from '../../components/reports/ReportCard';
import { ReportFilters, ReportFilters as ReportFiltersType } from '../../components/reports/ReportFilters';
import { useReportsList, useGenerateReport } from '../../hooks/useReports';
import { SkeletonCard } from '../../components/common/SkeletonLoader';
import { PlusIcon } from '@heroicons/react/24/outline';

export default function ReportsPage() {
  const [filters, setFilters] = useState<ReportFiltersType>({});
  const [showGenerateModal, setShowGenerateModal] = useState(false);

  // Convert filters to API params
  const apiParams = useMemo(() => {
    const params: any = {};
    if (filters.start_date) params.start_date = filters.start_date;
    if (filters.end_date) params.end_date = filters.end_date;
    if (filters.report_type) params.report_type = filters.report_type;
    return params;
  }, [filters]);

  const { data, isLoading, error, refetch } = useReportsList(apiParams);
  const generateMutation = useGenerateReport();

  const handleGenerateReport = () => {
    // For now, generate with default filters
    generateMutation.mutate(
      {},
      {
        onSuccess: () => {
          setShowGenerateModal(false);
          refetch();
        },
      }
    );
  };

  if (isLoading && !data) {
    return (
      <ErrorBoundary>
        <DashboardLayout>
          <div className="space-y-6">
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
              {[1, 2, 3].map((i) => (
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
            <p className="text-red-800">Error loading reports. Please try again.</p>
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
              <h1 className="text-3xl font-bold text-gray-900">Reports</h1>
              <p className="mt-1 text-sm text-gray-500">View and manage generated reports</p>
            </div>
            <button
              onClick={() => setShowGenerateModal(true)}
              className="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500"
            >
              <PlusIcon className="h-5 w-5" />
              Generate Report
            </button>
          </div>

          {/* Filters */}
          <ReportFilters filters={filters} onFiltersChange={setFilters} />

          {/* Results Summary */}
          {data && (
            <div className="text-sm text-gray-500">
              Showing {data.items.length} of {data.total} reports
            </div>
          )}

          {/* Reports Grid */}
          {data && data.items.length > 0 ? (
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
              {data.items.map((report) => (
                <ReportCard key={report.id} report={report} />
              ))}
            </div>
          ) : (
            <div className="bg-white rounded-lg shadow p-12 text-center">
              <p className="text-gray-500">No reports found. Generate a report to get started.</p>
            </div>
          )}

          {/* Generate Report Modal */}
          {showGenerateModal && (
            <div className="fixed inset-0 z-50 overflow-y-auto">
              <div className="flex min-h-full items-center justify-center p-4">
                <div className="fixed inset-0 bg-black/25" onClick={() => setShowGenerateModal(false)} />
                <div className="relative bg-white rounded-lg shadow-xl p-6 max-w-md w-full">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Generate Report</h3>
                  <p className="text-sm text-gray-500 mb-6">
                    Generate a new report with the current date range and filters.
                  </p>
                  <div className="flex items-center justify-end gap-4">
                    <button
                      onClick={() => setShowGenerateModal(false)}
                      className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-semibold text-gray-700 shadow-sm hover:bg-gray-50"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleGenerateReport}
                      disabled={generateMutation.isPending}
                      className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {generateMutation.isPending ? 'Generating...' : 'Generate'}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </DashboardLayout>
    </ErrorBoundary>
  );
}
