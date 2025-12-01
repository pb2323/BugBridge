/**
 * Reporting Settings Form Component
 * 
 * Form for configuring report schedule and recipients.
 */

'use client';

import { useState } from 'react';

interface ReportingSettings {
  schedule_cron?: string;
  email_enabled?: boolean;
  file_storage_enabled?: boolean;
  recipients?: string[];
}

interface ReportingSettingsFormProps {
  settings: ReportingSettings;
  onChange: (settings: ReportingSettings) => void;
  errors?: Record<string, string>;
}

export function ReportingSettingsForm({ settings, onChange, errors = {} }: ReportingSettingsFormProps) {
  const [newRecipient, setNewRecipient] = useState('');

  const updateField = <K extends keyof ReportingSettings>(field: K, value: ReportingSettings[K]) => {
    onChange({ ...settings, [field]: value });
  };

  const addRecipient = () => {
    if (newRecipient.trim() && newRecipient.includes('@')) {
      const recipients = settings.recipients || [];
      if (!recipients.includes(newRecipient.trim())) {
        updateField('recipients', [...recipients, newRecipient.trim()]);
        setNewRecipient('');
      }
    }
  };

  const removeRecipient = (email: string) => {
    const recipients = settings.recipients || [];
    updateField('recipients', recipients.filter((r) => r !== email));
  };

  return (
    <div className="space-y-4">
      <div>
        <label htmlFor="report_schedule" className="block text-sm font-medium text-gray-700">
          Schedule (Cron Expression)
        </label>
        <div className="mt-1">
          <input
            type="text"
            id="report_schedule"
            value={settings.schedule_cron || '0 9 * * *'}
            onChange={(e) => updateField('schedule_cron', e.target.value || undefined)}
            placeholder="0 9 * * *"
            className={`block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 ${
              errors.schedule_cron ? 'border-red-300' : ''
            }`}
          />
        </div>
        {errors.schedule_cron && <p className="mt-1 text-sm text-red-600">{errors.schedule_cron}</p>}
        <p className="mt-1 text-sm text-gray-500">
          Cron expression for report generation (e.g., "0 9 * * *" for daily at 9 AM)
        </p>
      </div>

      <div className="flex items-center">
        <input
          type="checkbox"
          id="email_enabled"
          checked={settings.email_enabled ?? false}
          onChange={(e) => updateField('email_enabled', e.target.checked)}
          className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
        />
        <label htmlFor="email_enabled" className="ml-2 block text-sm text-gray-700">
          Enable Email Delivery
        </label>
      </div>

      <div className="flex items-center">
        <input
          type="checkbox"
          id="file_storage_enabled"
          checked={settings.file_storage_enabled ?? false}
          onChange={(e) => updateField('file_storage_enabled', e.target.checked)}
          className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
        />
        <label htmlFor="file_storage_enabled" className="ml-2 block text-sm text-gray-700">
          Enable File Storage
        </label>
      </div>

      {settings.email_enabled && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Email Recipients</label>
          <div className="space-y-2">
            <div className="flex gap-2">
              <input
                type="email"
                value={newRecipient}
                onChange={(e) => setNewRecipient(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addRecipient())}
                placeholder="Enter email address"
                className="flex-1 rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
              />
              <button
                type="button"
                onClick={addRecipient}
                className="rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500"
              >
                Add
              </button>
            </div>
            <div className="flex flex-wrap gap-2">
              {(settings.recipients || []).map((email) => (
                <span
                  key={email}
                  className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800"
                >
                  {email}
                  <button
                    type="button"
                    onClick={() => removeRecipient(email)}
                    className="text-gray-400 hover:text-gray-600"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          </div>
          <p className="mt-1 text-sm text-gray-500">Email addresses to receive daily reports</p>
        </div>
      )}
    </div>
  );
}

