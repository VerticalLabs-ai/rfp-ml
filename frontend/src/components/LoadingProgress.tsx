import { CheckCircle2, Loader2, AlertCircle } from 'lucide-react'
import { cn } from '@/lib/utils'

export type LoadingStatus = 'pending' | 'loading' | 'success' | 'error' | 'timeout'

interface LoadingItem {
  id: string
  label: string
  status: LoadingStatus
}

interface LoadingProgressProps {
  items: LoadingItem[]
  className?: string
}

export function LoadingProgress({ items, className }: LoadingProgressProps) {
  const completedCount = items.filter(item => item.status === 'success').length
  const totalCount = items.length
  const hasError = items.some(item => item.status === 'error' || item.status === 'timeout')
  const isComplete = completedCount === totalCount

  const progressPercent = (completedCount / totalCount) * 100

  return (
    <div className={cn("space-y-4", className)}>
      {/* Progress bar */}
      <div className="relative">
        <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
          <div
            className={cn(
              "h-full transition-all duration-500 ease-out",
              hasError ? "bg-yellow-500" : isComplete ? "bg-green-500" : "bg-blue-500"
            )}
            style={{ width: `${progressPercent}%` }}
          />
        </div>
        <div className="mt-1 text-xs text-gray-500 dark:text-gray-400 text-right">
          {completedCount} / {totalCount} loaded
        </div>
      </div>

      {/* Individual items */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
        {items.map((item) => (
          <div
            key={item.id}
            className={cn(
              "flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors",
              item.status === 'success' && "bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400",
              item.status === 'loading' && "bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400",
              item.status === 'pending' && "bg-gray-50 dark:bg-gray-800 text-gray-500 dark:text-gray-400",
              (item.status === 'error' || item.status === 'timeout') && "bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400"
            )}
          >
            {item.status === 'success' && <CheckCircle2 className="h-4 w-4 flex-shrink-0" />}
            {item.status === 'loading' && <Loader2 className="h-4 w-4 flex-shrink-0 animate-spin" />}
            {item.status === 'pending' && <div className="h-4 w-4 flex-shrink-0 rounded-full border-2 border-current opacity-30" />}
            {(item.status === 'error' || item.status === 'timeout') && <AlertCircle className="h-4 w-4 flex-shrink-0" />}
            <span className="truncate">{item.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
