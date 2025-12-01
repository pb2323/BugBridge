/**
 * Mobile Sidebar Component
 * 
 * Mobile-responsive sidebar navigation for smaller screens.
 */

'use client';

import { Fragment } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Dialog, Transition } from '@headlessui/react';
import {
  HomeIcon,
  ChartBarIcon,
  DocumentTextIcon,
  Cog6ToothIcon,
  TicketIcon,
  XMarkIcon,
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

interface MobileSidebarProps {
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
}

export function MobileSidebar({ sidebarOpen, setSidebarOpen }: MobileSidebarProps) {
  const pathname = usePathname();

  return (
    <Transition.Root show={sidebarOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50 lg:hidden" onClose={setSidebarOpen}>
        <Transition.Child
          as={Fragment}
          enter="transition-opacity ease-linear duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="transition-opacity ease-linear duration-300"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-gray-900/80" />
        </Transition.Child>

        <div className="fixed inset-0 flex">
          <Transition.Child
            as={Fragment}
            enter="transition ease-in-out duration-300 transform"
            enterFrom="-translate-x-full"
            enterTo="translate-x-0"
            leave="transition ease-in-out duration-300 transform"
            leaveFrom="translate-x-0"
            leaveTo="-translate-x-full"
          >
            <Dialog.Panel className="relative mr-16 flex w-full max-w-xs flex-1">
              <Transition.Child
                as={Fragment}
                enter="ease-in-out duration-300"
                enterFrom="opacity-0"
                enterTo="opacity-100"
                leave="ease-in-out duration-300"
                leaveFrom="opacity-100"
                leaveTo="opacity-0"
              >
                <div className="absolute left-full top-0 flex w-16 justify-center pt-5">
                  <button
                    type="button"
                    className="-m-2.5 p-2.5"
                    onClick={() => setSidebarOpen(false)}
                  >
                    <span className="sr-only">Close sidebar</span>
                    <XMarkIcon className="h-6 w-6 text-white" aria-hidden="true" />
                  </button>
                </div>
              </Transition.Child>
              <div className="flex grow flex-col gap-y-5 overflow-y-auto bg-white px-6 pb-4">
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
                              onClick={() => setSidebarOpen(false)}
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
            </Dialog.Panel>
          </Transition.Child>
        </div>
      </Dialog>
    </Transition.Root>
  );
}

