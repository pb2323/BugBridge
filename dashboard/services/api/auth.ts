/**
 * Authentication API Service
 * 
 * API service functions for authentication endpoints.
 */

import apiClient from '@/lib/api-client';

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: {
    id: string;
    username: string;
    email?: string;
    role: 'admin' | 'viewer';
    created_at: string;
  };
}

export interface UserResponse {
  id: string;
  username: string;
  email?: string;
  role: 'admin' | 'viewer';
  created_at: string;
}

export const authApi = {
  /**
   * Login user and get JWT token
   */
  login: async (credentials: LoginRequest): Promise<LoginResponse> => {
    const response = await apiClient.post<LoginResponse>('/auth/login', credentials);
    return response.data;
  },

  /**
   * Logout user
   */
  logout: async (): Promise<void> => {
    await apiClient.post('/auth/logout');
  },

  /**
   * Get current user information
   */
  getCurrentUser: async (): Promise<UserResponse> => {
    const response = await apiClient.get<UserResponse>('/auth/me');
    return response.data;
  },
};

