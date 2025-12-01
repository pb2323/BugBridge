/**
 * Configuration Settings Page
 * 
 * Main page for managing all BugBridge configuration settings.
 */

'use client';

import { useState, useEffect } from 'react';
import { DashboardLayout } from '../../components/layout/DashboardLayout';
import { ErrorBoundary } from '../../components/common/ErrorBoundary';
import { ProtectedRoute } from '../../components/auth/ProtectedRoute';
import { RequireRole } from '../../components/auth/RequireRole';
import { CannySettingsForm } from '../../components/config/CannySettingsForm';
import { JiraSettingsForm } from '../../components/config/JiraSettingsForm';
import { XAISettingsForm } from '../../components/config/XAISettingsForm';
import { PriorityWeightsForm } from '../../components/config/PriorityWeightsForm';
import { ReportingSettingsForm } from '../../components/config/ReportingSettingsForm';
import { configApi } from '../../services/api/config';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { CheckCircleIcon, XCircleIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline';
import { SkeletonCard } from '../../components/common/SkeletonLoader';

interface ConfigData {
  canny: Record<string, any>;
  jira: Record<string, any>;
  xai: Record<string, any>;
  reporting: Record<string, any>;
  agent: Record<string, any>;
}

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'canny' | 'jira' | 'xai' | 'priority' | 'reporting'>('canny');
  const [formData, setFormData] = useState<Partial<ConfigData>>({});
  const [errors, setErrors] = useState<Record<string, Record<string, string>>>({});
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'success' | 'error'>('idle');
  const [saveMessage, setSaveMessage] = useState('');

  const { data: config, isLoading, error, refetch } = useQuery<ConfigData>({
    queryKey: ['config'],
    queryFn: () => configApi.get(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  const updateMutation = useMutation({
    mutationFn: (data: Partial<ConfigData>) => configApi.update(data),
    onSuccess: () => {
      setSaveStatus('success');
      setSaveMessage('Configuration saved successfully!');
      queryClient.invalidateQueries({ queryKey: ['config'] });
      setTimeout(() => {
        setSaveStatus('idle');
        setSaveMessage('');
      }, 3000);
    },
    onError: (error: any) => {
      setSaveStatus('error');
      setSaveMessage(error?.response?.data?.detail || 'Failed to save configuration');
      setTimeout(() => {
        setSaveStatus('idle');
        setSaveMessage('');
      }, 5000);
    },
  });

  useEffect(() => {
    if (config) {
      setFormData({
        canny: config.canny || {},
        jira: config.jira || {},
        xai: config.xai || {},
        reporting: config.reporting || {},
        agent: config.agent || {},
      });
    }
  }, [config]);

  const validateForm = (): boolean => {
    const newErrors: Record<string, Record<string, string>> = {};

    // Canny validation
    if (activeTab === 'canny') {
      if (!formData.canny?.subdomain) {
        newErrors.canny = { ...newErrors.canny, subdomain: 'Subdomain is required' };
      }
      if (!formData.canny?.board_id) {
        newErrors.canny = { ...newErrors.canny, board_id: 'Board ID is required' };
      }
      if (formData.canny?.sync_interval_minutes && (formData.canny.sync_interval_minutes < 1 || formData.canny.sync_interval_minutes > 1440)) {
        newErrors.canny = { ...newErrors.canny, sync_interval_minutes: 'Sync interval must be between 1 and 1440 minutes' };
      }
    }

    // Jira validation
    if (activeTab === 'jira') {
      if (!formData.jira?.server_url) {
        newErrors.jira = { ...newErrors.jira, server_url: 'Server URL is required' };
      }
      if (!formData.jira?.project_key) {
        newErrors.jira = { ...newErrors.jira, project_key: 'Project key is required' };
      }
    }

    // XAI validation
    if (activeTab === 'xai') {
      if (formData.xai?.temperature !== undefined && (formData.xai.temperature < 0 || formData.xai.temperature > 2)) {
        newErrors.xai = { ...newErrors.xai, temperature: 'Temperature must be between 0 and 2' };
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSave = () => {
    if (!validateForm()) {
      setSaveStatus('error');
      setSaveMessage('Please fix validation errors before saving');
      return;
    }

    setSaveStatus('saving');
    updateMutation.mutate(formData);
  };

  const handleCancel = () => {
    if (config) {
      setFormData({
        canny: config.canny || {},
        jira: config.jira || {},
        xai: config.xai || {},
        reporting: config.reporting || {},
        agent: config.agent || {},
      });
    }
    setErrors({});
    setSaveStatus('idle');
    setSaveMessage('');
  };

  if (isLoading) {
    return (
      <ErrorBoundary>
        <DashboardLayout>
          <div className="space-y-6">
            <SkeletonCard />
            <SkeletonCard />
          </div>
        </DashboardLayout>
      </ErrorBoundary>
    );
  }

  if (error) {
    return (
      <ErrorBoundary>
        <DashboardLayout>
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800">Error loading configuration. Please try again.</p>
            <button
              onClick={() => refetch()}
              className="mt-2 rounded-md bg-red-600 px-3 py-2 text-sm font-semibold text-white hover:bg-red-500"
            >
              Retry
            </button>
          </div>
        </DashboardLayout>
      </ErrorBoundary>
    );
  }

  const tabs = [
    { id: 'canny', name: 'Canny.io', icon: '📊' },
    { id: 'jira', name: 'Jira', icon: '🎫' },
    { id: 'xai', name: 'XAI/Grok', icon: '🤖' },
    { id: 'priority', name: 'Priority Weights', icon: '⚖️' },
    { id: 'reporting', name: 'Reporting', icon: '📈' },
  ];

  return (
    <ErrorBoundary>
      <ProtectedRoute requireAdmin>
        <DashboardLayout>
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Configuration Settings</h1>
              <p className="mt-1 text-sm text-gray-500">Manage BugBridge platform settings and integrations</p>
            </div>
          </div>

          {/* Save Status */}
          {saveStatus !== 'idle' && (
            <div
              className={`rounded-lg p-4 flex items-center gap-2 ${
                saveStatus === 'success'
                  ? 'bg-green-50 border border-green-200'
                  : saveStatus === 'error'
                  ? 'bg-red-50 border border-red-200'
                  : 'bg-blue-50 border border-blue-200'
              }`}
            >
              {saveStatus === 'success' && <CheckCircleIcon className="h-5 w-5 text-green-600" />}
              {saveStatus === 'error' && <XCircleIcon className="h-5 w-5 text-red-600" />}
              {saveStatus === 'saving' && <ExclamationTriangleIcon className="h-5 w-5 text-blue-600 animate-spin" />}
              <p
                className={`text-sm font-medium ${
                  saveStatus === 'success'
                    ? 'text-green-800'
                    : saveStatus === 'error'
                    ? 'text-red-800'
                    : 'text-blue-800'
                }`}
              >
                {saveMessage || (saveStatus === 'saving' ? 'Saving...' : '')}
              </p>
            </div>
          )}

          {/* Tabs */}
          <div className="border-b border-gray-200">
            <nav className="-mb-px flex space-x-8" aria-label="Tabs">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`${
                    activeTab === tab.id
                      ? 'border-indigo-500 text-indigo-600'
                      : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                  } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2`}
                >
                  <span>{tab.icon}</span>
                  {tab.name}
                </button>
              ))}
            </nav>
          </div>

          {/* Form Content */}
          <div className="bg-white rounded-lg shadow p-6">
            {activeTab === 'canny' && (
              <CannySettingsForm
                settings={formData.canny || {}}
                onChange={(settings) => setFormData({ ...formData, canny: settings })}
                errors={errors.canny || {}}
              />
            )}

            {activeTab === 'jira' && (
              <JiraSettingsForm
                settings={formData.jira || {}}
                onChange={(settings) => setFormData({ ...formData, jira: settings })}
                errors={errors.jira || {}}
              />
            )}

            {activeTab === 'xai' && (
              <XAISettingsForm
                settings={formData.xai || {}}
                onChange={(settings) => setFormData({ ...formData, xai: settings })}
                errors={errors.xai || {}}
              />
            )}

            {activeTab === 'priority' && (
              <PriorityWeightsForm
                weights={formData.agent || {}}
                onChange={(weights) => setFormData({ ...formData, agent: weights })}
                errors={errors.agent || {}}
              />
            )}

            {activeTab === 'reporting' && (
              <ReportingSettingsForm
                settings={formData.reporting || {}}
                onChange={(settings) => setFormData({ ...formData, reporting: settings })}
                errors={errors.reporting || {}}
              />
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-end gap-4">
            <button
              onClick={handleCancel}
              className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-semibold text-gray-700 shadow-sm hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saveStatus === 'saving'}
              className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saveStatus === 'saving' ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </div>
      </DashboardLayout>
      </ProtectedRoute>
    </ErrorBoundary>
  );
}
