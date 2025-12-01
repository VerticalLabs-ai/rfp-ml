import * as React from 'react'
import { useCallback, useState } from 'react'
import { useStreaming, StreamEvent } from './useStreaming'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  citations?: Array<{
    index: number
    content: string
    similarity: number
  }>
  isStreaming?: boolean
}

export interface UseStreamingChatOptions {
  /**
   * RFP ID for context
   */
  rfpId: string
  /**
   * Initial messages to load
   */
  initialMessages?: ChatMessage[]
  /**
   * Callback when a complete response is received
   */
  onResponse?: (message: ChatMessage) => void
  /**
   * Callback on error
   */
  onError?: (error: string) => void
}

/**
 * Hook for streaming chat with an RFP using the streaming API.
 *
 * Manages:
 * - Message history
 * - Streaming state for current response
 * - Citations from RAG
 * - Keyboard shortcuts (Enter to send)
 *
 * @example
 * ```tsx
 * const { messages, sendMessage, isStreaming, currentResponse } = useStreamingChat({
 *   rfpId: 'abc123',
 * })
 *
 * // Send a message
 * await sendMessage('What are the key requirements?')
 *
 * // Render messages
 * {messages.map(msg => (
 *   <Message key={msg.id} role={msg.role}>
 *     {msg.isStreaming ? (
 *       <StreamingText content={currentResponse} isStreaming />
 *     ) : msg.content}
 *   </Message>
 * ))}
 * ```
 */
export function useStreamingChat(options: UseStreamingChatOptions) {
  const { rfpId, initialMessages = [], onResponse, onError } = options

  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages)
  const [currentResponse, setCurrentResponse] = useState('')
  const [currentCitations, setCurrentCitations] = useState<ChatMessage['citations']>([])

  // Build the streaming URL
  const getStreamUrl = useCallback(
    (message: string) => {
      const encodedMessage = encodeURIComponent(message)
      const history = messages.slice(-10).map((m) => ({
        role: m.role,
        content: m.content,
      }))
      const encodedHistory = encodeURIComponent(JSON.stringify(history))
      return `/api/v1/streaming/${rfpId}/chat?message=${encodedMessage}&history=${encodedHistory}`
    },
    [rfpId, messages]
  )

  const handleEvent = useCallback((event: StreamEvent) => {
    if (event.type === 'citations' && event.data.citations) {
      setCurrentCitations(event.data.citations)
    }
  }, [])

  const handleText = useCallback((chunk: string) => {
    setCurrentResponse((prev) => prev + chunk)
  }, [])

  const handleComplete = useCallback(
    (content: string) => {
      // Create the complete assistant message
      const assistantMessage: ChatMessage = {
        id: `msg-${Date.now()}-assistant`,
        role: 'assistant',
        content,
        timestamp: new Date(),
        citations: currentCitations,
        isStreaming: false,
      }

      // Update the last message (which was streaming) to final state
      setMessages((prev) => {
        const lastMsg = prev[prev.length - 1]
        if (lastMsg?.role === 'assistant' && lastMsg.isStreaming) {
          return [...prev.slice(0, -1), assistantMessage]
        }
        return [...prev, assistantMessage]
      })

      setCurrentResponse('')
      setCurrentCitations([])
      onResponse?.(assistantMessage)
    },
    [currentCitations, onResponse]
  )

  const handleError = useCallback(
    (error: string) => {
      // Remove the streaming message on error
      setMessages((prev) => {
        const lastMsg = prev[prev.length - 1]
        if (lastMsg?.role === 'assistant' && lastMsg.isStreaming) {
          return prev.slice(0, -1)
        }
        return prev
      })
      setCurrentResponse('')
      setCurrentCitations([])
      onError?.(error)
    },
    [onError]
  )

  // URL ref to avoid race condition with state updates
  const streamUrlRef = React.useRef('')

  const streaming = useStreaming({
    url: streamUrlRef.current,
    onEvent: handleEvent,
    onText: handleText,
    onComplete: handleComplete,
    onError: handleError,
  })

  /**
   * Send a message and start streaming the response.
   */
  const sendMessage = useCallback(
    async (message: string) => {
      if (!message.trim() || streaming.isStreaming) {
        return
      }

      // Add user message
      const userMessage: ChatMessage = {
        id: `msg-${Date.now()}-user`,
        role: 'user',
        content: message.trim(),
        timestamp: new Date(),
      }

      // Add placeholder for assistant response
      const assistantPlaceholder: ChatMessage = {
        id: `msg-${Date.now()}-assistant`,
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        isStreaming: true,
      }

      setMessages((prev) => [...prev, userMessage, assistantPlaceholder])
      setCurrentResponse('')
      setCurrentCitations([])

      // Build URL and start streaming directly to avoid race condition
      const url = getStreamUrl(message.trim())
      streamUrlRef.current = url

      // Start streaming with URL as parameter to ensure correct URL is used
      await streaming.startStreaming()
    },
    [streaming, getStreamUrl]
  )

  /**
   * Stop the current streaming response.
   */
  const stopStreaming = useCallback(() => {
    streaming.stopStreaming()

    // Update the streaming message to show partial content
    if (currentResponse) {
      setMessages((prev) => {
        const lastMsg = prev[prev.length - 1]
        if (lastMsg?.role === 'assistant' && lastMsg.isStreaming) {
          return [
            ...prev.slice(0, -1),
            {
              ...lastMsg,
              content: currentResponse + ' [stopped]',
              isStreaming: false,
            },
          ]
        }
        return prev
      })
    }
    setCurrentResponse('')
  }, [streaming, currentResponse])

  /**
   * Clear all messages.
   */
  const clearMessages = useCallback(() => {
    streaming.reset()
    setMessages([])
    setCurrentResponse('')
    setCurrentCitations([])
  }, [streaming])

  /**
   * Get suggested questions for the RFP.
   */
  const suggestedQuestions = [
    'What are the key requirements for this RFP?',
    'What is the submission deadline?',
    'What certifications are required?',
    'What is the expected contract value?',
    'Are there any set-aside requirements?',
  ]

  return {
    messages,
    sendMessage,
    stopStreaming,
    clearMessages,
    isStreaming: streaming.isStreaming,
    currentResponse,
    currentCitations,
    error: streaming.error,
    suggestedQuestions,
  }
}
