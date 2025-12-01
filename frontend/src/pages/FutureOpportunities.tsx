
import { useQuery } from '@tanstack/react-query'
import { api } from '../services/api'
import { Calendar, TrendingUp, AlertCircle, BarChart3 } from 'lucide-react'

export function FutureOpportunities() {
  const { data: predictions, isLoading, error, isError } = useQuery({
    queryKey: ['predictions'],
    queryFn: () => api.getPredictions(0.5), // Get all above 50% confidence
    retry: 1, // Only retry once
    staleTime: 5 * 60 * 1000, // 5 minutes
  })

  if (isLoading) {
    return (
      <div className="p-8 text-center">
        <div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-4"></div>
        <p className="text-slate-500">Analyzing historical data patterns...</p>
        <p className="text-xs text-slate-400 mt-2">This may take a moment on first load...</p>
      </div>
    )
  }

  if (isError || error) {
    // Check if it's a "no data" error vs a real error
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
                AI-forecasted recurring contracts expected in the next 12 months.
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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <TrendingUp className="h-6 w-6 text-blue-500" />
            Future Opportunities
          </h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1">
            AI-forecasted recurring contracts expected in the next 12 months.
          </p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {predictions?.map((pred: any, idx: number) => (
          <div 
            key={idx}
            className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 shadow-sm hover:shadow-md transition-shadow"
          >
            <div className="flex justify-between items-start mb-3">
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                {Math.round(pred.confidence * 100)}% Confidence
              </span>
              <span className="text-xs text-slate-500">{pred.agency}</span>
            </div>
            
            <h3 className="font-semibold text-lg text-slate-900 dark:text-white mb-2 line-clamp-2" title={pred.predicted_title}>
              {pred.predicted_title}
            </h3>
            
            <div className="flex items-center gap-2 text-slate-600 dark:text-slate-300 text-sm mb-4">
              <Calendar className="h-4 w-4" />
              <span>Est. Release: {pred.predicted_date}</span>
            </div>
            
            <div className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-3 text-xs text-slate-500 dark:text-slate-400">
              <p className="font-medium mb-1">Prediction Basis:</p>
              {pred.basis}
            </div>
          </div>
        ))}

        {predictions?.length === 0 && (
          <div className="col-span-full text-center py-12 bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-dashed border-slate-300">
            <p className="text-slate-500">No high-confidence recurring opportunities identified yet.</p>
          </div>
        )}
      </div>
    </div>
  )
}
