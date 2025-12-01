/**
 * Reports API Service
 * 
 * API service functions for reports endpoints.
 */

import apiClient from '@/lib/api-client';

export interface Report {
  id: string;
  report_type: string;
  report_date: string;
  generated_at: string;
  has_content: boolean;
  has_metrics: boolean;
}

export interface ReportListResponse {
  items: Report[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ReportDetail {
  id: string;
  report_type: string;
  report_date: string;
  generated_at: string;
  content?: string;
  metrics?: Record<string, any>;
}

export interface ReportListParams {
  page?: number;
  page_size?: number;
  report_type?: string;
  start_date?: string;
  end_date?: string;
}

export interface ReportGenerateRequest {
  report_date?: string;
  filters?: {
    start_date?: string;
    end_date?: string;
    board_ids?: string[];
    tags?: string[];
    statuses?: string[];
    sentiment_filter?: string[];
    bug_only?: boolean;
    feature_only?: boolean;
    min_priority_score?: number;
    min_votes?: number;
    jira_project_keys?: string[];
    jira_statuses?: string[];
  };
}

export interface ReportGenerateResponse {
  success: boolean;
  report_id?: string;
  report_date?: string;
  metrics?: Record<string, any>;
  summary?: Record<string, any>;
  content?: string;
  delivery?: Record<string, any>;
  errors: string[];
}

export const reportsApi = {
  /**
   * List historical reports
   */
  list: async (params?: ReportListParams): Promise<ReportListResponse> => {
    const response = await apiClient.get<ReportListResponse>('/reports', { params });
    return response.data;
  },

  /**
   * Get specific report details
   */
  get: async (reportId: string): Promise<ReportDetail> => {
    const response = await apiClient.get<ReportDetail>(`/reports/${reportId}`);
    return response.data;
  },

  /**
   * Generate a new report
   */
  generate: async (request: ReportGenerateRequest): Promise<ReportGenerateResponse> => {
    const response = await apiClient.post<ReportGenerateResponse>('/reports/generate', request);
    return response.data;
  },

  /**
   * Generate a report using workflow
   */
  generateWorkflow: async (request: ReportGenerateRequest): Promise<ReportGenerateResponse> => {
    const response = await apiClient.post<ReportGenerateResponse>('/reports/generate/workflow', request);
    return response.data;
  },
};

