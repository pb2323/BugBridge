/**
 * Report Detail Page
 * 
 * Detailed view of a single report with formatted Markdown content.
 */

'use client';

import { useParams } from 'next/navigation';
import Link from 'next/link';
import { DashboardLayout } from '../../../components/layout/DashboardLayout';
import { ErrorBoundary } from '../../../components/common/ErrorBoundary';
import { ReportViewer } from '../../../components/reports/ReportViewer';
import { useReport } from '../../../hooks/useReports';
import { SkeletonCard } from '../../../components/common/SkeletonLoader';
import { ArrowLeftIcon } from '@heroicons/react/24/outline';

export default function ReportDetailPage() {
  const params = useParams();
  const reportId = params.id as string;

  const { data: report, isLoading, error, refetch } = useReport(reportId);

  const handleExport = (format: 'pdf' | 'csv') => {
    if (!report) return;

    if (format === 'csv') {
      // Convert markdown to CSV (simplified)
      const csv = `Report Type,Report Date,Generated At,Content\n${report.report_type || 'N/A'},${report.report_date || 'N/A'},${report.generated_at || 'N/A'},"${(report.content || '').replace(/"/g, '""')}"`;
      const blob = new Blob([csv], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `report-${report.id}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } else if (format === 'pdf') {
      // For PDF, we'd need a library like jsPDF or html2pdf
      // For now, just open print dialog
      window.print();
    }
  };

  if (isLoading) {
    return (
      <ErrorBoundary>
        <DashboardLayout>
          <div className="space-y-6">
            <SkeletonCard />
            <SkeletonCard />
          </div>
        </DashboardLayout>
      </ErrorBoundary>
    );
  }

  if (error || !report) {
    return (
      <ErrorBoundary>
        <DashboardLayout>
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800">Error loading report. Please try again.</p>
            <div className="mt-4 flex gap-2">
              <button
                onClick={() => refetch()}
                className="rounded-md bg-red-600 px-3 py-2 text-sm font-semibold text-white hover:bg-red-500"
              >
                Retry
              </button>
              <Link
                href="/reports"
                className="rounded-md bg-gray-600 px-3 py-2 text-sm font-semibold text-white hover:bg-gray-500"
              >
                Back to List
              </Link>
            </div>
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
          <div className="flex items-center gap-4">
            <Link
              href="/reports"
              className="text-gray-400 hover:text-gray-600"
            >
              <ArrowLeftIcon className="h-6 w-6" />
            </Link>
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Report Details</h1>
              <p className="mt-1 text-sm text-gray-500">View detailed report content</p>
            </div>
          </div>

          {/* Report Viewer */}
          <ReportViewer report={report} onExport={handleExport} />
        </div>
      </DashboardLayout>
    </ErrorBoundary>
  );
}

