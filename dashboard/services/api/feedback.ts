/**
 * Feedback API Service
 * 
 * API service functions for feedback endpoints.
 */

import apiClient from '@/lib/api-client';

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
};

