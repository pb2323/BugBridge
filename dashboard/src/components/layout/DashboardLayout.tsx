/**
 * Dashboard Layout Component
 * 
 * Main layout component for the dashboard with sidebar navigation and header.
 */

'use client';

import { ReactNode, useState } from 'react';
import { Sidebar } from './Sidebar';
import { MobileSidebar } from './MobileSidebar';
import { Header } from './Header';
import { Bars3Icon } from '@heroicons/react/24/outline';
import { ProtectedRoute } from '../auth/ProtectedRoute';

interface DashboardLayoutProps {
  children: ReactNode;
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <ProtectedRoute>
    <div className="min-h-screen bg-gray-50">
      <MobileSidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <Sidebar />
      <div className="lg:pl-64">
        <div className="sticky top-0 z-40 flex h-16 shrink-0 items-center gap-x-4 border-b border-gray-200 bg-white px-4 shadow-sm sm:gap-x-6 sm:px-6 lg:px-8 lg:hidden">
          <button
            type="button"
            className="-m-2.5 p-2.5 text-gray-700 lg:hidden"
            onClick={() => setSidebarOpen(true)}
          >
            <span className="sr-only">Open sidebar</span>
            <Bars3Icon className="h-6 w-6" aria-hidden="true" />
          </button>
        </div>
        <Header />
        <main className="py-8">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            {children}
          </div>
        </main>
      </div>
    </div>
    </ProtectedRoute>
  );
}

