/**
 * Canny.io Settings Form Component
 * 
 * Form for configuring Canny.io integration settings.
 */

'use client';

import { useState } from 'react';
import { EyeIcon, EyeSlashIcon } from '@heroicons/react/24/outline';

interface CannySettings {
  api_key?: string;
  subdomain?: string;
  board_id?: string;
  admin_user_id?: string;
  sync_interval_minutes?: number;
}

interface CannySettingsFormProps {
  settings: CannySettings;
  onChange: (settings: CannySettings) => void;
  errors?: Record<string, string>;
}

export function CannySettingsForm({ settings, onChange, errors = {} }: CannySettingsFormProps) {
  const [showApiKey, setShowApiKey] = useState(false);

  const updateField = <K extends keyof CannySettings>(field: K, value: CannySettings[K]) => {
    onChange({ ...settings, [field]: value });
  };

  return (
    <div className="space-y-4">
      <div>
        <label htmlFor="canny_api_key" className="block text-sm font-medium text-gray-700">
          API Key
        </label>
        <div className="mt-1 relative">
          <input
            type={showApiKey ? 'text' : 'password'}
            id="canny_api_key"
            value={settings.api_key || ''}
            onChange={(e) => updateField('api_key', e.target.value || undefined)}
            placeholder="Enter Canny.io API key"
            className={`block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 ${
              errors.api_key ? 'border-red-300' : ''
            }`}
          />
          <button
            type="button"
            onClick={() => setShowApiKey(!showApiKey)}
            className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600"
          >
            {showApiKey ? (
              <EyeSlashIcon className="h-5 w-5" />
            ) : (
              <EyeIcon className="h-5 w-5" />
            )}
          </button>
        </div>
        {errors.api_key && <p className="mt-1 text-sm text-red-600">{errors.api_key}</p>}
        <p className="mt-1 text-sm text-gray-500">Your Canny.io API token</p>
      </div>

      <div>
        <label htmlFor="canny_subdomain" className="block text-sm font-medium text-gray-700">
          Subdomain
        </label>
        <div className="mt-1">
          <input
            type="text"
            id="canny_subdomain"
            value={settings.subdomain || ''}
            onChange={(e) => updateField('subdomain', e.target.value || undefined)}
            placeholder="your-company"
            className={`block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 ${
              errors.subdomain ? 'border-red-300' : ''
            }`}
          />
        </div>
        {errors.subdomain && <p className="mt-1 text-sm text-red-600">{errors.subdomain}</p>}
        <p className="mt-1 text-sm text-gray-500">Your Canny.io company subdomain (e.g., your-company.canny.io)</p>
      </div>

      <div>
        <label htmlFor="canny_board_id" className="block text-sm font-medium text-gray-700">
          Board ID
        </label>
        <div className="mt-1">
          <input
            type="text"
            id="canny_board_id"
            value={settings.board_id || ''}
            onChange={(e) => updateField('board_id', e.target.value || undefined)}
            placeholder="Enter board ID"
            className={`block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 ${
              errors.board_id ? 'border-red-300' : ''
            }`}
          />
        </div>
        {errors.board_id && <p className="mt-1 text-sm text-red-600">{errors.board_id}</p>}
        <p className="mt-1 text-sm text-gray-500">Default board ID to sync feedback from</p>
      </div>

      <div>
        <label htmlFor="canny_admin_user_id" className="block text-sm font-medium text-gray-700">
          Admin User ID (Optional)
        </label>
        <div className="mt-1">
          <input
            type="text"
            id="canny_admin_user_id"
            value={settings.admin_user_id || ''}
            onChange={(e) => updateField('admin_user_id', e.target.value || undefined)}
            placeholder="Enter admin user ID"
            className="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
          />
        </div>
        <p className="mt-1 text-sm text-gray-500">Canny.io admin user ID for posting comments and notifications</p>
      </div>

      <div>
        <label htmlFor="canny_sync_interval" className="block text-sm font-medium text-gray-700">
          Sync Interval (minutes)
        </label>
        <div className="mt-1">
          <input
            type="number"
            id="canny_sync_interval"
            min="1"
            max="1440"
            value={settings.sync_interval_minutes || 5}
            onChange={(e) => updateField('sync_interval_minutes', parseInt(e.target.value) || undefined)}
            className={`block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 ${
              errors.sync_interval_minutes ? 'border-red-300' : ''
            }`}
          />
        </div>
        {errors.sync_interval_minutes && (
          <p className="mt-1 text-sm text-red-600">{errors.sync_interval_minutes}</p>
        )}
        <p className="mt-1 text-sm text-gray-500">Polling interval for syncing feedback posts (1-1440 minutes)</p>
      </div>
    </div>
  );
}

