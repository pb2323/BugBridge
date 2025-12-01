/**
 * Metrics API Service
 * 
 * API service functions for metrics endpoints.
 */

import apiClient from '../../lib/api-client';

export interface MetricsResponse {
  total_feedback_posts: number;
  total_bugs: number;
  total_feature_requests: number;
  bugs_percentage: number;
  sentiment_distribution: Record<string, number>;
  priority_distribution: Record<string, number>;
  total_jira_tickets: number;
  resolved_tickets: number;
  resolution_rate: number;
  average_response_time_hours?: number;
  average_resolution_time_hours?: number;
  recent_posts: number;
  recent_tickets: number;
  recent_resolutions: number;
  top_priority_items: Array<{
    title: string;
    priority_score: number;
    priority: string;
    post_id: string;
  }>;
}

export interface MetricsParams {
  start_date?: string;
  end_date?: string;
}

export const metricsApi = {
  /**
   * Get aggregated metrics and statistics
   */
  get: async (params?: MetricsParams): Promise<MetricsResponse> => {
    const response = await apiClient.get<MetricsResponse>('/metrics', { params });
    return response.data;
  },
};

