/**
 * Report Card Component
 * 
 * Card component for displaying report summary in the listing.
 */

'use client';

import Link from 'next/link';
import { format } from 'date-fns';
import { DocumentTextIcon, CalendarIcon, ChartBarIcon } from '@heroicons/react/24/outline';

export interface Report {
  id: string;
  report_type?: string;
  report_date?: string;
  generated_at?: string;
  content?: string;
  summary?: string;
  metrics?: Record<string, any>;
}

interface ReportCardProps {
  report: Report;
}

export function ReportCard({ report }: ReportCardProps) {
  return (
    <Link
      href={`/reports/${report.id}`}
      className="block bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow border border-gray-200 hover:border-indigo-300"
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <DocumentTextIcon className="h-5 w-5 text-indigo-600" />
            <h3 className="text-lg font-semibold text-gray-900">
              {report.report_type === 'daily' ? 'Daily Report' : report.report_type}
            </h3>
          </div>
          <div className="flex items-center gap-4 text-sm text-gray-500 mb-3">
            {report.report_date && (
              <div className="flex items-center gap-1">
                <CalendarIcon className="h-4 w-4" />
                <span>{format(new Date(report.report_date), 'MMM d, yyyy')}</span>
              </div>
            )}
            {report.generated_at && (
              <div className="flex items-center gap-1">
                <ChartBarIcon className="h-4 w-4" />
                <span>Generated {format(new Date(report.generated_at), 'MMM d, yyyy HH:mm')}</span>
              </div>
            )}
          </div>
          {report.summary && (
            <p className="text-sm text-gray-600 line-clamp-2">{report.summary}</p>
          )}
        </div>
        <div className="ml-4">
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800">
            View
          </span>
        </div>
      </div>
    </Link>
  );
}

