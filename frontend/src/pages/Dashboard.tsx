import { useEffect, useMemo } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Search, Settings, FileText, Send, CheckCircle, Clock, XCircle, RefreshCw } from 'lucide-react'
import { api } from '../services/api'
import StatsCard from '../components/StatsCard'
import RecentRFPs from '../components/RecentRFPs'
import { RFPStats, SubmissionStats, RFPOpportunity } from '../types/rfp'
import {
  PipelineOverviewSkeleton,
  SubmissionStatsSkeleton,
  RecentRFPsSkeleton,
  DashboardHeaderSkeleton
} from '../components/DashboardSkeletons'
import { DashboardErrorBoundary, SectionError } from '../components/DashboardErrorBoundary'
import { LoadingProgress, LoadingStatus } from '../components/LoadingProgress'
import { Button } from '@/components/ui/button'

// Cache configuration
const STALE_TIME = 30 * 1000 // 30 seconds - data considered fresh
const CACHE_TIME = 5 * 60 * 1000 // 5 minutes - keep in cache
const TIMEOUT_MS = 10 * 1000 // 10 seconds timeout

// Default/fallback data for timeout scenarios
const DEFAULT_STATS: RFPStats = {
  total_discovered: 0,
  in_pipeline: 0,
  approved_count: 0,
  rejected_count: 0,
  submitted_count: 0,
  pending_reviews: 0
}

const DEFAULT_SUBMISSION_STATS: SubmissionStats = {
  total_submissions: 0,
  queued: 0,
  submitted: 0,
  confirmed: 0,
  failed: 0,
  success_rate: 0
}

// Helper to create query with timeout
function createQueryFnWithTimeout<T>(queryFn: () => Promise<T>) {
  return async ({ signal }: { signal?: AbortSignal }) => {
    const timeoutPromise = new Promise<never>((_, reject) => {
      const timeoutId = setTimeout(() => {
        reject(new Error('Request timed out'))
      }, TIMEOUT_MS)
      signal?.addEventListener('abort', () => clearTimeout(timeoutId))
    })
    return Promise.race([queryFn(), timeoutPromise])
  }
}

