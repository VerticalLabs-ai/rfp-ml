import { useCallback, useRef, useState } from 'react'

/**
 * SSE Event types from the streaming API
 */
export type StreamEventType =
  | 'start'
  | 'thinking_start'
  | 'thinking'
  | 'text_start'
  | 'text'
  | 'block_stop'
  | 'usage'
  | 'complete'
  | 'error'
  | 'citations'

export interface StreamEvent {
  type: StreamEventType
  data: any
}

export interface StreamingState {
  isStreaming: boolean
  content: string
  thinking: string
  error: string | null
  citations: Array<{
    index: number
    content: string
    similarity: number
  }>
  usage: {
    inputTokens: number
    outputTokens: number
  }
}

export interface UseStreamingOptions {
  /**
   * Base URL for streaming endpoint (without query params)
   */
  url: string
  /**
   * Callback fired for each SSE event
   */
  onEvent?: (event: StreamEvent) => void
  /**
   * Callback fired when streaming completes successfully
   */
  onComplete?: (content: string) => void
  /**
   * Callback fired on error
   */
  onError?: (error: string) => void
  /**
   * Callback for text content chunks
   */
  onText?: (chunk: string) => void
  /**
   * Callback for thinking content chunks (if enabled)
   */
  onThinking?: (chunk: string) => void
}

/**
 * Hook for consuming Server-Sent Events (SSE) from the streaming API.
 *
 * Handles:
 * - Connection management with AbortController
 * - SSE event parsing
 * - Content accumulation
 * - Thinking content (for Claude thinking mode)
 * - Error handling
 *
 * @example
 * ```tsx
 * const { startStreaming, stopStreaming, state } = useStreaming({
 *   url: `/api/v1/streaming/${rfpId}/generate/executive_summary`,
 *   onComplete: (content) => console.log('Generated:', content),
 * })
 *
 * // Start streaming
 * await startStreaming({ use_thinking: true })
 *
 * // Show content
 * <StreamingText content={state.content} isStreaming={state.isStreaming} />
 * ```
 */
export function useStreaming(options: UseStreamingOptions) {
  const { url, onEvent, onComplete, onError, onText, onThinking } = options

  const [state, setState] = useState<StreamingState>({
    isStreaming: false,
    content: '',
    thinking: '',
    error: null,
    citations: [],
    usage: { inputTokens: 0, outputTokens: 0 },
  })

  const abortControllerRef = useRef<AbortController | null>(null)

  /**
   * Start streaming from the SSE endpoint.
   * @param params Optional query parameters to append to URL
   */
  const startStreaming = useCallback(
    async (params?: Record<string, string | number | boolean>) => {
      // Abort any existing stream
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }

      // Reset state
      setState({
        isStreaming: true,
        content: '',
        thinking: '',
        error: null,
        citations: [],
        usage: { inputTokens: 0, outputTokens: 0 },
      })

      // Build URL with params
      let streamUrl = url
      if (params) {
        const searchParams = new URLSearchParams()
        Object.entries(params).forEach(([key, value]) => {
          searchParams.set(key, String(value))
        })
        streamUrl = `${url}${url.includes('?') ? '&' : '?'}${searchParams.toString()}`
      }

      // Create abort controller
      abortControllerRef.current = new AbortController()

      try {
        const response = await fetch(streamUrl, {
          method: 'GET',
          headers: {
            Accept: 'text/event-stream',
          },
          signal: abortControllerRef.current.signal,
        })

        if (!response.ok) {
          const errorText = await response.text()
          throw new Error(`HTTP ${response.status}: ${errorText}`)
        }

        const reader = response.body?.getReader()
        if (!reader) {
          throw new Error('Response body is not readable')
        }

        const decoder = new TextDecoder()
        let buffer = ''
        let accumulatedContent = ''
        let accumulatedThinking = ''

        while (true) {
          const { done, value } = await reader.read()

          if (done) {
            break
          }

          buffer += decoder.decode(value, { stream: true })

          // Parse SSE events from buffer
          const lines = buffer.split('\n')
          buffer = lines.pop() || '' // Keep incomplete line in buffer

          let currentEventType: StreamEventType | null = null

          for (const line of lines) {
            if (line.startsWith('event: ')) {
              currentEventType = line.slice(7).trim() as StreamEventType
            } else if (line.startsWith('data: ') && currentEventType) {
              try {
                const data = JSON.parse(line.slice(6))
                const event: StreamEvent = { type: currentEventType, data }

                // Call event callback
                onEvent?.(event)

                // Handle different event types
                switch (currentEventType) {
                  case 'text':
                    if (data.content) {
                      accumulatedContent += data.content
                      setState((prev) => ({
                        ...prev,
                        content: accumulatedContent,
                      }))
                      onText?.(data.content)
                    }
                    break

                  case 'thinking':
                    if (data.content) {
                      accumulatedThinking += data.content
                      setState((prev) => ({
                        ...prev,
                        thinking: accumulatedThinking,
                      }))
                      onThinking?.(data.content)
                    }
                    break

                  case 'citations':
                    if (data.citations) {
                      setState((prev) => ({
                        ...prev,
                        citations: data.citations,
                      }))
                    }
                    break

                  case 'usage':
                    setState((prev) => ({
                      ...prev,
                      usage: {
                        inputTokens: data.input_tokens ?? prev.usage.inputTokens,
                        outputTokens: data.output_tokens ?? prev.usage.outputTokens,
                      },
                    }))
                    break

                  case 'error':
                    const errorMsg = data.error || 'Unknown error'
                    setState((prev) => ({
                      ...prev,
                      error: errorMsg,
                      isStreaming: false,
                    }))
                    onError?.(errorMsg)
                    break

                  case 'complete':
                    setState((prev) => ({
                      ...prev,
                      isStreaming: false,
                    }))
                    onComplete?.(accumulatedContent)
                    break
                }

                currentEventType = null
              } catch (parseError) {
                console.warn('Failed to parse SSE data:', line, parseError)
              }
            }
          }
        }

        // Stream ended naturally
        setState((prev) => ({ ...prev, isStreaming: false }))
        if (state.isStreaming && !state.error) {
          onComplete?.(accumulatedContent)
        }
      } catch (error) {
        if ((error as Error).name === 'AbortError') {
          // Intentional abort, not an error
          setState((prev) => ({ ...prev, isStreaming: false }))
          return
        }

        const errorMsg = (error as Error).message || 'Streaming failed'
        setState((prev) => ({
          ...prev,
          error: errorMsg,
          isStreaming: false,
        }))
        onError?.(errorMsg)
      }
    },
    [url, onEvent, onComplete, onError, onText, onThinking]
  )

  /**
   * Stop the current stream.
   */
  const stopStreaming = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    setState((prev) => ({ ...prev, isStreaming: false }))
  }, [])

  /**
   * Reset state to initial values.
   */
  const reset = useCallback(() => {
    stopStreaming()
    setState({
      isStreaming: false,
      content: '',
      thinking: '',
      error: null,
      citations: [],
      usage: { inputTokens: 0, outputTokens: 0 },
    })
  }, [stopStreaming])

  return {
    startStreaming,
    stopStreaming,
    reset,
    state,
    // Convenience accessors
    isStreaming: state.isStreaming,
    content: state.content,
    thinking: state.thinking,
    error: state.error,
    citations: state.citations,
    usage: state.usage,
  }
}
