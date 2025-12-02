/**
 * Error boundary and error display components for Pipeline Monitor.
 */
import { Component, ReactNode } from 'react'
import { AlertTriangle, RefreshCw, WifiOff } from 'lucide-react'
import { Button } from './ui/button'

interface Props {
  children: ReactNode
  onRetry?: () => void
}

interface State {
  hasError: boolean
  error: Error | null
}

export class PipelineErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Pipeline error:', error, errorInfo)
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null })
    this.props.onRetry?.()
  }

  render() {
    if (this.state.hasError) {
      return (
        <PipelineError
          error={this.state.error}
          onRetry={this.handleRetry}
        />
      )
    }

    return this.props.children
  }
}

interface PipelineErrorProps {
  error?: Error | null
  title?: string
  message?: string
  onRetry?: () => void
  isTimeout?: boolean
}

export function PipelineError({
  error,
  title,
  message,
  onRetry,
  isTimeout = false
}: PipelineErrorProps) {
  const errorMessage = message || error?.message || 'An unexpected error occurred'
  const errorTitle = title || (isTimeout ? 'Request Timed Out' : 'Pipeline Load Failed')

  const Icon = isTimeout ? WifiOff : AlertTriangle

  return (
    <div className="flex flex-col items-center justify-center py-12 px-4">
      <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-8 max-w-md w-full text-center">
        <Icon className="h-12 w-12 text-red-500 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-red-800 dark:text-red-200 mb-2">
          {errorTitle}
        </h3>
        <p className="text-sm text-red-600 dark:text-red-300 mb-4">
          {errorMessage}
        </p>
        {isTimeout && (
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">
            The server took too long to respond. This might be due to a large dataset or slow connection.
          </p>
        )}
        {onRetry && (
          <Button
            onClick={onRetry}
            variant="outline"
            className="gap-2"
          >
            <RefreshCw className="h-4 w-4" />
            Try Again
          </Button>
        )}
      </div>
    </div>
  )
}

interface PipelineEmptyProps {
  onRefresh?: () => void
}

export function PipelineEmpty({ onRefresh }: PipelineEmptyProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4">
      <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-8 max-w-md w-full text-center">
        <div className="h-12 w-12 bg-gray-200 dark:bg-gray-700 rounded-full mx-auto mb-4 flex items-center justify-center">
          <span className="text-2xl">📋</span>
        </div>
        <h3 className="text-lg font-semibold text-gray-700 dark:text-gray-200 mb-2">
          No RFPs in Pipeline
        </h3>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
          Discover new RFPs or import existing ones to see them appear in the pipeline.
        </p>
        {onRefresh && (
          <Button
            onClick={onRefresh}
            variant="outline"
            className="gap-2"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </Button>
        )}
      </div>
    </div>
  )
}