export default function Dashboard() {
  const queryClient = useQueryClient()

  // Fetch all data in parallel with timeout and caching
  const {
    data: stats,
    isLoading: statsLoading,
    isError: statsError,
    error: statsErrorObj,
    isFetching: statsFetching,
    refetch: refetchStats
  } = useQuery<RFPStats>({
    queryKey: ['rfp-stats'],
    queryFn: createQueryFnWithTimeout(() => api.getRFPStats()),
    staleTime: STALE_TIME,
    gcTime: CACHE_TIME,
    retry: 2,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 5000),
    placeholderData: DEFAULT_STATS,
    refetchOnWindowFocus: false
  })

  const {
    data: submissionStats,
    isLoading: submissionLoading,
    isError: submissionError,
    error: submissionErrorObj,
    isFetching: submissionFetching,
    refetch: refetchSubmission
  } = useQuery<SubmissionStats>({
    queryKey: ['submission-stats'],
    queryFn: createQueryFnWithTimeout(() => api.getSubmissionStats()),
    staleTime: STALE_TIME,
    gcTime: CACHE_TIME,
    retry: 2,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 5000),
    placeholderData: DEFAULT_SUBMISSION_STATS,
    refetchOnWindowFocus: false
  })

  const {
    data: recentRFPs,
    isLoading: rfpsLoading,
    isError: rfpsError,
    error: rfpsErrorObj,
    isFetching: rfpsFetching,
    refetch: refetchRFPs
  } = useQuery<RFPOpportunity[]>({
    queryKey: ['recent-rfps'],
    queryFn: createQueryFnWithTimeout(() => api.getRecentRFPs()),
    staleTime: STALE_TIME,
    gcTime: CACHE_TIME,
    retry: 2,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 5000),
    placeholderData: [] as RFPOpportunity[],
    refetchOnWindowFocus: false
  })

  // Calculate loading states for progress indicator
  const loadingItems = useMemo(() => {
    const getStatus = (loading: boolean, error: boolean, fetching: boolean): LoadingStatus => {
      if (error) return 'error'
      if (loading || fetching) return 'loading'
      return 'success'
    }

    return [
      { id: 'stats', label: 'Pipeline Stats', status: getStatus(statsLoading, statsError, statsFetching) },
      { id: 'submission', label: 'Submissions', status: getStatus(submissionLoading, submissionError, submissionFetching) },
      { id: 'rfps', label: 'Recent RFPs', status: getStatus(rfpsLoading, rfpsError, rfpsFetching) }
    ]
  }, [statsLoading, statsError, statsFetching, submissionLoading, submissionError, submissionFetching, rfpsLoading, rfpsError, rfpsFetching])

  const isInitialLoading = statsLoading && submissionLoading && rfpsLoading
  const isAnyLoading = statsLoading || submissionLoading || rfpsLoading

  // Prefetch data on mount for faster subsequent loads
  useEffect(() => {
    // These will be cached and available instantly on next visit
    queryClient.prefetchQuery({
      queryKey: ['rfp-stats'],
      queryFn: () => api.getRFPStats(),
      staleTime: STALE_TIME
    })
  }, [queryClient])

  // Cleanup on unmount - cancel any pending requests
  useEffect(() => {
    return () => {
      // React Query handles cancellation via AbortController automatically
      // when queries are unmounted, but we can also manually cancel here
      queryClient.cancelQueries({ queryKey: ['rfp-stats'] })
      queryClient.cancelQueries({ queryKey: ['submission-stats'] })
      queryClient.cancelQueries({ queryKey: ['recent-rfps'] })
    }
  }, [queryClient])

  const handleRefreshAll = () => {
    refetchStats()
    refetchSubmission()
    refetchRFPs()
  }

  // Show loading progress during initial load
  if (isInitialLoading) {
    return (
      <div className="space-y-8">
        <DashboardHeaderSkeleton />

        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Loading Dashboard...
          </h3>
          <LoadingProgress items={loadingItems} />
        </div>

        <PipelineOverviewSkeleton />
        <SubmissionStatsSkeleton />
        <RecentRFPsSkeleton />
      </div>
    )
  }

  return (
    <DashboardErrorBoundary sectionName="Dashboard" onRetry={handleRefreshAll}>
      <div className="space-y-8">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl shadow-xl p-8 text-white">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-3xl font-bold">RFP Dashboard</h1>
              <p className="mt-2 text-blue-100 text-lg">
                Overview of your RFP pipeline and submission status
              </p>
            </div>
            <Button
              variant="secondary"
              size="sm"
              onClick={handleRefreshAll}
              disabled={isAnyLoading}
              className="bg-white/20 hover:bg-white/30 text-white border-white/30"
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${isAnyLoading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </div>

          {/* Show mini loading progress in header when refetching */}
          {isAnyLoading && !isInitialLoading && (
            <div className="mt-4 pt-4 border-t border-white/20">
              <LoadingProgress items={loadingItems} />
            </div>
          )}
        </div>

        {/* Main Stats Grid */}
        <DashboardErrorBoundary sectionName="Pipeline Overview" onRetry={refetchStats}>
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              RFP Pipeline Overview
            </h2>

            {statsError ? (
              <SectionError
                sectionName="Pipeline Overview"
                error={statsErrorObj as Error}
                onRetry={refetchStats}
                isRetrying={statsFetching}
              />
            ) : statsLoading ? (
              <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
                {[...Array(4)].map((_, i) => (
                  <div key={i} className="animate-pulse">
                    <div className="bg-gray-200 dark:bg-gray-700 rounded-xl h-28" />
                  </div>
                ))}
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
                <StatsCard
                  title="Total Discovered"
                  value={stats?.total_discovered || 0}
                  icon={Search}
                  color="blue"
                />
                <StatsCard
                  title="In Pipeline"
                  value={stats?.in_pipeline || 0}
                  icon={Settings}
                  color="purple"
                />
                <StatsCard
                  title="Pending Review"
                  value={stats?.pending_reviews || 0}
                  icon={FileText}
                  color="orange"
                  highlight={(stats?.pending_reviews || 0) > 0}
                />
                <StatsCard
                  title="Submitted"
                  value={stats?.submitted_count || 0}
                  icon={Send}
                  color="green"
                />
              </div>
            )}
          </div>
        </DashboardErrorBoundary>

        {/* Submission Stats */}
        <DashboardErrorBoundary sectionName="Submission Performance" onRetry={refetchSubmission}>
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Submission Performance
            </h2>

            {submissionError ? (
              <SectionError
                sectionName="Submission Performance"
                error={submissionErrorObj as Error}
                onRetry={refetchSubmission}
                isRetrying={submissionFetching}
              />
            ) : submissionLoading ? (
              <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
                {[...Array(3)].map((_, i) => (
                  <div key={i} className="animate-pulse">
                    <div className="bg-gray-200 dark:bg-gray-700 rounded-xl h-28" />
                  </div>
                ))}
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
                <StatsCard
                  title="Success Rate"
                  value={`${submissionStats?.success_rate?.toFixed(1) || 0}%`}
                  icon={CheckCircle}
                  color="green"
                />
                <StatsCard
                  title="Queued"
                  value={submissionStats?.queued || 0}
                  icon={Clock}
                  color="orange"
                />
                <StatsCard
                  title="Failed"
                  value={submissionStats?.failed || 0}
                  icon={XCircle}
                  color="red"
                  highlight={(submissionStats?.failed || 0) > 0}
                />
              </div>
            )}
          </div>
        </DashboardErrorBoundary>

        {/* Recent RFPs */}
        <DashboardErrorBoundary sectionName="Recent RFPs" onRetry={refetchRFPs}>
          {rfpsError ? (
            <SectionError
              sectionName="Recent RFPs"
              error={rfpsErrorObj as Error}
              onRetry={refetchRFPs}
              isRetrying={rfpsFetching}
            />
          ) : rfpsLoading ? (
            <RecentRFPsSkeleton />
          ) : (
            <RecentRFPs rfps={recentRFPs || []} />
          )}
        </DashboardErrorBoundary>
      </div>
    </DashboardErrorBoundary>
  )
}
