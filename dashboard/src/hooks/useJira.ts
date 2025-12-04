/**
 * useJira Hook
 * 
 * React Query hook for fetching and managing Jira tickets data.
 */

import { useQuery } from '@tanstack/react-query';
import { jiraApi, JiraTicketListResponse, JiraTicketListParams } from '../services/api/jira';

export function useJiraList(params?: JiraTicketListParams) {
  return useQuery<JiraTicketListResponse>({
    queryKey: ['jira-tickets', params],
    queryFn: () => jiraApi.list(params),
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
}

export function useJiraTicket(ticketId: string) {
  return useQuery({
    queryKey: ['jira-ticket', ticketId],
    queryFn: () => jiraApi.get(ticketId),
    enabled: !!ticketId,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
}

