/**
 * Feedback API Service
 * 
 * API service functions for feedback endpoints.
 */

import apiClient from '../../lib/api-client';

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

export interface FeedbackListResponse {
  items: FeedbackPost[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface FeedbackRefreshResponse {
  success: boolean;
  collected_count: number;
  processed_count: number;
  successful_processing: number;
  jira_tickets_created: number;
  timestamp: string;
  error?: string | null;
}

export interface FeedbackProcessResponse {
  success: boolean;
  total_unprocessed: number;
  processed_count: number;
  successful_processing: number;
  jira_tickets_created: number;
  timestamp: string;
  error?: string | null;
}

export interface FeedbackListParams {
  page?: number;
  page_size?: number;
  board_ids?: string;
  tags?: string;
  status?: string;
  search?: string;
  is_bug?: boolean;
  sentiment?: string;
  min_priority?: number;
  min_votes?: number;
  has_jira_ticket?: boolean;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export const feedbackApi = {
  /**
   * List feedback posts with filtering and pagination
   */
  list: async (params?: FeedbackListParams): Promise<FeedbackListResponse> => {
    const response = await apiClient.get<FeedbackListResponse>('/feedback', { params });
    return response.data;
  },

  /**
   * Get detailed feedback post information
   */
  get: async (postId: string): Promise<FeedbackPost> => {
    const response = await apiClient.get<FeedbackPost>(`/feedback/${postId}`);
    return response.data;
  },

  /**
   * Refresh feedback posts from Canny.io
   *
   * Triggers backend collection that fetches new posts and skips existing ones.
   */
  refresh: async (): Promise<FeedbackRefreshResponse> => {
    const response = await apiClient.post<FeedbackRefreshResponse>('/feedback/refresh');
    return response.data;
  },

  /**
   * Process existing unprocessed feedback posts through the workflow
   *
   * Triggers analysis for posts that were collected but not yet processed.
   * This includes bug detection, sentiment analysis, priority scoring, and Jira ticket creation.
   */
  processExisting: async (limit?: number): Promise<FeedbackProcessResponse> => {
    const params = limit ? { limit } : {};
    const response = await apiClient.post<FeedbackProcessResponse>('/feedback/process-existing', null, { params });
    return response.data;
  },

  /**
   * Process a single feedback post through the workflow
   *
   * Triggers analysis for a specific post, including bug detection, sentiment analysis,
   * priority scoring, and Jira ticket creation. Can be used to reprocess posts.
   */
  processSingle: async (postId: string): Promise<FeedbackProcessResponse> => {
    const response = await apiClient.post<FeedbackProcessResponse>(`/feedback/${postId}/process`);
    return response.data;
  },
};

