/**
 * Report Viewer Component
 * 
 * Component for displaying formatted Markdown reports.
 */

'use client';

import { useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { format } from 'date-fns';
import { DocumentTextIcon, ArrowDownTrayIcon } from '@heroicons/react/24/outline';

interface ReportViewerProps {
  report: {
    id: string;
    report_type?: string;
    report_date?: string;
    generated_at?: string;
    content?: string;
    summary?: string;
  };
  onExport?: (format: 'pdf' | 'csv') => void;
}

export function ReportViewer({ report, onExport }: ReportViewerProps) {
  const contentRef = useRef<HTMLDivElement>(null);

  const handleExport = (format: 'pdf' | 'csv') => {
    if (onExport) {
      onExport(format);
    } else {
      // Default export behavior
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
    }
  };

  return (
    <div className="bg-white rounded-lg shadow">
      {/* Header */}
      <div className="border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <DocumentTextIcon className="h-6 w-6 text-indigo-600" />
            <div>
              <h2 className="text-xl font-semibold text-gray-900">
                {report.report_type === 'daily' ? 'Daily Report' : report.report_type || 'Report'}
              </h2>
              <p className="text-sm text-gray-500">
                {report.report_date && format(new Date(report.report_date), 'MMMM d, yyyy')}
                {report.report_date && report.generated_at && ' • '}
                {report.generated_at && `Generated ${format(new Date(report.generated_at), 'MMM d, yyyy HH:mm')}`}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => handleExport('csv')}
              className="inline-flex items-center gap-2 rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-700 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50"
            >
              <ArrowDownTrayIcon className="h-4 w-4" />
              Export CSV
            </button>
            <button
              onClick={() => handleExport('pdf')}
              className="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500"
            >
              <ArrowDownTrayIcon className="h-4 w-4" />
              Export PDF
            </button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div ref={contentRef} className="px-6 py-6 prose max-w-none">
        {report.content ? (
          <ReactMarkdown
          components={{
            h1: ({ node, ...props }) => <h1 className="text-3xl font-bold text-gray-900 mb-4" {...props} />,
            h2: ({ node, ...props }) => <h2 className="text-2xl font-semibold text-gray-900 mt-6 mb-3" {...props} />,
            h3: ({ node, ...props }) => <h3 className="text-xl font-semibold text-gray-900 mt-4 mb-2" {...props} />,
            p: ({ node, ...props }) => <p className="text-gray-700 mb-4" {...props} />,
            ul: ({ node, ...props }) => <ul className="list-disc list-inside mb-4 space-y-1" {...props} />,
            ol: ({ node, ...props }) => <ol className="list-decimal list-inside mb-4 space-y-1" {...props} />,
            li: ({ node, ...props }) => <li className="text-gray-700" {...props} />,
            code: ({ node, ...props }) => (
              <code className="bg-gray-100 px-1.5 py-0.5 rounded text-sm font-mono text-gray-800" {...props} />
            ),
            pre: ({ node, ...props }) => (
              <pre className="bg-gray-100 p-4 rounded-lg overflow-x-auto mb-4" {...props} />
            ),
            table: ({ node, ...props }) => (
              <div className="overflow-x-auto mb-4">
                <table className="min-w-full divide-y divide-gray-200" {...props} />
              </div>
            ),
            thead: ({ node, ...props }) => <thead className="bg-gray-50" {...props} />,
            th: ({ node, ...props }) => (
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider" {...props} />
            ),
            td: ({ node, ...props }) => (
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900" {...props} />
            ),
            blockquote: ({ node, ...props }) => (
              <blockquote className="border-l-4 border-indigo-500 pl-4 italic text-gray-600 mb-4" {...props} />
            ),
          }}
        >
          {report.content}
        </ReactMarkdown>
        ) : (
          <p className="text-gray-500">No content available for this report.</p>
        )}
      </div>
    </div>
  );
}

