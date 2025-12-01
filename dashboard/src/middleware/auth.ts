/**
 * Authentication Middleware
 * 
 * Middleware for handling token refresh and session management.
 */

import { authApi } from '../services/api/auth';

let refreshTimer: NodeJS.Timeout | null = null;

/**
 * Initialize session management
 * Sets up token refresh and expiration handling
 */
export function initializeSessionManagement() {
  // Import useAuthStore dynamically to avoid circular dependencies
  const { useAuthStore } = require('../store/auth-store');
  const { token, isAuthenticated } = useAuthStore.getState();

  if (!isAuthenticated || !token) {
    return;
  }

  // Clear existing timer
  if (refreshTimer) {
    clearTimeout(refreshTimer);
  }

  // Decode JWT to get expiration (simplified - in production use a JWT library)
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    const expirationTime = payload.exp * 1000; // Convert to milliseconds
    const currentTime = Date.now();
    const timeUntilExpiration = expirationTime - currentTime;
    
    // Refresh token 5 minutes before expiration
    const refreshTime = Math.max(0, timeUntilExpiration - 5 * 60 * 1000);

    refreshTimer = setTimeout(() => {
      refreshToken();
    }, refreshTime);
  } catch (error) {
    console.error('Failed to parse token expiration:', error);
  }
}

/**
 * Refresh the authentication token
 */
async function refreshToken() {
  try {
    // Import useAuthStore dynamically to avoid circular dependencies
    const { useAuthStore } = require('../store/auth-store');
    
    // In a real implementation, you would call a refresh endpoint
    // For now, we'll just refresh the user info to validate the token
    const user = await authApi.getCurrentUser();
    useAuthStore.getState().updateUser(user);
    
    // Re-initialize session management
    initializeSessionManagement();
  } catch (error) {
    // Import useAuthStore dynamically to avoid circular dependencies
    const { useAuthStore } = require('../store/auth-store');
    
    // Token is invalid or expired, logout user
    useAuthStore.getState().logout();
    if (typeof window !== 'undefined') {
      window.location.href = '/login';
    }
  }
}

/**
 * Clear session management
 */
export function clearSessionManagement() {
  if (refreshTimer) {
    clearTimeout(refreshTimer);
    refreshTimer = null;
  }
}
