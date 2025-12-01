/**
 * Metrics Page
 * 
 * Metrics and analytics page.
 * This will be implemented in task 10.4.
 */

import { DashboardLayout } from '../../components/layout/DashboardLayout';
import { ErrorBoundary } from '../../components/common/ErrorBoundary';

export default function MetricsPage() {
  return (
    <ErrorBoundary>
      <DashboardLayout>
        <div>
          <h1 className="text-3xl font-bold text-gray-900 mb-8">Metrics & Analytics</h1>
          <div className="bg-white rounded-lg shadow p-6">
            <p className="text-gray-600">
              Metrics dashboard will be implemented in task 10.4.
            </p>
          </div>
        </div>
      </DashboardLayout>
    </ErrorBoundary>
  );
}

