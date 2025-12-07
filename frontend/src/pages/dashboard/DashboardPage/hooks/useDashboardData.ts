/**
 * Dashboard data hook - Manages dashboard stats and jobs data
 */

import { useQuery } from '@tanstack/react-query';
import { jobsApi, usersApi } from '../../../../services/api';

export interface DashboardStats {
  total_jobs?: number;
  pending_jobs?: number;
  success_rate?: number;
  credits_used_this_month?: number;
  monthly_credit_limit?: number;
}

export interface JobData {
  id: string;
  status: string;
  display_name?: string;
  original_filename: string;
  created_at: string;
  progress?: number;
  output_url?: string;
}

export function useDashboardData() {
  // Get user stats (silently fail - stats are optional)
  const { data: stats } = useQuery<DashboardStats>({
    queryKey: ['user-stats'],
    queryFn: usersApi.getUserStats,
    refetchInterval: 30000, // Refresh every 30 seconds
    retry: false,
    enabled: true,
  });

  // Get recent jobs (silently fail - will show empty state)
  const {
    data: jobsResponse,
    refetch: refetchJobs,
  } = useQuery<{ jobs: JobData[]; total: number }>({
    queryKey: ['recent-jobs'],
    queryFn: () => jobsApi.getUserJobs({ limit: 5 }),
    refetchInterval: 10000, // Refresh every 10 seconds
    retry: false,
    enabled: true,
  });

  // Extract jobs array from response, default to empty array
  const recentJobs: JobData[] = jobsResponse?.jobs ?? [];

  return {
    stats,
    recentJobs,
    refetchJobs,
  };
}
