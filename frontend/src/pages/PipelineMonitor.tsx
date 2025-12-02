/**
 * Pipeline Monitor page with real-time updates.
 *
 * Features:
 * - Timeout handling (10 seconds) with graceful fallback
 * - Error boundary with retry option
 * - Skeleton loaders during initial load
 * - Cached data shown immediately, fresh data fetched in background
 * - WebSocket subscription for real-time pipeline updates
 * - Pagination for large datasets
 */
import { useEffect, useCallback, useState, useMemo } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { RefreshCw, Clock, AlertCircle, Wifi, WifiOff } from 'lucide-react'
import PipelineKanban from '../components/PipelineKanban'
import { PipelineFullSkeleton } from '../components/PipelineSkeletons'
import { PipelineErrorBoundary, PipelineError, PipelineEmpty } from '../components/PipelineErrorBoundary'
import { Button } from '../components/ui/button'
import { api } from '../services/api'
import { toast } from 'sonner'

const TIMEOUT_MS = 10000 // 10 second timeout
const STALE_TIME = 30000 // 30 seconds before data is considered stale
const REFETCH_INTERVAL = 60000 // Auto-refetch every 60 seconds

interface RFP {
  id: number
  rfp_id: string
  title: string
  agency: string | null
  current_stage: string
  triage_score: number | null
  created_at: string | null
  updated_at: string | null
}

interface PipelineStatus {
  stages: Record<string, number>
  rfps: RFP[]
  total_count: number
  timestamp: string
  cached: boolean
  cache_age_seconds?: number
  stale?: boolean
}

interface StageInfo {
  key: string
  label: string
  color: string
  count: number
}

const STAGE_CONFIG = [
  { key: 'discovered', label: 'Discovered', color: 'blue' },
  { key: 'triaged', label: 'Triaged', color: 'purple' },
  { key: 'analyzing', label: 'Analyzing', color: 'yellow' },
  { key: 'pricing', label: 'Pricing', color: 'orange' },
  { key: 'approved', label: 'Approved', color: 'green' },
  { key: 'submitted', label: 'Submitted', color: 'teal' },
]

// Fetch with timeout
async function fetchPipelineWithTimeout(
  options: { useCache: boolean } = { useCache: true }
): Promise<PipelineStatus> {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_MS)

  try {
    const result = await api.getPipelineStatus({ useCache: options.useCache })
    clearTimeout(timeoutId)
    return result
  } catch (error: any) {
    clearTimeout(timeoutId)
    if (error.name === 'AbortError' || error.code === 'ECONNABORTED') {
      throw new Error('Request timed out. The server took too long to respond.')
    }
    throw error
  }
}

