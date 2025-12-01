/**
 * Burning Issues List Component
 * 
 * List of high-priority burning issues requiring immediate attention.
 */

'use client';

import Link from 'next/link';
import { FireIcon } from '@heroicons/react/24/solid';

interface BurningIssue {
  title: string;
  priority_score: number;
  priority: string;
  post_id: string;
  votes?: number;
  sentiment?: string;
}

interface BurningIssuesListProps {
  items: BurningIssue[];
  maxItems?: number;
}

export function BurningIssuesList({ items, maxItems = 5 }: BurningIssuesListProps) {
  const displayItems = items.slice(0, maxItems);

  return (
    <div className="bg-white rounded-lg shadow p-6 border-l-4 border-red-500">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <FireIcon className="h-6 w-6 text-red-500" />
          <h3 className="text-lg font-semibold text-gray-900">Burning Issues</h3>
        </div>
        <span className="text-sm text-gray-500">{items.length} total</span>
      </div>
      <div className="space-y-3">
        {displayItems.length === 0 ? (
          <p className="text-sm text-gray-500 text-center py-4">No burning issues</p>
        ) : (
          displayItems.map((item) => (
            <Link
              key={item.post_id}
              href={`/feedback/${item.post_id}`}
              className="block p-3 rounded-lg border border-red-200 bg-red-50 hover:border-red-300 hover:bg-red-100 transition-colors"
            >
              <div className="flex items-center justify-between">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">{item.title}</p>
                  <div className="mt-1 flex items-center gap-3">
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium text-red-700 bg-red-100">
                      {item.priority}
                    </span>
                    <span className="text-xs text-gray-500">Score: {item.priority_score.toFixed(1)}</span>
                    {item.votes !== undefined && (
                      <span className="text-xs text-gray-500">Votes: {item.votes}</span>
                    )}
                    {item.sentiment && (
                      <span className="text-xs text-gray-500">Sentiment: {item.sentiment}</span>
                    )}
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

