/**
 * XAI Settings Form Component
 * 
 * Form for configuring XAI/Grok API settings.
 */

'use client';

import { useState } from 'react';
import { EyeIcon, EyeSlashIcon } from '@heroicons/react/24/outline';

interface XAISettings {
  api_key?: string;
  model?: string;
  temperature?: number;
}

interface XAISettingsFormProps {
  settings: XAISettings;
  onChange: (settings: XAISettings) => void;
  errors?: Record<string, string>;
}

const AVAILABLE_MODELS = [
  'grok-2-1212',
  'grok-2-vision-1212',
  'grok-beta',
  'grok-vision-beta',
  'grok-2-latest',
  'grok-2-vision-latest',
  'grok-4-fast-reasoning',
];

export function XAISettingsForm({ settings, onChange, errors = {} }: XAISettingsFormProps) {
  const [showApiKey, setShowApiKey] = useState(false);

  const updateField = <K extends keyof XAISettings>(field: K, value: XAISettings[K]) => {
    onChange({ ...settings, [field]: value });
  };

  return (
    <div className="space-y-4">
      <div>
        <label htmlFor="xai_api_key" className="block text-sm font-medium text-gray-700">
          API Key
        </label>
        <div className="mt-1 relative">
          <input
            type={showApiKey ? 'text' : 'password'}
            id="xai_api_key"
            value={settings.api_key || ''}
            onChange={(e) => updateField('api_key', e.target.value || undefined)}
            placeholder="Enter XAI API key"
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
        <p className="mt-1 text-sm text-gray-500">Your XAI (xAI) API token</p>
      </div>

      <div>
        <label htmlFor="xai_model" className="block text-sm font-medium text-gray-700">
          Model
        </label>
        <div className="mt-1">
          <select
            id="xai_model"
            value={settings.model || 'grok-4-fast-reasoning'}
            onChange={(e) => updateField('model', e.target.value || undefined)}
            className={`block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 ${
              errors.model ? 'border-red-300' : ''
            }`}
          >
            {AVAILABLE_MODELS.map((model) => (
              <option key={model} value={model}>
                {model}
              </option>
            ))}
          </select>
        </div>
        {errors.model && <p className="mt-1 text-sm text-red-600">{errors.model}</p>}
        <p className="mt-1 text-sm text-gray-500">XAI/Grok model to use for AI operations</p>
      </div>

      <div>
        <label htmlFor="xai_temperature" className="block text-sm font-medium text-gray-700">
          Temperature
        </label>
        <div className="mt-1">
          <input
            type="number"
            id="xai_temperature"
            min="0"
            max="2"
            step="0.1"
            value={settings.temperature !== undefined ? settings.temperature : 0}
            onChange={(e) => updateField('temperature', parseFloat(e.target.value) || 0)}
            className={`block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 ${
              errors.temperature ? 'border-red-300' : ''
            }`}
          />
        </div>
        {errors.temperature && <p className="mt-1 text-sm text-red-600">{errors.temperature}</p>}
        <p className="mt-1 text-sm text-gray-500">
          Temperature for AI responses (0 = deterministic, 2 = creative). Recommended: 0 for deterministic agents.
        </p>
      </div>
    </div>
  );
}

