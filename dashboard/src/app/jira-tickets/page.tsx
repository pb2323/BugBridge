/**
 * Jira Tickets Page
 * 
 * Jira tickets listing and management page.
 * This will be implemented in task 10.5.
 */

import { DashboardLayout } from '../../components/layout/DashboardLayout';
import { ErrorBoundary } from '../../components/common/ErrorBoundary';

export default function JiraTicketsPage() {
  return (
    <ErrorBoundary>
      <DashboardLayout>
        <div>
          <h1 className="text-3xl font-bold text-gray-900 mb-8">Jira Tickets</h1>
          <div className="bg-white rounded-lg shadow p-6">
            <p className="text-gray-600">
              Jira tickets listing will be implemented in task 10.5.
            </p>
          </div>
        </div>
      </DashboardLayout>
    </ErrorBoundary>
  );
}

