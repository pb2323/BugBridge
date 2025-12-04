/**
 * API Client Configuration
 * 
 * Centralized HTTP client for API requests with authentication and error handling.
 */

import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios';

// Get API base URL from environment variables
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_BASE_PATH = process.env.NEXT_PUBLIC_API_BASE_PATH || '/api';

// Create axios instance
const apiClient: AxiosInstance = axios.create({
  baseURL: `${API_BASE_URL}${API_BASE_PATH}`,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 seconds
});

// Request interceptor to add authentication token
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Get token from localStorage (or secure storage)
    if (typeof window !== 'undefined') {
      // Try localStorage first (set by auth store)
      let token = localStorage.getItem('auth_token');
      
      // Fallback: try to get from Zustand store if localStorage is empty
      if (!token) {
        try {
          const authStorage = localStorage.getItem('auth-storage');
          if (authStorage) {
            const parsed = JSON.parse(authStorage);
            if (parsed?.state?.token) {
              token = parsed.state.token;
              // Sync it to auth_token for future requests
              localStorage.setItem('auth_token', token);
            }
          }
        } catch (e) {
          // Ignore parsing errors
        }
      }
      
      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    // Handle 401 Unauthorized - redirect to login
    if (error.response?.status === 401) {
      if (typeof window !== 'undefined') {
        localStorage.removeItem('auth_token');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default apiClient;
