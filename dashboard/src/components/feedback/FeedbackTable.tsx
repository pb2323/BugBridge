/**
 * Feedback Table Component
 * 
 * Table component for displaying feedback posts with sorting and actions.
 */

'use client';

import Link from 'next/link';
import { formatDistanceToNow } from 'date-fns';
import {
  ArrowUpIcon,
  ArrowDownIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
} from '@heroicons/react/24/outline';

export interface FeedbackPost {
  id: string;
  canny_post_id: string;
  board_id: string;
  title: string;
  content: string;
  author_id?: string;
  author_name?: string;
  votes: number;
  comments_count: number;
  status?: string;
  url?: string;
  tags: string[];
  created_at: string;
  updated_at: string;
  collected_at: string;
  is_bug?: boolean;
  bug_severity?: string;
  sentiment?: string;
  priority_score?: number;
  jira_ticket_key?: string;
  jira_ticket_status?: string;
}

interface FeedbackTableProps {
  posts: FeedbackPost[];
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
  onSort?: (field: string) => void;
}

export function FeedbackTable({ posts, sortBy, sortOrder, onSort }: FeedbackTableProps) {
  const getSortIcon = (field: string) => {
    if (sortBy !== field) {
      return null;
    }
    return sortOrder === 'asc' ? (
      <ArrowUpIcon className="h-4 w-4 inline ml-1" />
    ) : (
      <ArrowDownIcon className="h-4 w-4 inline ml-1" />
    );
  };

  const getSentimentColor = (sentiment?: string) => {
    switch (sentiment?.toLowerCase()) {
      case 'positive':
        return 'text-green-600 bg-green-50';
      case 'negative':
        return 'text-red-600 bg-red-50';
      case 'neutral':
        return 'text-gray-600 bg-gray-50';
      default:
        return 'text-gray-400 bg-gray-50';
    }
  };

  const getPriorityColor = (score?: number) => {
    if (!score) return 'text-gray-400 bg-gray-50';
    if (score >= 8) return 'text-red-600 bg-red-50';
    if (score >= 6) return 'text-yellow-600 bg-yellow-50';
    return 'text-blue-600 bg-blue-50';
  };

  const getStatusIcon = (status?: string) => {
    switch (status?.toLowerCase()) {
      case 'resolved':
      case 'done':
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />;
      case 'notified':
        return <CheckCircleIcon className="h-5 w-5 text-blue-500" />;
      case 'analyzed':
        return <ClockIcon className="h-5 w-5 text-yellow-500" />;
      case 'collected':
        return <ClockIcon className="h-5 w-5 text-gray-500" />;
      default:
        return <ExclamationTriangleIcon className="h-5 w-5 text-gray-400" />;
    }
  };

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th
              className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
              onClick={() => onSort?.('collected_at')}
            >
              Date {getSortIcon('collected_at')}
            </th>
            <th
              className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
              onClick={() => onSort?.('title')}
            >
              Title {getSortIcon('title')}
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Type
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Sentiment
            </th>
            <th
              className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
              onClick={() => onSort?.('priority_score')}
            >
              Priority {getSortIcon('priority_score')}
            </th>
            <th
              className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
              onClick={() => onSort?.('votes')}
            >
              Votes {getSortIcon('votes')}
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Jira Ticket
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Status
            </th>
            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {posts.length === 0 ? (
            <tr>
              <td colSpan={9} className="px-6 py-8 text-center text-sm text-gray-500">
                No feedback posts found
              </td>
            </tr>
          ) : (
            posts.map((post) => (
              <tr key={post.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {formatDistanceToNow(new Date(post.collected_at), { addSuffix: true })}
                </td>
                <td className="px-6 py-4">
                  <div className="text-sm font-medium text-gray-900 max-w-xs truncate">{post.title}</div>
                  <div className="text-xs text-gray-500 mt-1">
                    {post.author_name || 'Unknown'} • {post.comments_count} comments
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {post.is_bug ? (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                      Bug
                    </span>
                  ) : (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                      Feature
                    </span>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {post.sentiment ? (
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getSentimentColor(
                        post.sentiment
                      )}`}
                    >
                      {post.sentiment}
                    </span>
                  ) : (
                    <span className="text-xs text-gray-400">-</span>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {post.priority_score !== undefined ? (
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getPriorityColor(
                        post.priority_score
                      )}`}
                    >
                      {post.priority_score.toFixed(1)}
                    </span>
                  ) : (
                    <span className="text-xs text-gray-400">-</span>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{post.votes}</td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {post.jira_ticket_key ? (
                    <a
                      href={`/jira-tickets/${post.jira_ticket_key}`}
                      className="text-sm text-indigo-600 hover:text-indigo-900"
                    >
                      {post.jira_ticket_key}
                    </a>
                  ) : (
                    <span className="text-xs text-gray-400">-</span>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center gap-2">
                    {getStatusIcon(post.status)}
                    <span className="text-sm text-gray-500">{post.status || 'Unknown'}</span>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  <Link
                    href={`/feedback/${post.id}`}
                    className="text-indigo-600 hover:text-indigo-900"
                  >
                    View
                  </Link>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

