/**
 * Sidebar Navigation Component
 * 
 * Navigation sidebar with menu items for dashboard sections.
 */

'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  HomeIcon,
  ChartBarIcon,
  DocumentTextIcon,
  Cog6ToothIcon,
  TicketIcon,
} from '@heroicons/react/24/outline';
import { RequireRole } from '../auth/RequireRole';

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: HomeIcon },
  { name: 'Feedback', href: '/feedback', icon: DocumentTextIcon },
  { name: 'Metrics', href: '/metrics', icon: ChartBarIcon },
  { name: 'Jira Tickets', href: '/jira-tickets', icon: TicketIcon },
  { name: 'Reports', href: '/reports', icon: DocumentTextIcon },
  { name: 'Settings', href: '/settings', icon: Cog6ToothIcon },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <div className="hidden lg:fixed lg:inset-y-0 lg:z-50 lg:flex lg:w-64 lg:flex-col">
      <div className="flex grow flex-col gap-y-5 overflow-y-auto bg-white border-r border-gray-200 px-6 pb-4">
        <div className="flex h-16 shrink-0 items-center">
          <h1 className="text-2xl font-bold text-gray-900">BugBridge</h1>
        </div>
        <nav className="flex flex-1 flex-col">
          <ul role="list" className="flex flex-1 flex-col gap-y-7">
            <li>
              <ul role="list" className="-mx-2 space-y-1">
                {navigation.map((item) => {
                  const isActive = pathname === item.href || pathname?.startsWith(`${item.href}/`);
                  const requiresAdmin = item.name === 'Settings';
                  
                  const linkContent = (
                    <Link
                      href={item.href}
                      className={`
                        group flex gap-x-3 rounded-md p-2 text-sm leading-6 font-semibold
                        ${
                          isActive
                            ? 'bg-gray-50 text-indigo-600'
                            : 'text-gray-700 hover:text-indigo-600 hover:bg-gray-50'
                        }
                      `}
                    >
                      <item.icon
                        className={`h-6 w-6 shrink-0 ${
                          isActive ? 'text-indigo-600' : 'text-gray-400 group-hover:text-indigo-600'
                        }`}
                        aria-hidden="true"
                      />
                      {item.name}
                    </Link>
                  );

                  return (
                    <li key={item.name}>
                      {requiresAdmin ? (
                        <RequireRole allowedRoles={['admin']}>
                          {linkContent}
                        </RequireRole>
                      ) : (
                        linkContent
                      )}
                    </li>
                  );
                })}
              </ul>
            </li>
          </ul>
        </nav>
      </div>
    </div>
  );
}

