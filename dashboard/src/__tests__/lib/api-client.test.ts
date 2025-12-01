/**
 * Unit Tests for API Client
 * 
 * Note: These tests verify the API client configuration and interceptors.
 */

describe('API Client', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    jest.resetModules();
  });

  it('should be configured with correct base URL', async () => {
    const apiClient = (await import('../../lib/api-client')).default;
    expect(apiClient.defaults.baseURL).toContain('/api');
  });

  it('should have request interceptor configured', async () => {
    const apiClient = (await import('../../lib/api-client')).default;
    expect(apiClient.interceptors.request.handlers.length).toBeGreaterThan(0);
  });

  it('should have response interceptor configured', async () => {
    const apiClient = (await import('../../lib/api-client')).default;
    expect(apiClient.interceptors.response.handlers.length).toBeGreaterThan(0);
  });
});

