import * as React from 'react'
import { Check, Loader2, X } from 'lucide-react'

import { Button, ButtonProps } from '@/components/ui/button'
import { cn } from '@/lib/utils'

export type AsyncButtonState = 'idle' | 'loading' | 'success' | 'error'

export interface AsyncButtonProps extends Omit<ButtonProps, 'onClick'> {
  /**
   * Async click handler. Button state managed automatically based on promise resolution.
   */
  onAsyncClick?: () => Promise<void>
  /**
   * Regular click handler (for non-async operations)
   */
  onClick?: () => void
  /**
   * Text to show while loading
   */
  loadingText?: string
  /**
   * Text to show on success (briefly)
   */
  successText?: string
  /**
   * Text to show on error (briefly)
   */
  errorText?: string
  /**
   * Duration to show success state (ms)
   */
  successDuration?: number
  /**
   * Duration to show error state (ms)
   */
  errorDuration?: number
  /**
   * External loading state override
   */
  isLoading?: boolean
  /**
   * Show icon indicators for states
   */
  showStateIcons?: boolean
}

/**
 * Button with automatic async state management.
 *
 * Features:
 * - Automatic loading → success/error state transitions
 * - Visual feedback with icons
 * - Customizable state durations
 * - Works with both async and sync handlers
 *
 * @example
 * ```tsx
 * <AsyncButton
 *   onAsyncClick={async () => {
 *     await api.saveDocument()
 *   }}
 *   loadingText="Saving..."
 *   successText="Saved!"
 * >
 *   Save Document
 * </AsyncButton>
 * ```
 */
const AsyncButton = React.forwardRef<HTMLButtonElement, AsyncButtonProps>(
  (
    {
      className,
      children,
      disabled,
      onAsyncClick,
      onClick,
      loadingText,
      successText,
      errorText,
      successDuration = 2000,
      errorDuration = 3000,
      isLoading: externalLoading,
      showStateIcons = true,
      ...props
    },
    ref
  ) => {
    const [state, setState] = React.useState<AsyncButtonState>('idle')
    const timeoutRef = React.useRef<ReturnType<typeof setTimeout>>()

    // Clean up timeout on unmount
    React.useEffect(() => {
      return () => {
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current)
        }
      }
    }, [])

    const handleClick = async () => {
      // Handle regular click
      if (onClick && !onAsyncClick) {
        onClick()
        return
      }

      // Handle async click
      if (onAsyncClick) {
        setState('loading')

        try {
          await onAsyncClick()
          setState('success')

          // Reset to idle after success
          timeoutRef.current = setTimeout(() => {
            setState('idle')
          }, successDuration)
        } catch (error) {
          console.error('AsyncButton error:', error)
          setState('error')

          // Reset to idle after error
          timeoutRef.current = setTimeout(() => {
            setState('idle')
          }, errorDuration)
        }
      }
    }

    // Determine effective loading state
    const isLoading = externalLoading || state === 'loading'
    const isSuccess = state === 'success'
    const isError = state === 'error'

    // Determine content
    let content = children
    if (isLoading && loadingText) {
      content = loadingText
    } else if (isSuccess && successText) {
      content = successText
    } else if (isError && errorText) {
      content = errorText
    }

    // Determine icon
    let icon = null
    if (showStateIcons) {
      if (isLoading) {
        icon = <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
      } else if (isSuccess) {
        icon = <Check className="mr-2 h-4 w-4 text-green-500" aria-hidden="true" />
      } else if (isError) {
        icon = <X className="mr-2 h-4 w-4 text-red-500" aria-hidden="true" />
      }
    }

    return (
      <Button
        className={cn(
          isSuccess && 'border-green-500/50',
          isError && 'border-red-500/50',
          className
        )}
        disabled={disabled || isLoading}
        onClick={handleClick}
        ref={ref}
        {...props}
      >
        {icon}
        {content}
      </Button>
    )
  }
)
AsyncButton.displayName = 'AsyncButton'

export { AsyncButton }
