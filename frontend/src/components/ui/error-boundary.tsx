import * as React from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'

export interface ErrorBoundaryProps {
  children: React.ReactNode
  /**
   * Custom fallback UI to render on error
   */
  fallback?: React.ReactNode
  /**
   * Callback when error occurs
   */
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void
  /**
   * Custom reset handler (defaults to resetting state)
   */
  onReset?: () => void
  /**
   * Class name for the fallback container
   */
  className?: string
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
  errorInfo: React.ErrorInfo | null
}

/**
 * Error boundary component that catches JavaScript errors in child components.
 *
 * Features:
 * - Catches render errors in child tree
 * - Displays friendly error UI
 * - Provides retry functionality
 * - Reports errors via callback
 *
 * @example
 * ```tsx
 * <ErrorBoundary
 *   onError={(error) => logToService(error)}
 *   fallback={<CustomErrorUI />}
 * >
 *   <ComponentThatMightError />
 * </ErrorBoundary>
 * ```
 */
class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    }
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    this.setState({ errorInfo })
    this.props.onError?.(error, errorInfo)
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    })
    this.props.onReset?.()
  }

  render() {
    const { hasError, error, errorInfo } = this.state
    const { children, fallback, className } = this.props

    if (hasError) {
      if (fallback) {
        return fallback
      }

      return (
        <Card className={cn('border-destructive/50', className)}>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-destructive">
              <AlertTriangle className="h-5 w-5" />
              Something went wrong
            </CardTitle>
            <CardDescription>
              An error occurred while rendering this component.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {error && (
              <div className="rounded-md bg-destructive/10 p-3 text-sm">
                <p className="font-medium text-destructive">{error.message}</p>
              </div>
            )}

            {process.env.NODE_ENV === 'development' && errorInfo && (
              <details className="text-xs">
                <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
                  Show stack trace
                </summary>
                <pre className="mt-2 max-h-40 overflow-auto rounded bg-muted p-2">
                  {errorInfo.componentStack}
                </pre>
              </details>
            )}

            <Button onClick={this.handleReset} variant="outline" size="sm">
              <RefreshCw className="mr-2 h-4 w-4" />
              Try again
            </Button>
          </CardContent>
        </Card>
      )
    }

    return children
  }
}

/**
 * HOC to wrap a component with an error boundary
 */
function withErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  errorBoundaryProps?: Omit<ErrorBoundaryProps, 'children'>
) {
  return function WrappedWithErrorBoundary(props: P) {
    return (
      <ErrorBoundary {...errorBoundaryProps}>
        <Component {...props} />
      </ErrorBoundary>
    )
  }
}

/**
 * Hook-style error boundary using a wrapper component
 * Note: This doesn't catch errors like a class component, but provides
 * a consistent API for error handling in functional components.
 */
function useErrorHandler() {
  const [error, setError] = React.useState<Error | null>(null)

  const resetError = React.useCallback(() => {
    setError(null)
  }, [])

  const handleError = React.useCallback((err: Error) => {
    setError(err)
  }, [])

  // Re-throw error to be caught by nearest ErrorBoundary
  if (error) {
    throw error
  }

  return { handleError, resetError }
}

export { ErrorBoundary, withErrorBoundary, useErrorHandler }
