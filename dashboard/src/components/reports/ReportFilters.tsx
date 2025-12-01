/**
 * Report Filters Component
 * 
 * Filter panel for reports with date range and type filtering.
 */

'use client';

import { useState } from 'react';
import { XMarkIcon, FunnelIcon } from '@heroicons/react/24/outline';

export interface ReportFilters {
  start_date?: string;
  end_date?: string;
  report_type?: string;
}

interface ReportFiltersProps {
  filters: ReportFilters;
  onFiltersChange: (filters: ReportFilters) => void;
}

export function ReportFilters({ filters, onFiltersChange }: ReportFiltersProps) {
  const [isOpen, setIsOpen] = useState(false);

  const updateFilter = <K extends keyof ReportFilters>(key: K, value: ReportFilters[K]) => {
    onFiltersChange({ ...filters, [key]: value });
  };

  const clearFilter = (key: keyof ReportFilters) => {
    const newFilters = { ...filters };
    delete newFilters[key];
    onFiltersChange(newFilters);
  };

  const clearAllFilters = () => {
    onFiltersChange({});
  };

  const hasActiveFilters = Object.keys(filters).length > 0;

  return (
    <div className="bg-white rounded-lg shadow mb-6">
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FunnelIcon className="h-5 w-5 text-gray-400" />
            <h3 className="text-sm font-medium text-gray-900">Filters</h3>
            {hasActiveFilters && (
              <span className="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800">
                {Object.keys(filters).length} active
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {hasActiveFilters && (
              <button
                onClick={clearAllFilters}
                className="text-sm text-gray-500 hover:text-gray-700"
              >
                Clear all
              </button>
            )}
            <button
              onClick={() => setIsOpen(!isOpen)}
              className="text-sm text-indigo-600 hover:text-indigo-900"
            >
              {isOpen ? 'Hide' : 'Show'} filters
            </button>
          </div>
        </div>
      </div>

      {isOpen && (
        <div className="p-4 space-y-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            {/* Start Date */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Start Date</label>
              <input
                type="date"
                value={filters.start_date || ''}
                onChange={(e) => updateFilter('start_date', e.target.value || undefined)}
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
              />
            </div>

            {/* End Date */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">End Date</label>
              <input
                type="date"
                value={filters.end_date || ''}
                onChange={(e) => updateFilter('end_date', e.target.value || undefined)}
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
              />
            </div>

            {/* Report Type */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Report Type</label>
              <select
                value={filters.report_type || ''}
                onChange={(e) => updateFilter('report_type', e.target.value || undefined)}
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
              >
                <option value="">All Types</option>
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
              </select>
            </div>
          </div>

          {/* Active Filters Tags */}
          {hasActiveFilters && (
            <div className="pt-4 border-t border-gray-200">
              <div className="flex flex-wrap gap-2">
                {filters.start_date && (
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                    Start: {filters.start_date}
                    <button onClick={() => clearFilter('start_date')} className="hover:text-gray-600">
                      <XMarkIcon className="h-3 w-3" />
                    </button>
                  </span>
                )}
                {filters.end_date && (
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                    End: {filters.end_date}
                    <button onClick={() => clearFilter('end_date')} className="hover:text-gray-600">
                      <XMarkIcon className="h-3 w-3" />
                    </button>
                  </span>
                )}
                {filters.report_type && (
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                    Type: {filters.report_type}
                    <button onClick={() => clearFilter('report_type')} className="hover:text-gray-600">
                      <XMarkIcon className="h-3 w-3" />
                    </button>
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

