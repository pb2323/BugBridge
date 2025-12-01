/**
 * useFeedback Hook
 * 
 * React Query hook for fetching and managing feedback posts.
 */

import { useQuery } from '@tanstack/react-query';
import { feedbackApi, FeedbackListParams, FeedbackListResponse, FeedbackPost } from '../services/api/feedback';

interface UseFeedbackListOptions extends FeedbackListParams {
  enabled?: boolean;
}

export function useFeedbackList(options: UseFeedbackListOptions = {}) {
  const { enabled = true, ...params } = options;

  return useQuery<FeedbackListResponse>({
    queryKey: ['feedback', 'list', params],
    queryFn: () => feedbackApi.list(params),
    enabled,
    staleTime: 30 * 1000, // 30 seconds
  });
}

export function useFeedbackPost(postId: string, enabled: boolean = true) {
  return useQuery<FeedbackPost>({
    queryKey: ['feedback', 'post', postId],
    queryFn: () => feedbackApi.get(postId),
    enabled: enabled && !!postId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

