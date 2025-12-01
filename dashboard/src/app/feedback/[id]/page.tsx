/**
 * Feedback Post Detail Page
 * 
 * Detailed view of a single feedback post with analysis results, Jira ticket info, and workflow status.
 */

'use client';

import { use } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { DashboardLayout } from '../../../components/layout/DashboardLayout';
import { ErrorBoundary } from '../../../components/common/ErrorBoundary';
import { useFeedbackPost } from '../../../hooks/useFeedback';
import { formatDistanceToNow, format } from 'date-fns';
import {
  ArrowLeftIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ClockIcon,
  TagIcon,
  UserIcon,
  CalendarIcon,
  ChartBarIcon,
} from '@heroicons/react/24/outline';
import { SkeletonCard } from '../../../components/common/SkeletonLoader';

export default function FeedbackDetailPage() {
  const params = useParams();
  const postId = params.id as string;

  const { data: post, isLoading, error, refetch } = useFeedbackPost(postId);

  if (isLoading) {
    return (
      <ErrorBoundary>
        <DashboardLayout>
          <div className="space-y-6">
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </div>
        </DashboardLayout>
      </ErrorBoundary>
    );
  }

  if (error || !post) {
    return (
      <ErrorBoundary>
        <DashboardLayout>
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800">Error loading feedback post. Please try again.</p>
            <div className="mt-4 flex gap-2">
              <button
                onClick={() => refetch()}
                className="rounded-md bg-red-600 px-3 py-2 text-sm font-semibold text-white hover:bg-red-500"
              >
                Retry
              </button>
              <Link
                href="/feedback"
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
    <ErrorBoundary>
      <DashboardLayout>
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link
                href="/feedback"
                className="text-gray-400 hover:text-gray-600"
              >
                <ArrowLeftIcon className="h-6 w-6" />
              </Link>
              <div>
                <h1 className="text-3xl font-bold text-gray-900">{post.title}</h1>
                <p className="mt-1 text-sm text-gray-500">
                  Collected {formatDistanceToNow(new Date(post.collected_at), { addSuffix: true })}
                </p>
              </div>
            </div>
            {post.url && (
              <a
                href={post.url}
                target="_blank"
                rel="noopener noreferrer"
                className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500"
              >
                View on Canny
              </a>
            )}
          </div>

          {/* Main Content */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            {/* Left Column - Main Content */}
            <div className="lg:col-span-2 space-y-6">
              {/* Post Content */}
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Post Content</h2>
                <div className="prose max-w-none">
                  <p className="text-gray-700 whitespace-pre-wrap">{post.content}</p>
                </div>
              </div>

              {/* Analysis Results */}
              {(post.is_bug !== undefined || post.sentiment || post.priority_score !== undefined) && (
                <div className="bg-white rounded-lg shadow p-6">
                  <div className="flex items-center gap-2 mb-4">
                    <ChartBarIcon className="h-5 w-5 text-gray-400" />
                    <h2 className="text-lg font-semibold text-gray-900">Analysis Results</h2>
                  </div>
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                    {post.is_bug !== undefined && (
                      <div>
                        <p className="text-sm text-gray-500">Type</p>
                        <p className="mt-1 text-sm font-medium text-gray-900">
                          {post.is_bug ? (
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                              Bug
                            </span>
                          ) : (
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                              Feature Request
                            </span>
                          )}
                        </p>
                        {post.bug_severity && (
                          <p className="mt-1 text-xs text-gray-500">Severity: {post.bug_severity}</p>
                        )}
                      </div>
                    )}
                    {post.sentiment && (
                      <div>
                        <p className="text-sm text-gray-500">Sentiment</p>
                        <p className="mt-1">
                          <span
                            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getSentimentColor(
                              post.sentiment
                            )}`}
                          >
                            {post.sentiment}
                          </span>
                        </p>
                      </div>
                    )}
                    {post.priority_score !== undefined && (
                      <div>
                        <p className="text-sm text-gray-500">Priority Score</p>
                        <p className="mt-1">
                          <span
                            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getPriorityColor(
                              post.priority_score
                            )}`}
                          >
                            {post.priority_score.toFixed(1)}
                          </span>
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Jira Ticket Information */}
              {post.jira_ticket_key && (
                <div className="bg-white rounded-lg shadow p-6">
                  <h2 className="text-lg font-semibold text-gray-900 mb-4">Jira Ticket</h2>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-500">Ticket Key</span>
                      <a
                        href={`/jira-tickets/${post.jira_ticket_key}`}
                        className="text-sm font-medium text-indigo-600 hover:text-indigo-900"
                      >
                        {post.jira_ticket_key}
                      </a>
                    </div>
                    {post.jira_ticket_status && (
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-500">Status</span>
                        <span className="text-sm font-medium text-gray-900">{post.jira_ticket_status}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Right Column - Metadata */}
            <div className="space-y-6">
              {/* Status Card */}
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-sm font-medium text-gray-500 mb-4">Status</h3>
                <div className="flex items-center gap-2">
                  {getStatusIcon(post.status)}
                  <span className="text-sm font-medium text-gray-900">{post.status || 'Unknown'}</span>
                </div>
              </div>

              {/* Metadata */}
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-sm font-medium text-gray-500 mb-4">Metadata</h3>
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <UserIcon className="h-4 w-4 text-gray-400" />
                    <div>
                      <p className="text-xs text-gray-500">Author</p>
                      <p className="text-sm font-medium text-gray-900">{post.author_name || 'Unknown'}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <CalendarIcon className="h-4 w-4 text-gray-400" />
                    <div>
                      <p className="text-xs text-gray-500">Created</p>
                      <p className="text-sm font-medium text-gray-900">
                        {format(new Date(post.created_at), 'MMM d, yyyy')}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <CalendarIcon className="h-4 w-4 text-gray-400" />
                    <div>
                      <p className="text-xs text-gray-500">Collected</p>
                      <p className="text-sm font-medium text-gray-900">
                        {format(new Date(post.collected_at), 'MMM d, yyyy')}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <ChartBarIcon className="h-4 w-4 text-gray-400" />
                    <div>
                      <p className="text-xs text-gray-500">Votes</p>
                      <p className="text-sm font-medium text-gray-900">{post.votes}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <ChartBarIcon className="h-4 w-4 text-gray-400" />
                    <div>
                      <p className="text-xs text-gray-500">Comments</p>
                      <p className="text-sm font-medium text-gray-900">{post.comments_count}</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Tags */}
              {post.tags && post.tags.length > 0 && (
                <div className="bg-white rounded-lg shadow p-6">
                  <div className="flex items-center gap-2 mb-4">
                    <TagIcon className="h-4 w-4 text-gray-400" />
                    <h3 className="text-sm font-medium text-gray-500">Tags</h3>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {post.tags.map((tag) => (
                      <span
                        key={tag}
                        className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </DashboardLayout>
    </ErrorBoundary>
  );
}

