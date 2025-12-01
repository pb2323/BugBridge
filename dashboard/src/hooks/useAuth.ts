/**
 * useAuth Hook
 * 
 * React Query hook for authentication operations.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { authApi, UserResponse } from '../services/api/auth';
import { useAuthStore } from '../store/auth-store';
import { useRouter } from 'next/navigation';

export function useCurrentUser() {
  const { token, isAuthenticated } = useAuthStore();

  return useQuery<UserResponse>({
    queryKey: ['auth', 'me'],
    queryFn: () => authApi.getCurrentUser(),
    enabled: isAuthenticated && !!token,
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: false,
  });
}

export function useLogout() {
  const router = useRouter();
  const { logout } = useAuthStore();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => authApi.logout(),
    onSuccess: () => {
      logout();
      queryClient.clear();
      router.push('/login');
    },
    onError: () => {
      // Even if logout API call fails, clear local state
      logout();
      queryClient.clear();
      router.push('/login');
    },
  });
}

