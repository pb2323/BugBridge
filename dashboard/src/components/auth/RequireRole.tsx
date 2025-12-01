/**
 * Require Role Component
 * 
 * Component to conditionally render content based on user role.
 */

'use client';

import { useAuthStore } from '../../store/auth-store';

interface RequireRoleProps {
  children: React.ReactNode;
  allowedRoles: ('admin' | 'viewer')[];
  fallback?: React.ReactNode;
}

export function RequireRole({ children, allowedRoles, fallback = null }: RequireRoleProps) {
  const { user } = useAuthStore();

  if (!user || !allowedRoles.includes(user.role)) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}