export default function PipelineMonitor() {
  const queryClient = useQueryClient()
  const [wsConnected, setWsConnected] = useState(false)
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null)

  // Main pipeline query with timeout and caching
  const {
    data: pipelineStatus,
    isLoading,
    isFetching,
    error,
    refetch,
    isError
  } = useQuery<PipelineStatus, Error>({
    queryKey: ['pipeline-status'],
    queryFn: () => fetchPipelineWithTimeout({ useCache: true }),
    staleTime: STALE_TIME,
    gcTime: 5 * 60 * 1000, // 5 minutes
    refetchInterval: REFETCH_INTERVAL,
    retry: 1,
    retryDelay: 1000,
    placeholderData: (previousData) => previousData, // Show stale data while fetching
  })

  // WebSocket connection for real-time updates
  useEffect(() => {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/pipeline`

    let ws: WebSocket | null = null
    let reconnectTimeout: NodeJS.Timeout | null = null
    let reconnectAttempt = 0
    const maxReconnectAttempts = 5

    function connect() {
      try {
        ws = new WebSocket(wsUrl)

        ws.onopen = () => {
          setWsConnected(true)
          reconnectAttempt = 0
          console.log('[Pipeline WS] Connected')
        }

        ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data)

            if (message.type === 'pipeline_update') {
              // Invalidate and refetch pipeline data
              queryClient.invalidateQueries({ queryKey: ['pipeline-status'] })
              setLastUpdate(new Date())

              // Show toast for significant updates
              if (message.event === 'rfp_moved') {
                toast.info(`RFP moved to ${message.rfp?.current_stage || 'new stage'}`)
              } else if (message.event === 'rfp_added') {
                toast.info('New RFP added to pipeline')
              }
            } else if (message.type === 'rfp_update') {
              // Also handle rfp_update messages
              queryClient.invalidateQueries({ queryKey: ['pipeline-status'] })
              setLastUpdate(new Date())
            }
          } catch (e) {
            console.warn('[Pipeline WS] Failed to parse message:', e)
          }
        }

        ws.onclose = (event) => {
          setWsConnected(false)
          console.log('[Pipeline WS] Disconnected:', event.code, event.reason)

          // Attempt to reconnect with exponential backoff
          if (reconnectAttempt < maxReconnectAttempts) {
            const delay = Math.min(1000 * Math.pow(2, reconnectAttempt), 30000)
            reconnectTimeout = setTimeout(() => {
              reconnectAttempt++
              connect()
            }, delay)
          }
        }

        ws.onerror = (error) => {
          console.error('[Pipeline WS] Error:', error)
        }
      } catch (e) {
        console.error('[Pipeline WS] Connection failed:', e)
      }
    }

    connect()

    return () => {
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout)
      }
      if (ws) {
        ws.close()
      }
    }
  }, [queryClient])

  // Manual refresh handler
  const handleRefresh = useCallback(async () => {
    try {
      // Clear cache and force fresh fetch
      await api.clearPipelineCache()
      await refetch()
      toast.success('Pipeline refreshed')
    } catch (e) {
      toast.error('Failed to refresh pipeline')
    }
  }, [refetch])

  // Computed stage info with counts
  const stageInfo: StageInfo[] = useMemo(() => {
    const stages = pipelineStatus?.stages || {}
    return STAGE_CONFIG.map(stage => ({
      ...stage,
      count: stages[stage.key] || 0
    }))
  }, [pipelineStatus?.stages])

  // Total RFP count
  const totalCount = pipelineStatus?.total_count || 0

  // Format last update time
  const lastUpdateText = useMemo(() => {
    if (!lastUpdate && !pipelineStatus?.timestamp) return null
    const timestamp = lastUpdate || (pipelineStatus?.timestamp ? new Date(pipelineStatus.timestamp) : null)
    if (!timestamp) return null

    const now = new Date()
    const diffMs = now.getTime() - timestamp.getTime()
    const diffSecs = Math.floor(diffMs / 1000)

    if (diffSecs < 60) return 'Just now'
    if (diffSecs < 3600) return `${Math.floor(diffSecs / 60)}m ago`
    return timestamp.toLocaleTimeString()
  }, [lastUpdate, pipelineStatus?.timestamp])

  // Handle timeout error specially
  const isTimeoutError = error?.message?.includes('timed out')

  // Show skeleton on initial load
  if (isLoading && !pipelineStatus) {
    return (
      <div className="space-y-6">
        <PipelineFullSkeleton />
      </div>
    )
  }

  return (
    <PipelineErrorBoundary onRetry={handleRefresh}>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
              Pipeline Monitor
            </h2>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              Real-time view of RFPs moving through the pipeline
            </p>
          </div>

          <div className="flex items-center gap-3">
            {/* WebSocket status */}
            <div className="flex items-center gap-2 text-sm text-gray-500">
              {wsConnected ? (
                <>
                  <Wifi className="h-4 w-4 text-green-500" />
                  <span className="hidden sm:inline">Live</span>
                </>
              ) : (
                <>
                  <WifiOff className="h-4 w-4 text-gray-400" />
                  <span className="hidden sm:inline">Offline</span>
                </>
              )}
            </div>

            {/* Last update time */}
            {lastUpdateText && (
              <div className="flex items-center gap-1 text-sm text-gray-500">
                <Clock className="h-4 w-4" />
                <span className="hidden sm:inline">{lastUpdateText}</span>
              </div>
            )}

            {/* Cache indicator */}
            {pipelineStatus?.cached && (
              <span className="text-xs px-2 py-1 bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-200 rounded">
                {pipelineStatus.stale ? 'Stale' : 'Cached'}
              </span>
            )}

            {/* Refresh button */}
            <Button
              onClick={handleRefresh}
              variant="outline"
              size="sm"
              disabled={isFetching}
              className="gap-2"
            >
              <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
              <span className="hidden sm:inline">Refresh</span>
            </Button>
          </div>
        </div>

        {/* Error state */}
        {isError && !pipelineStatus && (
          <PipelineError
            error={error}
            isTimeout={isTimeoutError}
            onRetry={handleRefresh}
          />
        )}

        {/* Warning banner for stale data */}
        {isError && pipelineStatus && (
          <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 flex items-center gap-3">
            <AlertCircle className="h-5 w-5 text-yellow-600 dark:text-yellow-400 flex-shrink-0" />
            <div className="flex-1">
              <p className="text-sm text-yellow-800 dark:text-yellow-200">
                Failed to fetch latest data. Showing cached results.
              </p>
              <p className="text-xs text-yellow-600 dark:text-yellow-400 mt-1">
                {error?.message}
              </p>
            </div>
            <Button
              onClick={handleRefresh}
              variant="outline"
              size="sm"
              className="flex-shrink-0"
            >
              Retry
            </Button>
          </div>
        )}

        {/* Stage summary cards */}
        {pipelineStatus && (
          <>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
              {stageInfo.map((stage) => (
                <div
                  key={stage.key}
                  className={`bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border-l-4 border-${stage.color}-500`}
                >
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {stage.label}
                  </p>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {stage.count}
                  </p>
                </div>
              ))}
            </div>

            {/* Total count */}
            <div className="flex items-center justify-between text-sm text-gray-500">
              <span>
                Total: <strong>{totalCount}</strong> RFPs in pipeline
              </span>
              {isFetching && !isLoading && (
                <span className="flex items-center gap-2">
                  <RefreshCw className="h-3 w-3 animate-spin" />
                  Updating...
                </span>
              )}
            </div>

            {/* Kanban board */}
            {pipelineStatus.rfps.length > 0 ? (
              <PipelineKanban rfps={pipelineStatus.rfps} />
            ) : (
              <PipelineEmpty onRefresh={handleRefresh} />
            )}
          </>
        )}

        {/* Loading overlay for refetch */}
        {isFetching && !isLoading && pipelineStatus && (
          <div className="fixed bottom-4 right-4 bg-blue-500 text-white px-4 py-2 rounded-lg shadow-lg flex items-center gap-2">
            <RefreshCw className="h-4 w-4 animate-spin" />
            <span className="text-sm">Updating pipeline...</span>
          </div>
        )}
      </div>
    </PipelineErrorBoundary>
  )
}
