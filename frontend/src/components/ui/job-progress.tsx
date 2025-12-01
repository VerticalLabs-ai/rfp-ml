import * as React from 'react'
import { useQuery } from '@tanstack/react-query'
import { AlertCircle, CheckCircle2, Clock, Loader2, XCircle } from 'lucide-react'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { cn } from '@/lib/utils'

export type JobStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'

export interface JobStatusResponse {
  job_id: string
  status: JobStatus
  progress?: number
  result?: any
  error?: string
  created_at?: string
  updated_at?: string
}

export interface JobProgressProps {
  /**
   * The job ID to track
   */
  jobId: string
  /**
   * Title to display
   */
  title?: string
  /**
   * Callback when job completes successfully
   */
  onComplete?: (result: any) => void
  /**
   * Callback when job fails
   */
  onError?: (error: string) => void
  /**
   * Polling interval in ms (default: 1000)
   */
  pollInterval?: number
  /**
   * Custom API endpoint (default: /api/v1/jobs/{jobId})
   */
  apiEndpoint?: string
  /**
   * Custom class name
   */
  className?: string
  /**
   * Show compact version without card wrapper
   */
  compact?: boolean
}

/**
 * Job progress tracking component with automatic polling.
 *
 * Features:
 * - Auto-polls job status until completion
 * - Shows progress bar with percentage
 * - Visual status indicators
 * - Callbacks for completion/error
 * - Compact mode for inline display
 *
 * @example
 * ```tsx
 * <JobProgress
 *   jobId="abc123"
 *   title="Generating proposal..."
 *   onComplete={(result) => console.log('Done:', result)}
 *   onError={(error) => toast.error(error)}
 * />
 * ```
 */
function JobProgress({
  jobId,
  title,
  onComplete,
  onError,
  pollInterval = 1000,
  apiEndpoint,
  className,
  compact = false,
}: JobProgressProps) {
  const completedRef = React.useRef(false)
  const erroredRef = React.useRef(false)

  const endpoint = apiEndpoint || `/api/v1/jobs/${jobId}`

  const { data: status, isLoading, error } = useQuery<JobStatusResponse>({
    queryKey: ['job', jobId],
    queryFn: async () => {
      const response = await fetch(endpoint)
      if (!response.ok) {
        throw new Error(`Failed to fetch job status: ${response.statusText}`)
      }
      return response.json()
    },
    refetchInterval: (query) => {
      const data = query.state.data
      // Stop polling when job is done
      if (data?.status === 'completed' || data?.status === 'failed' || data?.status === 'cancelled') {
        return false
      }
      return pollInterval
    },
    enabled: !!jobId,
  })

  // Handle completion callback
  React.useEffect(() => {
    if (status?.status === 'completed' && !completedRef.current) {
      completedRef.current = true
      onComplete?.(status.result)
    }
    if (status?.status === 'failed' && !erroredRef.current) {
      erroredRef.current = true
      onError?.(status.error || 'Job failed')
    }
  }, [status?.status, status?.result, status?.error, onComplete, onError])

  // Reset refs when jobId changes
  React.useEffect(() => {
    completedRef.current = false
    erroredRef.current = false
  }, [jobId])

  const progress = status?.progress ?? 0
  const jobStatus = status?.status ?? 'pending'

  const statusConfig = {
    pending: {
      icon: Clock,
      text: 'Pending...',
      color: 'text-muted-foreground',
    },
    running: {
      icon: Loader2,
      text: 'Processing...',
      color: 'text-primary',
      iconClass: 'animate-spin',
    },
    completed: {
      icon: CheckCircle2,
      text: 'Completed',
      color: 'text-green-500',
    },
    failed: {
      icon: XCircle,
      text: 'Failed',
      color: 'text-destructive',
    },
    cancelled: {
      icon: AlertCircle,
      text: 'Cancelled',
      color: 'text-muted-foreground',
    },
  }

  const config = statusConfig[jobStatus]
  const Icon = config.icon

  if (compact) {
    return (
      <div className={cn('flex items-center gap-3', className)}>
        <Icon className={cn('h-4 w-4', config.color, config.iconClass)} />
        <div className="flex-1">
          <Progress value={progress} className="h-2" />
        </div>
        <span className={cn('text-sm', config.color)}>
          {progress > 0 ? `${progress}%` : config.text}
        </span>
      </div>
    )
  }

  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-sm font-medium">
          <Icon className={cn('h-4 w-4', config.color, config.iconClass)} />
          {title || 'Processing...'}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        <Progress value={progress} />
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span className={config.color}>{config.text}</span>
          <span>{progress}% complete</span>
        </div>
        {jobStatus === 'failed' && status?.error && (
          <p className="text-xs text-destructive">
            Error: {status.error}
          </p>
        )}
      </CardContent>
    </Card>
  )
}

/**
 * Hook for tracking job progress without UI
 */
function useJobProgress(jobId: string | null, options?: {
  pollInterval?: number
  apiEndpoint?: string
  onComplete?: (result: any) => void
  onError?: (error: string) => void
}) {
  const {
    pollInterval = 1000,
    apiEndpoint,
    onComplete,
    onError,
  } = options || {}

  const completedRef = React.useRef(false)
  const erroredRef = React.useRef(false)

  const endpoint = apiEndpoint || (jobId ? `/api/v1/jobs/${jobId}` : '')

  const query = useQuery<JobStatusResponse>({
    queryKey: ['job', jobId],
    queryFn: async () => {
      const response = await fetch(endpoint)
      if (!response.ok) {
        throw new Error(`Failed to fetch job status: ${response.statusText}`)
      }
      return response.json()
    },
    refetchInterval: (q) => {
      const data = q.state.data
      if (data?.status === 'completed' || data?.status === 'failed' || data?.status === 'cancelled') {
        return false
      }
      return pollInterval
    },
    enabled: !!jobId,
  })

  // Handle callbacks
  React.useEffect(() => {
    if (query.data?.status === 'completed' && !completedRef.current) {
      completedRef.current = true
      onComplete?.(query.data.result)
    }
    if (query.data?.status === 'failed' && !erroredRef.current) {
      erroredRef.current = true
      onError?.(query.data.error || 'Job failed')
    }
  }, [query.data?.status, query.data?.result, query.data?.error, onComplete, onError])

  // Reset refs when jobId changes
  React.useEffect(() => {
    completedRef.current = false
    erroredRef.current = false
  }, [jobId])

  return {
    status: query.data?.status ?? 'pending',
    progress: query.data?.progress ?? 0,
    result: query.data?.result,
    error: query.data?.error,
    isLoading: query.isLoading,
    isComplete: query.data?.status === 'completed',
    isFailed: query.data?.status === 'failed',
    isRunning: query.data?.status === 'running',
  }
}

export { JobProgress, useJobProgress }
