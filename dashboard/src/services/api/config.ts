/**
 * Configuration API Service
 * 
 * API service functions for configuration endpoints.
 */

import apiClient from '../../lib/api-client';

export interface ConfigResponse {
  canny: Record<string, any>;
  jira: Record<string, any>;
  xai: Record<string, any>;
  database: Record<string, any>;
  reporting: Record<string, any>;
  agent: Record<string, any>;
}

export interface ConfigUpdateRequest {
  canny?: Record<string, any>;
  jira?: Record<string, any>;
  reporting?: Record<string, any>;
  agent?: Record<string, any>;
}

export const configApi = {
  /**
   * Get current configuration settings
   */
  get: async (): Promise<ConfigResponse> => {
    const response = await apiClient.get<ConfigResponse>('/config');
    return response.data;
  },

  /**
   * Update configuration settings
   */
  update: async (request: ConfigUpdateRequest): Promise<ConfigResponse> => {
    const response = await apiClient.put<ConfigResponse>('/config', request);
    return response.data;
  },
};

