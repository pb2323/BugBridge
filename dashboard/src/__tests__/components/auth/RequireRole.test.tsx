/**
 * Unit Tests for RequireRole Component
 */

import { render, screen } from '@testing-library/react';
import { RequireRole } from '../../../components/auth/RequireRole';
import { useAuthStore } from '../../../store/auth-store';

// Mock the auth store
jest.mock('../../../store/auth-store');

describe('RequireRole', () => {
  const mockUseAuthStore = useAuthStore as jest.MockedFunction<typeof useAuthStore>;

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should render children when user has required role', () => {
    mockUseAuthStore.mockReturnValue({
      user: { id: '1', username: 'admin', role: 'admin', created_at: '2024-01-01' },
      token: 'token',
      isAuthenticated: true,
      login: jest.fn(),
      logout: jest.fn(),
      updateUser: jest.fn(),
    });

    render(
      <RequireRole allowedRoles={['admin']}>
        <div>Admin Content</div>
      </RequireRole>
    );

    expect(screen.getByText('Admin Content')).toBeInTheDocument();
  });

  it('should not render children when user does not have required role', () => {
    mockUseAuthStore.mockReturnValue({
      user: { id: '1', username: 'viewer', role: 'viewer', created_at: '2024-01-01' },
      token: 'token',
      isAuthenticated: true,
      login: jest.fn(),
      logout: jest.fn(),
      updateUser: jest.fn(),
    });

    render(
      <RequireRole allowedRoles={['admin']}>
        <div>Admin Content</div>
      </RequireRole>
    );

    expect(screen.queryByText('Admin Content')).not.toBeInTheDocument();
  });

  it('should render fallback when user does not have required role', () => {
    mockUseAuthStore.mockReturnValue({
      user: { id: '1', username: 'viewer', role: 'viewer', created_at: '2024-01-01' },
      token: 'token',
      isAuthenticated: true,
      login: jest.fn(),
      logout: jest.fn(),
      updateUser: jest.fn(),
    });

    render(
      <RequireRole allowedRoles={['admin']} fallback={<div>Access Denied</div>}>
        <div>Admin Content</div>
      </RequireRole>
    );

    expect(screen.queryByText('Admin Content')).not.toBeInTheDocument();
    expect(screen.getByText('Access Denied')).toBeInTheDocument();
  });

  it('should render children when user has one of multiple allowed roles', () => {
    mockUseAuthStore.mockReturnValue({
      user: { id: '1', username: 'viewer', role: 'viewer', created_at: '2024-01-01' },
      token: 'token',
      isAuthenticated: true,
      login: jest.fn(),
      logout: jest.fn(),
      updateUser: jest.fn(),
    });

    render(
      <RequireRole allowedRoles={['admin', 'viewer']}>
        <div>Content</div>
      </RequireRole>
    );

    expect(screen.getByText('Content')).toBeInTheDocument();
  });

  it('should not render children when user is null', () => {
    mockUseAuthStore.mockReturnValue({
      user: null,
      token: null,
      isAuthenticated: false,
      login: jest.fn(),
      logout: jest.fn(),
      updateUser: jest.fn(),
    });

    render(
      <RequireRole allowedRoles={['admin']}>
        <div>Content</div>
      </RequireRole>
    );

    expect(screen.queryByText('Content')).not.toBeInTheDocument();
  });
});

