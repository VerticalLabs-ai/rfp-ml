import * as React from "react"
import { Loader2 } from "lucide-react"

import { Button, ButtonProps } from "@/components/ui/button"
import { cn } from "@/lib/utils"

export interface LoadingButtonProps extends ButtonProps {
  loading?: boolean
  loadingText?: string
}

/**
 * Button with built-in loading state.
 *
 * Replaces the pattern of:
 *   <Button disabled={isLoading}>
 *     {isLoading && <Loader2 className="animate-spin" />}
 *     {isLoading ? "Loading..." : "Submit"}
 *   </Button>
 *
 * With:
 *   <LoadingButton loading={isLoading} loadingText="Submitting...">
 *     Submit
 *   </LoadingButton>
 */
const LoadingButton = React.forwardRef<HTMLButtonElement, LoadingButtonProps>(
  ({ className, children, disabled, loading, loadingText, ...props }, ref) => {
    return (
      <Button
        className={cn(className)}
        disabled={disabled || loading}
        ref={ref}
        {...props}
      >
        {loading && (
          <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
        )}
        {loading && loadingText ? loadingText : children}
      </Button>
    )
  }
)
LoadingButton.displayName = "LoadingButton"

export { LoadingButton }
