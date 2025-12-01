/**
 * Priority Weights Configuration Form Component
 * 
 * Form for configuring priority scoring weights with interactive sliders.
 */

'use client';

import { useMemo } from 'react';

interface PriorityWeights {
  sentiment_weight?: number;
  bug_severity_weight?: number;
  engagement_weight?: number;
}

interface PriorityWeightsFormProps {
  weights: PriorityWeights;
  onChange: (weights: PriorityWeights) => void;
  errors?: Record<string, string>;
}

export function PriorityWeightsForm({ weights, onChange, errors = {} }: PriorityWeightsFormProps) {
  const defaultWeights = {
    sentiment_weight: 0.3,
    bug_severity_weight: 0.4,
    engagement_weight: 0.3,
  };

  const currentWeights = {
    sentiment_weight: weights.sentiment_weight ?? defaultWeights.sentiment_weight,
    bug_severity_weight: weights.bug_severity_weight ?? defaultWeights.bug_severity_weight,
    engagement_weight: weights.engagement_weight ?? defaultWeights.engagement_weight,
  };

  const totalWeight = useMemo(() => {
    return currentWeights.sentiment_weight + currentWeights.bug_severity_weight + currentWeights.engagement_weight;
  }, [currentWeights]);

  const updateWeight = (field: keyof PriorityWeights, value: number) => {
    onChange({ ...weights, [field]: value });
  };

  const normalizeWeights = () => {
    if (totalWeight === 0) return;
    const factor = 1 / totalWeight;
    onChange({
      sentiment_weight: currentWeights.sentiment_weight * factor,
      bug_severity_weight: currentWeights.bug_severity_weight * factor,
      engagement_weight: currentWeights.engagement_weight * factor,
    });
  };

  return (
    <div className="space-y-4">
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p className="text-sm text-blue-800">
          <strong>Total Weight:</strong> {totalWeight.toFixed(2)} {totalWeight !== 1 && (
            <span className="text-red-600">(should be 1.0)</span>
          )}
        </p>
        {totalWeight !== 1 && (
          <button
            type="button"
            onClick={normalizeWeights}
            className="mt-2 text-sm text-blue-600 hover:text-blue-800 underline"
          >
            Normalize to 1.0
          </button>
        )}
      </div>

      <div className="space-y-6">
        {/* Sentiment Weight */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label htmlFor="sentiment_weight" className="block text-sm font-medium text-gray-700">
              Sentiment Weight
            </label>
            <span className="text-sm text-gray-500">{currentWeights.sentiment_weight.toFixed(2)}</span>
          </div>
          <input
            type="range"
            id="sentiment_weight"
            min="0"
            max="1"
            step="0.01"
            value={currentWeights.sentiment_weight}
            onChange={(e) => updateWeight('sentiment_weight', parseFloat(e.target.value))}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
          />
          <div className="mt-1 flex justify-between text-xs text-gray-500">
            <span>0</span>
            <span>0.5</span>
            <span>1.0</span>
          </div>
          {errors.sentiment_weight && (
            <p className="mt-1 text-sm text-red-600">{errors.sentiment_weight}</p>
          )}
          <p className="mt-1 text-sm text-gray-500">Weight for sentiment analysis in priority scoring</p>
        </div>

        {/* Bug Severity Weight */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label htmlFor="bug_severity_weight" className="block text-sm font-medium text-gray-700">
              Bug Severity Weight
            </label>
            <span className="text-sm text-gray-500">{currentWeights.bug_severity_weight.toFixed(2)}</span>
          </div>
          <input
            type="range"
            id="bug_severity_weight"
            min="0"
            max="1"
            step="0.01"
            value={currentWeights.bug_severity_weight}
            onChange={(e) => updateWeight('bug_severity_weight', parseFloat(e.target.value))}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
          />
          <div className="mt-1 flex justify-between text-xs text-gray-500">
            <span>0</span>
            <span>0.5</span>
            <span>1.0</span>
          </div>
          {errors.bug_severity_weight && (
            <p className="mt-1 text-sm text-red-600">{errors.bug_severity_weight}</p>
          )}
          <p className="mt-1 text-sm text-gray-500">Weight for bug severity in priority scoring</p>
        </div>

        {/* Engagement Weight */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label htmlFor="engagement_weight" className="block text-sm font-medium text-gray-700">
              Engagement Weight
            </label>
            <span className="text-sm text-gray-500">{currentWeights.engagement_weight.toFixed(2)}</span>
          </div>
          <input
            type="range"
            id="engagement_weight"
            min="0"
            max="1"
            step="0.01"
            value={currentWeights.engagement_weight}
            onChange={(e) => updateWeight('engagement_weight', parseFloat(e.target.value))}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
          />
          <div className="mt-1 flex justify-between text-xs text-gray-500">
            <span>0</span>
            <span>0.5</span>
            <span>1.0</span>
          </div>
          {errors.engagement_weight && (
            <p className="mt-1 text-sm text-red-600">{errors.engagement_weight}</p>
          )}
          <p className="mt-1 text-sm text-gray-500">Weight for engagement (votes, comments, recency) in priority scoring</p>
        </div>
      </div>

      {/* Visual Preview */}
      <div className="mt-6 bg-gray-50 rounded-lg p-4">
        <h4 className="text-sm font-medium text-gray-700 mb-3">Weight Distribution Preview</h4>
        <div className="space-y-2">
          <div>
            <div className="flex justify-between text-xs text-gray-600 mb-1">
              <span>Sentiment</span>
              <span>{(currentWeights.sentiment_weight * 100).toFixed(0)}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full"
                style={{ width: `${currentWeights.sentiment_weight * 100}%` }}
              />
            </div>
          </div>
          <div>
            <div className="flex justify-between text-xs text-gray-600 mb-1">
              <span>Bug Severity</span>
              <span>{(currentWeights.bug_severity_weight * 100).toFixed(0)}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-red-600 h-2 rounded-full"
                style={{ width: `${currentWeights.bug_severity_weight * 100}%` }}
              />
            </div>
          </div>
          <div>
            <div className="flex justify-between text-xs text-gray-600 mb-1">
              <span>Engagement</span>
              <span>{(currentWeights.engagement_weight * 100).toFixed(0)}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-green-600 h-2 rounded-full"
                style={{ width: `${currentWeights.engagement_weight * 100}%` }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

