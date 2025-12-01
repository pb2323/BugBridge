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

function SessionManager() {
  const { isAuthenticated } = useAuthStore();

  useEffect(() => {
    if (isAuthenticated) {
      initializeSessionManagement();
    } else {
      clearSessionManagement();
    }

    return () => {
      clearSessionManagement();
    };
  }, [isAuthenticated]);

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
