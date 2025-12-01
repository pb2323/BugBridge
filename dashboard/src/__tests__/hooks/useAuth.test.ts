/**
 * Unit Tests for useAuth Hook
 */

import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useLogout } from '../../hooks/useAuth';
import { authApi } from '../../services/api/auth';
import { useAuthStore } from '../../store/auth-store';

// Mock dependencies
jest.mock('../../services/api/auth');
jest.mock('../../store/auth-store');
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
  }),
}));

const mockAuthApi = authApi as jest.Mocked<typeof authApi>;
const mockUseAuthStore = useAuthStore as jest.MockedFunction<typeof useAuthStore>;

describe('useAuth', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    jest.clearAllMocks();
  });

  describe('useLogout', () => {
    it('should logout successfully', async () => {
      const mockLogout = jest.fn();
      mockUseAuthStore.mockReturnValue({
        user: { id: '1', username: 'user', role: 'viewer', created_at: '2024-01-01' },
        token: 'token',
        isAuthenticated: true,
        login: jest.fn(),
        logout: mockLogout,
        updateUser: jest.fn(),
      });

      mockAuthApi.logout.mockResolvedValue(undefined);

      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      );

      const { result } = renderHook(() => useLogout(), { wrapper });

      result.current.mutate();

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(mockAuthApi.logout).toHaveBeenCalledTimes(1);
      expect(mockLogout).toHaveBeenCalledTimes(1);
    });

    it('should logout even if API call fails', async () => {
      const mockLogout = jest.fn();
      mockUseAuthStore.mockReturnValue({
        user: { id: '1', username: 'user', role: 'viewer', created_at: '2024-01-01' },
        token: 'token',
        isAuthenticated: true,
        login: jest.fn(),
        logout: mockLogout,
        updateUser: jest.fn(),
      });

      mockAuthApi.logout.mockRejectedValue(new Error('API Error'));

      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      );

      const { result } = renderHook(() => useLogout(), { wrapper });

      result.current.mutate();

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      // Should still logout locally even if API fails
      expect(mockLogout).toHaveBeenCalledTimes(1);
    });
  });
});

