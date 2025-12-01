/**
 * Priority Items List Component
 * 
 * List of high-priority items requiring attention.
 */

'use client';

import Link from 'next/link';
import { ExclamationTriangleIcon } from '@heroicons/react/24/outline';

interface PriorityItem {
  title: string;
  priority_score: number;
  priority: string;
  post_id: string;
}

interface PriorityListProps {
  items: PriorityItem[];
  maxItems?: number;
}

export function PriorityList({ items, maxItems = 10 }: PriorityListProps) {
  const displayItems = items.slice(0, maxItems);

  const getPriorityColor = (priority: string) => {
    switch (priority.toLowerCase()) {
      case 'critical':
      case 'high':
        return 'text-red-600 bg-red-50';
      case 'medium':
        return 'text-yellow-600 bg-yellow-50';
      case 'low':
        return 'text-blue-600 bg-blue-50';
      default:
        return 'text-gray-600 bg-gray-50';
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Priority Items</h3>
        <ExclamationTriangleIcon className="h-5 w-5 text-yellow-500" />
      </div>
      <div className="space-y-3">
        {displayItems.length === 0 ? (
          <p className="text-sm text-gray-500 text-center py-4">No priority items</p>
        ) : (
          displayItems.map((item) => (
            <Link
              key={item.post_id}
              href={`/feedback/${item.post_id}`}
              className="block p-3 rounded-lg border border-gray-200 hover:border-indigo-300 hover:bg-indigo-50 transition-colors"
            >
              <div className="flex items-center justify-between">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">{item.title}</p>
                  <div className="mt-1 flex items-center gap-2">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${getPriorityColor(
                        item.priority
                      )}`}
                    >
                      {item.priority}
                    </span>
                    <span className="text-xs text-gray-500">Score: {item.priority_score.toFixed(1)}</span>
                  </div>
                </div>
              </div>
            </Link>
          ))
        )}
      </div>
    </div>
  );
}

