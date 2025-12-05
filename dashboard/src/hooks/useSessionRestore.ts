/**
 * Session Restoration Hook
 * 
 * Restores user session from localStorage on page load/refresh.
 */

import { useEffect, useState } from 'react';
import { useAuthStore } from '../store/auth-store';
import { authApi } from '../services/api/auth';

/**
 * Hook to restore and validate session on page load.
 * 
 * Returns:
 * - isRestoring: true while checking/restoring session
 * - isAuthenticated: true if user is authenticated after restoration
 */
export function useSessionRestore() {
  const [isRestoring, setIsRestoring] = useState(true);
  const { token, isAuthenticated, login, logout } = useAuthStore();

  useEffect(() => {
    async function restoreSession() {
      // Wait a bit for Zustand persist to rehydrate
      await new Promise(resolve => setTimeout(resolve, 100));

      const currentToken = useAuthStore.getState().token;
      
      // If no token in store, check localStorage directly
      if (!currentToken && typeof window !== 'undefined') {
        const storedToken = localStorage.getItem('auth_token') || 
          (() => {
            try {
              const authStorage = localStorage.getItem('auth-storage');
              if (authStorage) {
                const parsed = JSON.parse(authStorage);
                return parsed?.state?.token || null;
              }
            } catch {
              return null;
            }
          })();

        if (storedToken) {
          // Validate token with backend
          try {
            const user = await authApi.getCurrentUser();
            // Token is valid, restore session
            login(storedToken, user);
            setIsRestoring(false);
            return;
          } catch (error) {
            // Token is invalid, clear it
            localStorage.removeItem('auth_token');
            localStorage.removeItem('auth-storage');
            logout();
          }
        } else {
          // No token found
          logout();
        }
      } else if (currentToken) {
        // Token exists in store, validate it
        try {
          await authApi.getCurrentUser();
          // Token is valid, session is restored
          setIsRestoring(false);
          return;
        } catch (error) {
          // Token is invalid, clear session
          localStorage.removeItem('auth_token');
          logout();
        }
      } else {
        // No token, user is not authenticated
        setIsRestoring(false);
      }
      
      setIsRestoring(false);
    }

    restoreSession();
  }, []); // Only run once on mount

  return { isRestoring, isAuthenticated: useAuthStore.getState().isAuthenticated };
}

