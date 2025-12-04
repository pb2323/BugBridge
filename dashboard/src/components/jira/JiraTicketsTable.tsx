/**
 * Jira Tickets Table Component
 * 
 * Table component for displaying Jira tickets with sorting and actions.
 */

'use client';

import Link from 'next/link';
import { formatDistanceToNow } from 'date-fns';
import {
  ArrowUpIcon,
  ArrowDownIcon,
  CheckCircleIcon,
  ClockIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';
import { JiraTicket } from '../../services/api/jira';
import { getJiraTicketUrl } from '@/lib/jira-utils';

interface JiraTicketsTableProps {
  tickets: JiraTicket[];
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
  onSort?: (field: string) => void;
}

function getStatusColor(status?: string): string {
  if (!status) return 'bg-gray-100 text-gray-800';
  
  const statusLower = status.toLowerCase();
  if (statusLower.includes('done') || statusLower.includes('resolved') || statusLower.includes('closed')) {
    return 'bg-green-100 text-green-800';
  }
  if (statusLower.includes('progress')) {
    return 'bg-blue-100 text-blue-800';
  }
  if (statusLower.includes('todo') || statusLower.includes('open')) {
    return 'bg-gray-100 text-gray-800';
  }
  return 'bg-yellow-100 text-yellow-800';
}

function getPriorityColor(priority?: string): string {
  if (!priority) return 'bg-gray-100 text-gray-800';
  
  const priorityLower = priority.toLowerCase();
  if (priorityLower.includes('highest') || priorityLower.includes('critical')) {
    return 'bg-red-100 text-red-800';
  }
  if (priorityLower.includes('high')) {
    return 'bg-orange-100 text-orange-800';
  }
  if (priorityLower.includes('medium')) {
    return 'bg-yellow-100 text-yellow-800';
  }
  return 'bg-gray-100 text-gray-800';
}

export function JiraTicketsTable({ tickets, sortBy, sortOrder, onSort }: JiraTicketsTableProps) {
  const handleSort = (field: string) => {
    if (onSort) {
      onSort(field);
    }
  };

  const SortableHeader = ({ field, children }: { field: string; children: React.ReactNode }) => {
    const isSorted = sortBy === field;
    const isAsc = isSorted && sortOrder === 'asc';
    
    return (
      <th
        scope="col"
        className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-50"
        onClick={() => handleSort(field)}
      >
        <div className="flex items-center gap-1">
          {children}
          {isSorted && (
            isAsc ? (
              <ArrowUpIcon className="h-4 w-4" />
            ) : (
              <ArrowDownIcon className="h-4 w-4" />
            )
          )}
        </div>
      </th>
    );
  };

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <SortableHeader field="jira_issue_key">Ticket Key</SortableHeader>
            <SortableHeader field="jira_project_key">Project</SortableHeader>
            <SortableHeader field="status">Status</SortableHeader>
            <SortableHeader field="priority">Priority</SortableHeader>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Assignee
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Feedback Post
            </th>
            <SortableHeader field="created_at">Created</SortableHeader>
            <SortableHeader field="resolved_at">Resolved</SortableHeader>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {tickets.length === 0 ? (
            <tr>
              <td colSpan={8} className="px-6 py-8 text-center text-sm text-gray-500">
                No Jira tickets found.
              </td>
            </tr>
          ) : (
            tickets.map((ticket) => (
              <tr key={ticket.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap">
                  <a
                    href={getJiraTicketUrl(ticket.jira_issue_key)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm font-medium text-indigo-600 hover:text-indigo-900"
                  >
                    {ticket.jira_issue_key}
                  </a>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {ticket.jira_project_key || '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {ticket.status ? (
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(ticket.status)}`}>
                      {ticket.status}
                    </span>
                  ) : (
                    <span className="text-xs text-gray-400">-</span>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {ticket.priority ? (
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getPriorityColor(ticket.priority)}`}>
                      {ticket.priority}
                    </span>
                  ) : (
                    <span className="text-xs text-gray-400">-</span>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {ticket.assignee || '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {ticket.feedback_post_title ? (
                    <Link
                      href={`/feedback/${ticket.feedback_post_id}`}
                      className="text-indigo-600 hover:text-indigo-900 truncate max-w-xs block"
                      title={ticket.feedback_post_title}
                    >
                      {ticket.feedback_post_title}
                    </Link>
                  ) : (
                    <span className="text-xs text-gray-400">-</span>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {formatDistanceToNow(new Date(ticket.created_at), { addSuffix: true })}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {ticket.resolved_at ? (
                    <span className="text-green-600">
                      {formatDistanceToNow(new Date(ticket.resolved_at), { addSuffix: true })}
                    </span>
                  ) : (
                    <span className="text-gray-400">-</span>
                  )}
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

