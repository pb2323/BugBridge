/**
 * Jira Tickets API Service
 * 
 * API service functions for Jira tickets endpoints.
 */

import apiClient from '../../lib/api-client';

export interface JiraTicket {
  id: string;
  jira_issue_key: string;
  jira_issue_id?: string;
  jira_project_key?: string;
  status?: string;
  priority?: string;
  assignee?: string;
  created_at: string;
  resolved_at?: string;
  updated_at: string;
  feedback_post_id?: string;
  feedback_post_title?: string;
  feedback_post_canny_id?: string;
}

export interface JiraTicketListResponse {
  items: JiraTicket[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface JiraTicketListParams {
  page?: number;
  page_size?: number;
  project_keys?: string;
  statuses?: string;
  priorities?: string;
  assignee?: string;
  resolved_only?: boolean;
  unresolved_only?: boolean;
  has_feedback?: boolean;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface JiraTicketRefreshResponse {
  success: boolean;
  tickets_updated: number;
  tickets_failed: number;
  total_tickets: number;
  errors: string[];
  timestamp: string;
}

export const jiraApi = {
  /**
   * List Jira tickets with filtering and pagination
   */
  list: async (params?: JiraTicketListParams): Promise<JiraTicketListResponse> => {
    const response = await apiClient.get<JiraTicketListResponse>('/jira-tickets', { params });
    return response.data;
  },

  /**
   * Get detailed Jira ticket information
   */
  get: async (ticketId: string): Promise<JiraTicket> => {
    const response = await apiClient.get<JiraTicket>(`/jira-tickets/${ticketId}`);
    return response.data;
  },

  /**
   * Refresh all Jira tickets from the Jira instance via MCP server.
   * Fetches latest status, priority, assignee, and other fields from Jira.
   */
  refresh: async (limit?: number): Promise<JiraTicketRefreshResponse> => {
    const params = limit ? { limit } : {};
    const response = await apiClient.post<JiraTicketRefreshResponse>('/jira-tickets/refresh', null, { params });
    return response.data;
  },
};

