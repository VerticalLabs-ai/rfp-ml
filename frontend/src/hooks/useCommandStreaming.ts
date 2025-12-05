/**
 * Hook for streaming slash command execution via POST request.
 */
import { useCallback, useRef, useState } from 'react'

interface CommandStreamingState {
  isStreaming: boolean
  content: string
  error: string | null
}

interface CommandStreamingOptions {
  url: string
  onComplete?: (content: string) => void
  onError?: (error: string) => void
}

interface CommandRequestBody {
  command: string
  selected_text: string
  context: string
  section_id: string
  custom_prompt?: string
}

export function useCommandStreaming(options: CommandStreamingOptions) {
  const { url, onComplete, onError } = options

  const [state, setState] = useState<CommandStreamingState>({
    isStreaming: false,
    content: '',
    error: null,
  })

  const abortControllerRef = useRef<AbortController | null>(null)

  const startStreaming = useCallback(
    async (body: CommandRequestBody) => {
      // Abort any existing stream
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }

      // Reset state
      setState({
        isStreaming: true,
        content: '',
        error: null,
      })

      // Create abort controller
      abortControllerRef.current = new AbortController()

      try {
        const response = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Accept: 'text/event-stream',
          },
          body: JSON.stringify(body),
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

        while (true) {
          const { done, value } = await reader.read()

          if (done) {
            break
          }

          buffer += decoder.decode(value, { stream: true })

          // Parse SSE events from buffer
          const lines = buffer.split('\n')
          buffer = lines.pop() || '' // Keep incomplete line in buffer

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6))

                if (data.type === 'content' && data.text) {
                  accumulatedContent += data.text
                  setState((prev) => ({
                    ...prev,
                    content: accumulatedContent,
                  }))
                } else if (data.type === 'error') {
                  const errorMsg = data.message || 'Unknown error'
                  setState((prev) => ({
                    ...prev,
                    error: errorMsg,
                    isStreaming: false,
                  }))
                  onError?.(errorMsg)
                  return
                } else if (data.type === 'done') {
                  setState((prev) => ({
                    ...prev,
                    isStreaming: false,
                  }))
                  onComplete?.(accumulatedContent)
                  return
                }
              } catch (parseError) {
                console.warn('Failed to parse SSE data:', line, parseError)
              }
            }
          }
        }

        // Stream ended naturally
        setState((prev) => ({ ...prev, isStreaming: false }))
        if (accumulatedContent) {
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
    [url, onComplete, onError]
  )

  const stopStreaming = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    setState((prev) => ({ ...prev, isStreaming: false }))
  }, [])

  const reset = useCallback(() => {
    stopStreaming()
    setState({
      isStreaming: false,
      content: '',
      error: null,
    })
  }, [stopStreaming])

  return {
    startStreaming,
    stopStreaming,
    reset,
    isStreaming: state.isStreaming,
    content: state.content,
    error: state.error,
  }
}
