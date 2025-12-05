/**
 * App Providers
 * 
 * Wraps the application with necessary providers (React Query, etc.)
 */

'use client';

import { useEffect } from 'react';
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from '../lib/query-client';
import { initializeSessionManagement, clearSessionManagement } from '../middleware/auth';
import { useAuthStore } from '../store/auth-store';
import { useSessionRestore } from '../hooks/useSessionRestore';

function SessionManager() {
  const { isAuthenticated } = useAuthStore();
  const { isRestoring } = useSessionRestore();

  useEffect(() => {
    // Wait for session restoration before initializing session management
    if (isRestoring) {
      return;
    }

    if (isAuthenticated) {
      initializeSessionManagement();
    } else {
      clearSessionManagement();
    }

    return () => {
      clearSessionManagement();
    };
  }, [isAuthenticated, isRestoring]);

  return null;
}

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <SessionManager />
      {children}
    </QueryClientProvider>
  );
}
