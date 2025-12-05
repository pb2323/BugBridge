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
    // Handle 401 Unauthorized
    if (error.response?.status === 401) {
      const url = error.config?.url || '';
      
      // Don't auto-logout for auth endpoints (let them handle it)
      if (!url.includes('/auth/')) {
        if (typeof window !== 'undefined') {
          // Check if we're on the login page already
          const isOnLoginPage = window.location.pathname.includes('/login');
          
          // Only logout and redirect if not already on login page
          // This prevents logout loops during session restore
          if (!isOnLoginPage) {
            localStorage.removeItem('auth_token');
            const { useAuthStore } = require('../store/auth-store');
            useAuthStore.getState().logout();
          }
        }
      }
    }
    return Promise.reject(error);
  }
);

export default apiClient;
