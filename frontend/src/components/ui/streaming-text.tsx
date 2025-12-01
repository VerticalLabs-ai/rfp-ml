import * as React from 'react'

import { cn } from '@/lib/utils'

export interface StreamingTextProps extends React.HTMLAttributes<HTMLDivElement> {
  /**
   * The text content to display
   */
  content: string
  /**
   * Whether the text is currently streaming
   */
  isStreaming?: boolean
  /**
   * Custom class for the cursor element
   */
  cursorClassName?: string
  /**
   * Whether to show the blinking cursor when streaming
   */
  showCursor?: boolean
  /**
   * Render content as markdown-like blocks (paragraphs)
   */
  asBlocks?: boolean
}

/**
 * Animated text component for displaying streaming LLM responses.
 *
 * Features:
 * - Blinking cursor animation while streaming
 * - Smooth text appearance
 * - Preserves whitespace and line breaks
 * - Optional paragraph block rendering
 *
 * @example
 * ```tsx
 * const { content, isStreaming } = useStreaming({ url: '...' })
 *
 * <StreamingText
 *   content={content}
 *   isStreaming={isStreaming}
 *   className="text-sm"
 * />
 * ```
 */
const StreamingText = React.forwardRef<HTMLDivElement, StreamingTextProps>(
  (
    {
      content,
      isStreaming = false,
      className,
      cursorClassName,
      showCursor = true,
      asBlocks = false,
      ...props
    },
    ref
  ) => {
    // If asBlocks, split by double newlines into paragraphs
    if (asBlocks && content) {
      const blocks = content.split(/\n\n+/).filter(Boolean)
      return (
        <div ref={ref} className={cn('space-y-4', className)} {...props}>
          {blocks.map((block, i) => (
            <p key={i} className="whitespace-pre-wrap">
              {block}
              {isStreaming && showCursor && i === blocks.length - 1 && <Cursor className={cursorClassName} />}
            </p>
          ))}
          {blocks.length === 0 && isStreaming && showCursor && <Cursor className={cursorClassName} />}
        </div>
      )
    }

    return (
      <div ref={ref} className={cn('whitespace-pre-wrap', className)} {...props}>
        {content}
        {isStreaming && showCursor && <Cursor className={cursorClassName} />}
      </div>
    )
  }
)
StreamingText.displayName = 'StreamingText'

/**
 * Blinking cursor component for streaming text
 */
function Cursor({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        'ml-0.5 inline-block h-4 w-2 animate-pulse bg-primary align-middle',
        className
      )}
      aria-hidden="true"
    />
  )
}

/**
 * Thinking indicator component for Claude's extended thinking mode
 */
export interface ThinkingIndicatorProps extends React.HTMLAttributes<HTMLDivElement> {
  /**
   * The thinking content (if visible)
   */
  thinking?: string
  /**
   * Whether thinking is in progress
   */
  isThinking?: boolean
  /**
   * Whether to show the thinking content (collapsed by default)
   */
  showContent?: boolean
}

const ThinkingIndicator = React.forwardRef<HTMLDivElement, ThinkingIndicatorProps>(
  ({ thinking, isThinking = false, showContent = false, className, ...props }, ref) => {
    const [expanded, setExpanded] = React.useState(showContent)

    if (!isThinking && !thinking) {
      return null
    }

    return (
      <div
        ref={ref}
        className={cn(
          'rounded-lg border border-muted bg-muted/30 p-3 text-sm',
          className
        )}
        {...props}
      >
        <button
          type="button"
          className="flex w-full items-center gap-2 text-left text-muted-foreground"
          onClick={() => setExpanded(!expanded)}
        >
          {isThinking ? (
            <>
              <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-primary" />
              <span>Thinking...</span>
            </>
          ) : (
            <>
              <span className="text-xs">💭</span>
              <span>Thought process</span>
            </>
          )}
          <span className="ml-auto text-xs">
            {expanded ? '▼' : '▶'}
          </span>
        </button>
        {expanded && thinking && (
          <div className="mt-2 max-h-40 overflow-y-auto text-xs text-muted-foreground">
            <StreamingText content={thinking} isStreaming={isThinking} />
          </div>
        )}
      </div>
    )
  }
)
ThinkingIndicator.displayName = 'ThinkingIndicator'

export { StreamingText, ThinkingIndicator, Cursor }
