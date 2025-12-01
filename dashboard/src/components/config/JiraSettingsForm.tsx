/**
 * Jira Settings Form Component
 * 
 * Form for configuring Jira MCP server settings.
 */

'use client';

import { useState } from 'react';

interface JiraSettings {
  server_url?: string;
  project_key?: string;
  resolution_done_statuses?: string[];
  monitoring_poll_interval_seconds?: number;
  monitoring_max_attempts?: number | null;
  monitoring_timeout_seconds?: number | null;
  assignment_strategy?: 'none' | 'round_robin' | 'component_based' | 'priority_based';
  round_robin_assignees?: string[];
  component_assignees?: Record<string, string>;
  priority_assignees?: Record<string, string>;
}

interface JiraSettingsFormProps {
  settings: JiraSettings;
  onChange: (settings: JiraSettings) => void;
  errors?: Record<string, string>;
}

export function JiraSettingsForm({ settings, onChange, errors = {} }: JiraSettingsFormProps) {
  const [newResolutionStatus, setNewResolutionStatus] = useState('');
  const [newAssignee, setNewAssignee] = useState('');

  const updateField = <K extends keyof JiraSettings>(field: K, value: JiraSettings[K]) => {
    onChange({ ...settings, [field]: value });
  };

  const addResolutionStatus = () => {
    if (newResolutionStatus.trim()) {
      const statuses = settings.resolution_done_statuses || [];
      if (!statuses.includes(newResolutionStatus.trim())) {
        updateField('resolution_done_statuses', [...statuses, newResolutionStatus.trim()]);
        setNewResolutionStatus('');
      }
    }
  };

  const removeResolutionStatus = (status: string) => {
    const statuses = settings.resolution_done_statuses || [];
    updateField('resolution_done_statuses', statuses.filter((s) => s !== status));
  };

  const addRoundRobinAssignee = () => {
    if (newAssignee.trim()) {
      const assignees = settings.round_robin_assignees || [];
      if (!assignees.includes(newAssignee.trim())) {
        updateField('round_robin_assignees', [...assignees, newAssignee.trim()]);
        setNewAssignee('');
      }
    }
  };

  const removeRoundRobinAssignee = (assignee: string) => {
    const assignees = settings.round_robin_assignees || [];
    updateField('round_robin_assignees', assignees.filter((a) => a !== assignee));
  };

  return (
    <div className="space-y-4">
      <div>
        <label htmlFor="jira_server_url" className="block text-sm font-medium text-gray-700">
          Server URL
        </label>
        <div className="mt-1">
          <input
            type="url"
            id="jira_server_url"
            value={settings.server_url || ''}
            onChange={(e) => updateField('server_url', e.target.value || undefined)}
            placeholder="https://your-jira-server.com"
            className={`block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 ${
              errors.server_url ? 'border-red-300' : ''
            }`}
          />
        </div>
        {errors.server_url && <p className="mt-1 text-sm text-red-600">{errors.server_url}</p>}
        <p className="mt-1 text-sm text-gray-500">Base URL of the Jira MCP server</p>
      </div>

      <div>
        <label htmlFor="jira_project_key" className="block text-sm font-medium text-gray-700">
          Project Key
        </label>
        <div className="mt-1">
          <input
            type="text"
            id="jira_project_key"
            value={settings.project_key || ''}
            onChange={(e) => updateField('project_key', e.target.value || undefined)}
            placeholder="PROJ"
            className={`block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 ${
              errors.project_key ? 'border-red-300' : ''
            }`}
          />
        </div>
        {errors.project_key && <p className="mt-1 text-sm text-red-600">{errors.project_key}</p>}
        <p className="mt-1 text-sm text-gray-500">Default Jira project key</p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">Resolution Statuses</label>
        <div className="space-y-2">
          <div className="flex gap-2">
            <input
              type="text"
              value={newResolutionStatus}
              onChange={(e) => setNewResolutionStatus(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addResolutionStatus())}
              placeholder="Enter status (e.g., Done)"
              className="flex-1 rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
            />
            <button
              type="button"
              onClick={addResolutionStatus}
              className="rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500"
            >
              Add
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            {(settings.resolution_done_statuses || []).map((status) => (
              <span
                key={status}
                className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800"
              >
                {status}
                <button
                  type="button"
                  onClick={() => removeResolutionStatus(status)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        </div>
        <p className="mt-1 text-sm text-gray-500">Statuses that indicate an issue is resolved</p>
      </div>

      <div>
        <label htmlFor="jira_poll_interval" className="block text-sm font-medium text-gray-700">
          Monitoring Poll Interval (seconds)
        </label>
        <div className="mt-1">
          <input
            type="number"
            id="jira_poll_interval"
            min="5"
            max="3600"
            value={settings.monitoring_poll_interval_seconds || 30}
            onChange={(e) => updateField('monitoring_poll_interval_seconds', parseInt(e.target.value) || undefined)}
            className="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
          />
        </div>
        <p className="mt-1 text-sm text-gray-500">Interval between status checks when monitoring tickets (5-3600 seconds)</p>
      </div>

      <div>
        <label htmlFor="jira_max_attempts" className="block text-sm font-medium text-gray-700">
          Max Monitoring Attempts (Optional)
        </label>
        <div className="mt-1">
          <input
            type="number"
            id="jira_max_attempts"
            min="1"
            value={settings.monitoring_max_attempts === null ? '' : settings.monitoring_max_attempts || ''}
            onChange={(e) =>
              updateField('monitoring_max_attempts', e.target.value ? parseInt(e.target.value) : null)
            }
            placeholder="Unlimited"
            className="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
          />
        </div>
        <p className="mt-1 text-sm text-gray-500">Maximum polling attempts before timeout (leave empty for unlimited)</p>
      </div>

      <div>
        <label htmlFor="jira_timeout" className="block text-sm font-medium text-gray-700">
          Monitoring Timeout (seconds, Optional)
        </label>
        <div className="mt-1">
          <input
            type="number"
            id="jira_timeout"
            min="60"
            value={settings.monitoring_timeout_seconds === null ? '' : settings.monitoring_timeout_seconds || ''}
            onChange={(e) =>
              updateField('monitoring_timeout_seconds', e.target.value ? parseInt(e.target.value) : null)
            }
            placeholder="Unlimited"
            className="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
          />
        </div>
        <p className="mt-1 text-sm text-gray-500">Maximum time to monitor a ticket before timeout (leave empty for unlimited)</p>
      </div>

      <div>
        <label htmlFor="jira_assignment_strategy" className="block text-sm font-medium text-gray-700">
          Assignment Strategy
        </label>
        <div className="mt-1">
          <select
            id="jira_assignment_strategy"
            value={settings.assignment_strategy || 'none'}
            onChange={(e) => updateField('assignment_strategy', e.target.value as any)}
            className="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
          >
            <option value="none">None</option>
            <option value="round_robin">Round Robin</option>
            <option value="component_based">Component Based</option>
            <option value="priority_based">Priority Based</option>
          </select>
        </div>
        <p className="mt-1 text-sm text-gray-500">Strategy for automatic ticket assignment</p>
      </div>

      {settings.assignment_strategy === 'round_robin' && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Round Robin Assignees</label>
          <div className="space-y-2">
            <div className="flex gap-2">
              <input
                type="text"
                value={newAssignee}
                onChange={(e) => setNewAssignee(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addRoundRobinAssignee())}
                placeholder="Enter assignee (email or account ID)"
                className="flex-1 rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
              />
              <button
                type="button"
                onClick={addRoundRobinAssignee}
                className="rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500"
              >
                Add
              </button>
            </div>
            <div className="flex flex-wrap gap-2">
              {(settings.round_robin_assignees || []).map((assignee) => (
                <span
                  key={assignee}
                  className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800"
                >
                  {assignee}
                  <button
                    type="button"
                    onClick={() => removeRoundRobinAssignee(assignee)}
                    className="text-gray-400 hover:text-gray-600"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

