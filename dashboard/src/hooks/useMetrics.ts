/**
 * useMetrics Hook
 * 
 * React Query hook for fetching and managing metrics data.
 */

import { useQuery } from '@tanstack/react-query';
import { metricsApi, MetricsResponse } from '../services/api/metrics';

interface UseMetricsOptions {
  startDate?: string;
  endDate?: string;
  refetchInterval?: number | false;
  enabled?: boolean;
}

export function useMetrics(options: UseMetricsOptions = {}) {
  const { startDate, endDate, refetchInterval = 30000, enabled = true } = options;

  return useQuery<MetricsResponse>({
    queryKey: ['metrics', startDate, endDate],
    queryFn: () => metricsApi.get({ start_date: startDate, end_date: endDate }),
    refetchInterval,
    enabled,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

