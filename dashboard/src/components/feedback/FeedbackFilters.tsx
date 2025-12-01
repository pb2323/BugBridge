/**
 * Feedback Filters Component
 * 
 * Filter panel for feedback posts with various filter options.
 */

'use client';

import { useState } from 'react';
import { XMarkIcon, FunnelIcon } from '@heroicons/react/24/outline';

export interface FeedbackFilters {
  board_ids?: string[];
  tags?: string[];
  status?: string[];
  search?: string;
  is_bug?: boolean;
  sentiment?: string;
  min_priority?: number;
  min_votes?: number;
  has_jira_ticket?: boolean;
  start_date?: string;
  end_date?: string;
}

interface FeedbackFiltersProps {
  filters: FeedbackFilters;
  onFiltersChange: (filters: FeedbackFilters) => void;
  availableTags?: string[];
  availableBoards?: Array<{ id: string; name: string }>;
}

export function FeedbackFilters({
  filters,
  onFiltersChange,
  availableTags = [],
  availableBoards = [],
}: FeedbackFiltersProps) {
  const [isOpen, setIsOpen] = useState(false);

  const updateFilter = <K extends keyof FeedbackFilters>(key: K, value: FeedbackFilters[K]) => {
    onFiltersChange({ ...filters, [key]: value });
  };

  const clearFilter = (key: keyof FeedbackFilters) => {
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
          {/* Search */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Search</label>
            <input
              type="text"
              value={filters.search || ''}
              onChange={(e) => updateFilter('search', e.target.value || undefined)}
              placeholder="Search by title or content..."
              className="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
            />
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {/* Date Range */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Start Date</label>
              <input
                type="date"
                value={filters.start_date || ''}
                onChange={(e) => updateFilter('start_date', e.target.value || undefined)}
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">End Date</label>
              <input
                type="date"
                value={filters.end_date || ''}
                onChange={(e) => updateFilter('end_date', e.target.value || undefined)}
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
              />
            </div>

            {/* Bug vs Feature */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
              <select
                value={filters.is_bug === undefined ? '' : filters.is_bug ? 'bug' : 'feature'}
                onChange={(e) => {
                  if (e.target.value === '') {
                    clearFilter('is_bug');
                  } else {
                    updateFilter('is_bug', e.target.value === 'bug');
                  }
                }}
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
              >
                <option value="">All</option>
                <option value="bug">Bugs</option>
                <option value="feature">Features</option>
              </select>
            </div>

            {/* Sentiment */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Sentiment</label>
              <select
                value={filters.sentiment || ''}
                onChange={(e) => updateFilter('sentiment', e.target.value || undefined)}
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
              >
                <option value="">All</option>
                <option value="positive">Positive</option>
                <option value="neutral">Neutral</option>
                <option value="negative">Negative</option>
              </select>
            </div>

            {/* Priority Score */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Min Priority Score</label>
              <input
                type="number"
                min="0"
                max="10"
                step="0.1"
                value={filters.min_priority || ''}
                onChange={(e) =>
                  updateFilter('min_priority', e.target.value ? parseFloat(e.target.value) : undefined)
                }
                placeholder="0.0"
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
              />
            </div>

            {/* Min Votes */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Min Votes</label>
              <input
                type="number"
                min="0"
                value={filters.min_votes || ''}
                onChange={(e) =>
                  updateFilter('min_votes', e.target.value ? parseInt(e.target.value) : undefined)
                }
                placeholder="0"
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
              />
            </div>

            {/* Jira Ticket */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Jira Ticket</label>
              <select
                value={filters.has_jira_ticket === undefined ? '' : filters.has_jira_ticket ? 'yes' : 'no'}
                onChange={(e) => {
                  if (e.target.value === '') {
                    clearFilter('has_jira_ticket');
                  } else {
                    updateFilter('has_jira_ticket', e.target.value === 'yes');
                  }
                }}
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
              >
                <option value="">All</option>
                <option value="yes">Has Ticket</option>
                <option value="no">No Ticket</option>
              </select>
            </div>

            {/* Status */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
              <select
                value={filters.status?.[0] || ''}
                onChange={(e) => {
                  if (e.target.value === '') {
                    clearFilter('status');
                  } else {
                    updateFilter('status', [e.target.value]);
                  }
                }}
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
              >
                <option value="">All</option>
                <option value="collected">Collected</option>
                <option value="analyzed">Analyzed</option>
                <option value="ticket_created">Ticket Created</option>
                <option value="resolved">Resolved</option>
                <option value="notified">Notified</option>
              </select>
            </div>
          </div>

          {/* Active Filters Tags */}
          {hasActiveFilters && (
            <div className="pt-4 border-t border-gray-200">
              <div className="flex flex-wrap gap-2">
                {filters.search && (
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                    Search: {filters.search}
                    <button onClick={() => clearFilter('search')} className="hover:text-gray-600">
                      <XMarkIcon className="h-3 w-3" />
                    </button>
                  </span>
                )}
                {filters.is_bug !== undefined && (
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                    Type: {filters.is_bug ? 'Bug' : 'Feature'}
                    <button onClick={() => clearFilter('is_bug')} className="hover:text-gray-600">
                      <XMarkIcon className="h-3 w-3" />
                    </button>
                  </span>
                )}
                {filters.sentiment && (
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                    Sentiment: {filters.sentiment}
                    <button onClick={() => clearFilter('sentiment')} className="hover:text-gray-600">
                      <XMarkIcon className="h-3 w-3" />
                    </button>
                  </span>
                )}
                {filters.min_priority !== undefined && (
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                    Min Priority: {filters.min_priority}
                    <button onClick={() => clearFilter('min_priority')} className="hover:text-gray-600">
                      <XMarkIcon className="h-3 w-3" />
                    </button>
                  </span>
                )}
                {filters.min_votes !== undefined && (
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                    Min Votes: {filters.min_votes}
                    <button onClick={() => clearFilter('min_votes')} className="hover:text-gray-600">
                      <XMarkIcon className="h-3 w-3" />
                    </button>
                  </span>
                )}
                {filters.has_jira_ticket !== undefined && (
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                    Jira: {filters.has_jira_ticket ? 'Has Ticket' : 'No Ticket'}
                    <button onClick={() => clearFilter('has_jira_ticket')} className="hover:text-gray-600">
                      <XMarkIcon className="h-3 w-3" />
                    </button>
                  </span>
                )}
                {filters.status && filters.status.length > 0 && (
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                    Status: {filters.status.join(', ')}
                    <button onClick={() => clearFilter('status')} className="hover:text-gray-600">
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

