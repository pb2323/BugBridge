'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '../store/auth-store';
import { useSessionRestore } from '../hooks/useSessionRestore';
import { LoadingSpinner } from '../components/common/LoadingSpinner';

export default function Home() {
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();
  const { isRestoring } = useSessionRestore();

  useEffect(() => {
    // Wait for session restoration to complete before redirecting
    if (isRestoring) {
      return;
    }

    if (isAuthenticated) {
      router.push('/dashboard');
    } else {
      router.push('/login');
    }
  }, [isAuthenticated, isRestoring, router]);

  // Show loading while restoring session
  if (isRestoring) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner />
      </div>
    );
  }

  return null;
}

