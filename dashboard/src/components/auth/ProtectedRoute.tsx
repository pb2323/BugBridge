/**
 * Protected Route Component
 * 
 * Higher-order component to protect routes that require authentication.
 */

'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '../../store/auth-store';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { useSessionRestore } from '../../hooks/useSessionRestore';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requireAdmin?: boolean;
}

export function ProtectedRoute({ children, requireAdmin = false }: ProtectedRouteProps) {
  const router = useRouter();
  const { isAuthenticated, user } = useAuthStore();
  const { isRestoring } = useSessionRestore();

  useEffect(() => {
    // Wait for session restoration to complete before checking auth
    if (isRestoring) {
      return;
    }

    if (!isAuthenticated) {
      router.push('/login');
    } else if (requireAdmin && user?.role !== 'admin') {
      // Redirect to dashboard if not admin
      router.push('/dashboard');
    }
  }, [isAuthenticated, isRestoring, user, requireAdmin, router]);

  // Show loading while restoring session or checking authentication
  if (isRestoring || !isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner />
      </div>
    );
  }

  if (requireAdmin && user?.role !== 'admin') {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Access Denied</h2>
          <p className="text-gray-600">You don't have permission to access this page.</p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}

