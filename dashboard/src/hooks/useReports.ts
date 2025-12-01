/**
 * useReports Hook
 * 
 * React Query hook for fetching and managing reports.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { reportsApi, Report, ReportListResponse, ReportGenerateRequest, ReportDetail } from '../services/api/reports';

interface UseReportsListOptions {
  start_date?: string;
  end_date?: string;
  report_type?: string;
  page?: number;
  page_size?: number;
  enabled?: boolean;
}

export function useReportsList(options: UseReportsListOptions = {}) {
  const { enabled = true, ...params } = options;

  return useQuery<ReportListResponse>({
    queryKey: ['reports', 'list', params],
    queryFn: () => reportsApi.list(params),
    enabled,
    staleTime: 30 * 1000, // 30 seconds
  });
}

export function useReport(reportId: string, enabled: boolean = true) {
  return useQuery<ReportDetail>({
    queryKey: ['reports', 'detail', reportId],
    queryFn: () => reportsApi.get(reportId),
    enabled: enabled && !!reportId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useGenerateReport() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: ReportGenerateRequest) => reportsApi.generate(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports'] });
    },
  });
}

