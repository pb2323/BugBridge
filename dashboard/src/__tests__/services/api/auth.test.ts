/**
 * Integration Tests for Auth API Service
 */

import { authApi } from '../../../services/api/auth';
import apiClient from '../../../lib/api-client';

// Mock the API client
jest.mock('../../../lib/api-client');

const mockApiClient = apiClient as jest.Mocked<typeof apiClient>;

describe('authApi', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('login', () => {
    it('should login successfully', async () => {
      const mockResponse = {
        data: {
          access_token: 'token123',
          token_type: 'Bearer',
          expires_in: 3600,
          user: {
            id: '1',
            username: 'testuser',
            email: 'test@example.com',
            role: 'admin' as const,
            created_at: '2024-01-01',
          },
        },
      };

      mockApiClient.post.mockResolvedValue(mockResponse);

      const result = await authApi.login({
        username: 'testuser',
        password: 'password123',
      });

      expect(mockApiClient.post).toHaveBeenCalledWith('/auth/login', {
        username: 'testuser',
        password: 'password123',
      });
      expect(result).toEqual(mockResponse.data);
    });

    it('should handle login errors', async () => {
      const mockError = new Error('Invalid credentials');
      mockApiClient.post.mockRejectedValue(mockError);

      await expect(
        authApi.login({
          username: 'testuser',
          password: 'wrongpassword',
        })
      ).rejects.toThrow('Invalid credentials');
    });
  });

  describe('logout', () => {
    it('should logout successfully', async () => {
      mockApiClient.post.mockResolvedValue({ data: undefined });

      await authApi.logout();

      expect(mockApiClient.post).toHaveBeenCalledWith('/auth/logout');
    });
  });

  describe('getCurrentUser', () => {
    it('should get current user successfully', async () => {
      const mockResponse = {
        data: {
          id: '1',
          username: 'testuser',
          email: 'test@example.com',
          role: 'admin' as const,
          created_at: '2024-01-01',
        },
      };

      mockApiClient.get.mockResolvedValue(mockResponse);

      const result = await authApi.getCurrentUser();

      expect(mockApiClient.get).toHaveBeenCalledWith('/auth/me');
      expect(result).toEqual(mockResponse.data);
    });
  });
});

