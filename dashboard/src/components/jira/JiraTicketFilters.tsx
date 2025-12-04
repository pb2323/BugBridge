/**
 * Jira Ticket Filters Component
 * 
 * Filter panel for Jira tickets with various filter options.
 */

'use client';

import { useState } from 'react';
import { XMarkIcon } from '@heroicons/react/24/outline';

export interface JiraTicketFilters {
  project_keys?: string[];
  statuses?: string[];
  priorities?: string[];
  assignee?: string;
  resolved_only?: boolean;
  unresolved_only?: boolean;
  has_feedback?: boolean;
}

interface JiraTicketFiltersProps {
  filters: JiraTicketFilters;
  onFiltersChange: (filters: JiraTicketFilters) => void;
}

export function JiraTicketFilters({ filters, onFiltersChange }: JiraTicketFiltersProps) {
  const [isOpen, setIsOpen] = useState(false);

  const updateFilter = <K extends keyof JiraTicketFilters>(
    key: K,
    value: JiraTicketFilters[K]
  ) => {
    onFiltersChange({
      ...filters,
      [key]: value,
    });
  };

  const clearFilters = () => {
    onFiltersChange({});
  };

  const hasActiveFilters = Object.keys(filters).length > 0;

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="flex items-center justify-between mb-4">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="text-sm font-medium text-gray-700 hover:text-gray-900"
        >
          {isOpen ? 'Hide' : 'Show'} Filters
        </button>
        {hasActiveFilters && (
          <button
            onClick={clearFilters}
            className="text-sm text-indigo-600 hover:text-indigo-800"
          >
            Clear All
          </button>
        )}
      </div>

      {isOpen && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {/* Project Keys */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Project Keys
            </label>
            <input
              type="text"
              placeholder="PROJ, DEV, ..."
              value={filters.project_keys?.join(', ') || ''}
              onChange={(e) =>
                updateFilter(
                  'project_keys',
                  e.target.value
                    .split(',')
                    .map((s) => s.trim())
                    .filter((s) => s.length > 0)
                )
              }
              className="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
            />
          </div>

          {/* Statuses */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Statuses
            </label>
            <input
              type="text"
              placeholder="To Do, In Progress, Done, ..."
              value={filters.statuses?.join(', ') || ''}
              onChange={(e) =>
                updateFilter(
                  'statuses',
                  e.target.value
                    .split(',')
                    .map((s) => s.trim())
                    .filter((s) => s.length > 0)
                )
              }
              className="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
            />
          </div>

          {/* Priorities */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Priorities
            </label>
            <input
              type="text"
              placeholder="Highest, High, Medium, ..."
              value={filters.priorities?.join(', ') || ''}
              onChange={(e) =>
                updateFilter(
                  'priorities',
                  e.target.value
                    .split(',')
                    .map((s) => s.trim())
                    .filter((s) => s.length > 0)
                )
              }
              className="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
            />
          </div>

          {/* Assignee */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Assignee
            </label>
            <input
              type="text"
              placeholder="Username or email"
              value={filters.assignee || ''}
              onChange={(e) => updateFilter('assignee', e.target.value || undefined)}
              className="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
            />
          </div>

          {/* Resolution Status */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Resolution Status
            </label>
            <select
              value={
                filters.resolved_only
                  ? 'resolved'
                  : filters.unresolved_only
                  ? 'unresolved'
                  : 'all'
              }
              onChange={(e) => {
                if (e.target.value === 'resolved') {
                  updateFilter('resolved_only', true);
                  updateFilter('unresolved_only', undefined);
                } else if (e.target.value === 'unresolved') {
                  updateFilter('unresolved_only', true);
                  updateFilter('resolved_only', undefined);
                } else {
                  updateFilter('resolved_only', undefined);
                  updateFilter('unresolved_only', undefined);
                }
              }}
              className="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
            >
              <option value="all">All</option>
              <option value="resolved">Resolved Only</option>
              <option value="unresolved">Unresolved Only</option>
            </select>
          </div>

          {/* Has Feedback */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Feedback Linkage
            </label>
            <select
              value={
                filters.has_feedback === true
                  ? 'yes'
                  : filters.has_feedback === false
                  ? 'no'
                  : 'all'
              }
              onChange={(e) => {
                if (e.target.value === 'yes') {
                  updateFilter('has_feedback', true);
                } else if (e.target.value === 'no') {
                  updateFilter('has_feedback', false);
                } else {
                  updateFilter('has_feedback', undefined);
                }
              }}
              className="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
            >
              <option value="all">All</option>
              <option value="yes">Has Feedback</option>
              <option value="no">No Feedback</option>
            </select>
          </div>
        </div>
      )}
    </div>
  );
}

