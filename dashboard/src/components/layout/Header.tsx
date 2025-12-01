/**
 * Header Component
 * 
 * Top header with user information and logout button.
 */

'use client';

import { useAuthStore } from '../../store/auth-store';
import { useLogout } from '../../hooks/useAuth';
import { UserIcon } from '@heroicons/react/24/outline';

export function Header() {
  const { user } = useAuthStore();
  const logoutMutation = useLogout();

  const handleLogout = () => {
    logoutMutation.mutate();
  };

  return (
    <header className="sticky top-0 z-40 flex h-16 shrink-0 items-center gap-x-4 border-b border-gray-200 bg-white px-4 shadow-sm sm:gap-x-6 sm:px-6 lg:px-8">
      <div className="flex flex-1 gap-x-4 self-stretch lg:gap-x-6">
        <div className="flex items-center gap-x-4 lg:gap-x-6 ml-auto">
          <div className="hidden lg:block lg:h-6 lg:w-px lg:bg-gray-200" aria-hidden="true" />
          <div className="flex items-center gap-x-4 lg:gap-x-6">
            <div className="relative">
              <div className="flex items-center gap-x-3">
                <div className="flex items-center gap-2">
                  <UserIcon className="h-5 w-5 text-gray-400" />
                  <div className="text-sm">
                    <div className="font-semibold text-gray-900">{user?.username || 'User'}</div>
                    <div className="text-gray-500 capitalize">{user?.role || 'viewer'}</div>
                  </div>
                </div>
                <button
                  onClick={handleLogout}
                  disabled={logoutMutation.isPending}
                  className="ml-4 rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {logoutMutation.isPending ? 'Logging out...' : 'Logout'}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}

