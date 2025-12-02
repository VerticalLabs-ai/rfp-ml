import { useQuery } from '@tanstack/react-query'
import { api } from '../services/api'
import {
  Calendar,
  TrendingUp,
  AlertCircle,
  BarChart3,
  Sparkles,
  Clock,
  RefreshCw,
  RotateCcw,
  Loader2,
  DollarSign,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { apiClient } from '../services/api'

interface Prediction {
  predicted_title: string
  agency: string
  predicted_date: string
  confidence: number
  cycle_type?: string
  cycle_days?: number
  variance_days?: number
  num_observations?: number
  last_posted?: string
  days_until?: number
  naics_code?: string
  historical_value?: number
  basis: string
  ai_enhanced?: boolean
  ai_insight?: string
}

const cycleTypeColors: Record<string, string> = {
  quarterly: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  biannual: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200',
  annual: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  biennial: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-200',
  recurring: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  irregular: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
}

const getConfidenceColor = (confidence: number): string => {
  if (confidence >= 0.8) return 'bg-green-500'
  if (confidence >= 0.6) return 'bg-blue-500'
  if (confidence >= 0.4) return 'bg-yellow-500'
  return 'bg-orange-500'
}

const getConfidenceBadgeClass = (confidence: number): string => {
  if (confidence >= 0.8) return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
  if (confidence >= 0.6) return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
  if (confidence >= 0.4) return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
  return 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200'
}

const formatCurrency = (amount: number): string => {
  if (amount >= 1000000) return `$${(amount / 1000000).toFixed(1)}M`
  if (amount >= 1000) return `$${(amount / 1000).toFixed(0)}K`
  return `$${amount.toFixed(0)}`
}

export function FutureOpportunities() {
  const { data: predictions, isLoading, error, isError, refetch, isFetching } = useQuery({
    queryKey: ['predictions'],
    queryFn: () => api.getPredictions(0.3), // Get all above 30% confidence
    retry: 1,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })

  const handleRefresh = async () => {
    // Clear cache and refetch
    await apiClient.delete('/predictions/cache').catch(() => {})
    refetch()
  }

  if (isLoading) {
    return (
      <div className="p-8 text-center">
        <div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-4" />
        <p className="text-slate-500">Running AI-powered opportunity analysis...</p>
        <p className="text-xs text-slate-400 mt-2">Analyzing historical patterns and generating insights...</p>
      </div>
    )
  }

  if (isError || error) {
    const errorMessage = error instanceof Error ? error.message : String(error)
    const isNoData = errorMessage.includes('404') || errorMessage.includes('not found')

    if (isNoData) {
      return (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <TrendingUp className="h-6 w-6 text-blue-500" />
                Future Opportunities
              </h1>
              <p className="text-slate-500 dark:text-slate-400 mt-1">
                AI-powered forecasting of recurring government contracts
              </p>
            </div>
          </div>

          <div className="text-center py-16 bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-dashed border-slate-300">
            <BarChart3 className="mx-auto h-12 w-12 text-slate-400 mb-4" />
            <h3 className="text-lg font-medium text-slate-700 dark:text-slate-300 mb-2">No Historical Data Available</h3>
            <p className="text-slate-500 max-w-md mx-auto">
              Upload historical RFP data (FY2023 or FY2025 archived opportunities) to enable AI-powered opportunity forecasting.
            </p>
          </div>
        </div>
      )
    }

    return (
      <div className="p-8 text-center text-red-500">
        <AlertCircle className="mx-auto h-12 w-12 mb-2" />
        <p>Failed to load predictions. Please ensure historical data is available.</p>
        <p className="text-sm mt-2 text-slate-500">{errorMessage}</p>
      </div>
    )
  }

  const aiEnhancedCount = predictions?.filter((p: Prediction) => p.ai_enhanced).length || 0

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <TrendingUp className="h-6 w-6 text-blue-500" />
            Future Opportunities
          </h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1">
            AI-powered forecasting of recurring government contracts
          </p>
        </div>
        <div className="flex items-center gap-3">
          {aiEnhancedCount > 0 && (
            <Badge variant="secondary" className="gap-1">
              <Sparkles className="h-3 w-3" />
              {aiEnhancedCount} AI-analyzed
            </Badge>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={isFetching}
          >
            {isFetching ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4 mr-2" />
            )}
            Refresh Analysis
          </Button>
        </div>
      </div>

      {/* Stats summary */}
      {predictions && predictions.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white dark:bg-slate-800 rounded-lg border p-4">
            <div className="text-sm text-slate-500">Total Predictions</div>
            <div className="text-2xl font-bold">{predictions.length}</div>
          </div>
          <div className="bg-white dark:bg-slate-800 rounded-lg border p-4">
            <div className="text-sm text-slate-500">High Confidence (&gt;70%)</div>
            <div className="text-2xl font-bold text-green-600">
              {predictions.filter((p: Prediction) => p.confidence >= 0.7).length}
            </div>
          </div>
          <div className="bg-white dark:bg-slate-800 rounded-lg border p-4">
            <div className="text-sm text-slate-500">Next 30 Days</div>
            <div className="text-2xl font-bold text-blue-600">
              {predictions.filter((p: Prediction) => (p.days_until || 0) <= 30).length}
            </div>
          </div>
          <div className="bg-white dark:bg-slate-800 rounded-lg border p-4">
            <div className="text-sm text-slate-500">AI Enhanced</div>
            <div className="text-2xl font-bold text-purple-600">{aiEnhancedCount}</div>
          </div>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {predictions?.map((pred: Prediction, idx: number) => (
          <div
            key={idx}
            className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 shadow-sm hover:shadow-md transition-shadow"
          >
            {/* Header with badges */}
            <div className="flex flex-wrap gap-2 mb-3">
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getConfidenceBadgeClass(pred.confidence)}`}>
                {Math.round(pred.confidence * 100)}% Confidence
              </span>
              {pred.cycle_type && (
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize ${cycleTypeColors[pred.cycle_type] || cycleTypeColors.recurring}`}>
                  {pred.cycle_type}
                </span>
              )}
              {pred.ai_enhanced && (
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger>
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-violet-100 text-violet-800 dark:bg-violet-900 dark:text-violet-200">
                        <Sparkles className="h-3 w-3 mr-1" />
                        AI
                      </span>
                    </TooltipTrigger>
                    <TooltipContent>AI-generated insights available</TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              )}
            </div>

            {/* Confidence bar */}
            <div className="mb-3">
              <Progress
                value={pred.confidence * 100}
                className={`h-1.5 [&>div]:${getConfidenceColor(pred.confidence)}`}
              />
            </div>

            {/* Agency */}
            <div className="text-xs text-slate-500 mb-1">{pred.agency}</div>

            {/* Title */}
            <h3
              className="font-semibold text-lg text-slate-900 dark:text-white mb-3 line-clamp-2"
              title={pred.predicted_title}
            >
              {pred.predicted_title}
            </h3>

            {/* Key info */}
            <div className="space-y-2 mb-4">
              <div className="flex items-center gap-2 text-slate-600 dark:text-slate-300 text-sm">
                <Calendar className="h-4 w-4 flex-shrink-0" />
                <span>Est. Release: {pred.predicted_date}</span>
                {pred.days_until !== undefined && pred.days_until > 0 && (
                  <Badge variant="outline" className="ml-auto text-xs">
                    {pred.days_until} days
                  </Badge>
                )}
              </div>

              {pred.historical_value && (
                <div className="flex items-center gap-2 text-slate-600 dark:text-slate-300 text-sm">
                  <DollarSign className="h-4 w-4 flex-shrink-0" />
                  <span>Historical Value: {formatCurrency(pred.historical_value)}</span>
                </div>
              )}

              {pred.num_observations && (
                <div className="flex items-center gap-2 text-slate-600 dark:text-slate-300 text-sm">
                  <RotateCcw className="h-4 w-4 flex-shrink-0" />
                  <span>
                    {pred.num_observations} historical postings
                    {pred.variance_days !== undefined && ` (±${pred.variance_days}d variance)`}
                  </span>
                </div>
              )}

              {pred.last_posted && (
                <div className="flex items-center gap-2 text-slate-600 dark:text-slate-300 text-sm">
                  <Clock className="h-4 w-4 flex-shrink-0" />
                  <span>Last posted: {pred.last_posted}</span>
                </div>
              )}
            </div>

            {/* AI Insight */}
            {pred.ai_insight && (
              <div className="bg-violet-50 dark:bg-violet-900/30 border border-violet-200 dark:border-violet-800 rounded-lg p-3 mb-3">
                <div className="flex items-center gap-1 text-xs font-medium text-violet-700 dark:text-violet-300 mb-1">
                  <Sparkles className="h-3 w-3" />
                  AI Insight
                </div>
                <p className="text-xs text-violet-600 dark:text-violet-400">
                  {pred.ai_insight}
                </p>
              </div>
            )}

            {/* Basis */}
            <div className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-3 text-xs text-slate-500 dark:text-slate-400">
              <p className="font-medium mb-1">Prediction Basis:</p>
              {pred.basis}
            </div>
          </div>
        ))}

        {predictions?.length === 0 && (
          <div className="col-span-full text-center py-12 bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-dashed border-slate-300">
            <p className="text-slate-500">No recurring opportunities identified in historical data.</p>
            <p className="text-xs text-slate-400 mt-2">
              Try uploading more historical data or lowering the confidence threshold.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
