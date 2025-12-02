import { useEffect, useRef, useState, useCallback } from 'react'
import { toast } from 'sonner'

interface WebSocketMessage {
  type: string
  data: any
  timestamp?: string
}

interface QueuedMessage {
  message: any
  timestamp: number
}

export type ConnectionState = 'connecting' | 'connected' | 'disconnected' | 'reconnecting'

interface UseWebSocketOptions {
  url: string
  onMessage?: (message: WebSocketMessage) => void
  onError?: (error: Event) => void
  onConnect?: () => void
  onDisconnect?: (reason?: string) => void
  onStateChange?: (state: ConnectionState) => void
  maxReconnectAttempts?: number
  initialReconnectInterval?: number
  maxReconnectInterval?: number
  heartbeatInterval?: number
  messageQueueMaxSize?: number
  enablePersistence?: boolean
}

// Storage key for persisted state
const WS_STATE_KEY = 'ws_connection_state'
const WS_QUEUE_KEY = 'ws_message_queue'

interface PersistedState {
  lastConnectedUrl: string
  reconnectAttempt: number
  timestamp: number
}

function getPersistedState(): PersistedState | null {
  try {
    const stored = sessionStorage.getItem(WS_STATE_KEY)
    if (stored) {
      const state = JSON.parse(stored) as PersistedState
      // Only use state if less than 5 minutes old
      if (Date.now() - state.timestamp < 5 * 60 * 1000) {
        return state
      }
    }
  } catch (e) {
    console.warn('[WebSocket] Failed to read persisted state:', e)
  }
  return null
}

function persistState(state: PersistedState): void {
  try {
    sessionStorage.setItem(WS_STATE_KEY, JSON.stringify(state))
  } catch (e) {
    console.warn('[WebSocket] Failed to persist state:', e)
  }
}

function clearPersistedState(): void {
  try {
    sessionStorage.removeItem(WS_STATE_KEY)
  } catch (e) {
    // Ignore
  }
}

function getQueuedMessages(url: string): QueuedMessage[] {
  try {
    const stored = sessionStorage.getItem(`${WS_QUEUE_KEY}_${btoa(url)}`)
    if (stored) {
      return JSON.parse(stored) as QueuedMessage[]
    }
  } catch (e) {
    console.warn('[WebSocket] Failed to read queued messages:', e)
  }
  return []
}

function persistQueuedMessages(url: string, messages: QueuedMessage[]): void {
  try {
    sessionStorage.setItem(`${WS_QUEUE_KEY}_${btoa(url)}`, JSON.stringify(messages))
  } catch (e) {
    console.warn('[WebSocket] Failed to persist queued messages:', e)
  }
}

function clearQueuedMessages(url: string): void {
  try {
    sessionStorage.removeItem(`${WS_QUEUE_KEY}_${btoa(url)}`)
  } catch (e) {
    // Ignore
  }
}

export function useWebSocket({
  url,
  onMessage,
  onError,
  onConnect,
  onDisconnect,
  onStateChange,
  maxReconnectAttempts = Infinity,
  initialReconnectInterval = 1000,
  maxReconnectInterval = 30000,
  heartbeatInterval = 30000,
  messageQueueMaxSize = 100,
  enablePersistence = true
}: UseWebSocketOptions) {
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected')
  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null)
  const [reconnectAttempt, setReconnectAttempt] = useState(0)
  const [reconnectCountdown, setReconnectCountdown] = useState<number | null>(null)

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout>>()
  const countdownIntervalRef = useRef<ReturnType<typeof setInterval>>()
  const heartbeatIntervalRef = useRef<ReturnType<typeof setInterval>>()
  const heartbeatTimeoutRef = useRef<ReturnType<typeof setTimeout>>()
  const intentionalDisconnectRef = useRef(false)
  const hasConnectedOnceRef = useRef(false)
  const messageQueueRef = useRef<QueuedMessage[]>([])
  const reconnectAttemptRef = useRef(0)
  const lastPongRef = useRef<number>(Date.now())

  // Update connection state and notify
  const updateConnectionState = useCallback((state: ConnectionState) => {
    setConnectionState(state)
    setIsConnected(state === 'connected')
    onStateChange?.(state)
  }, [onStateChange])

  // Log disconnection with detailed reason
  const logDisconnection = useCallback((code: number, reason: string, wasClean: boolean) => {
    const codeDescriptions: Record<number, string> = {
      1000: 'Normal closure',
      1001: 'Going away (page navigation)',
      1002: 'Protocol error',
      1003: 'Unsupported data',
      1005: 'No status received',
      1006: 'Abnormal closure (connection lost)',
      1007: 'Invalid frame payload data',
      1008: 'Policy violation',
      1009: 'Message too big',
      1010: 'Missing extension',
      1011: 'Internal error',
      1012: 'Service restart',
      1013: 'Try again later',
      1014: 'Bad gateway',
      1015: 'TLS handshake failure'
    }

    const description = codeDescriptions[code] || 'Unknown reason'
    const details = {
      code,
      reason: reason || description,
      wasClean,
      timestamp: new Date().toISOString(),
      reconnectAttempt: reconnectAttemptRef.current,
      lastPong: new Date(lastPongRef.current).toISOString()
    }

    console.warn('[WebSocket] Disconnected:', details)

    // Log to console for debugging
    if (code === 1006) {
      console.error('[WebSocket] Connection lost unexpectedly. Possible causes:')
      console.error('  - Server closed connection')
      console.error('  - Network interruption')
      console.error('  - Firewall/proxy interference')
      console.error('  - Server overload or restart')
    }

    return details
  }, [])

  // Send heartbeat ping
  const sendHeartbeat = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      try {
        wsRef.current.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }))

        // Set timeout for pong response (10 seconds)
        heartbeatTimeoutRef.current = setTimeout(() => {
          const timeSinceLastPong = Date.now() - lastPongRef.current
          if (timeSinceLastPong > heartbeatInterval + 10000) {
            console.warn('[WebSocket] No pong received, connection may be stale. Reconnecting...')
            wsRef.current?.close(4000, 'Heartbeat timeout')
          }
        }, 10000)
      } catch (error) {
        console.warn('[WebSocket] Failed to send heartbeat:', error)
      }
    }
  }, [heartbeatInterval])

  // Start heartbeat monitoring
  const startHeartbeat = useCallback(() => {
    stopHeartbeat()
    lastPongRef.current = Date.now()
    heartbeatIntervalRef.current = setInterval(sendHeartbeat, heartbeatInterval)
  }, [sendHeartbeat, heartbeatInterval])

  // Stop heartbeat monitoring
  const stopHeartbeat = useCallback(() => {
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current)
      heartbeatIntervalRef.current = undefined
    }
    if (heartbeatTimeoutRef.current) {
      clearTimeout(heartbeatTimeoutRef.current)
      heartbeatTimeoutRef.current = undefined
    }
  }, [])

  // Replay queued messages
  const replayQueuedMessages = useCallback(() => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) return

    const queue = messageQueueRef.current
    if (queue.length === 0) return

    console.log(`[WebSocket] Replaying ${queue.length} queued messages`)

    const messagesToReplay = [...queue]
    messageQueueRef.current = []
    clearQueuedMessages(url)

    messagesToReplay.forEach(({ message, timestamp }) => {
      // Only replay messages less than 5 minutes old
      if (Date.now() - timestamp < 5 * 60 * 1000) {
        try {
          wsRef.current?.send(JSON.stringify(message))
        } catch (error) {
          console.warn('[WebSocket] Failed to replay message:', error)
        }
      }
    })
  }, [url])

  // Calculate reconnect delay with exponential backoff
  const getReconnectDelay = useCallback((attempt: number): number => {
    const delay = Math.min(
      initialReconnectInterval * Math.pow(2, attempt),
      maxReconnectInterval
    )
    // Add jitter (±20%) to prevent thundering herd
    const jitter = delay * 0.2 * (Math.random() - 0.5)
    return Math.round(delay + jitter)
  }, [initialReconnectInterval, maxReconnectInterval])

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (intentionalDisconnectRef.current) {
      return
    }

    // Clear any existing reconnect timers
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = undefined
    }
    if (countdownIntervalRef.current) {
      clearInterval(countdownIntervalRef.current)
      countdownIntervalRef.current = undefined
    }
    setReconnectCountdown(null)

    try {
      // Close existing connection if any
      if (wsRef.current) {
        if (wsRef.current.readyState === WebSocket.OPEN ||
            wsRef.current.readyState === WebSocket.CONNECTING) {
          wsRef.current.close(1000, 'Reconnecting')
        }
        wsRef.current = null
      }

      updateConnectionState(reconnectAttemptRef.current > 0 ? 'reconnecting' : 'connecting')

      const ws = new WebSocket(url)

      ws.onopen = () => {
        console.log('[WebSocket] Connected successfully')
        updateConnectionState('connected')
        reconnectAttemptRef.current = 0
        setReconnectAttempt(0)
        onConnect?.()

        // Clear persisted state on successful connection
        if (enablePersistence) {
          clearPersistedState()
        }

        // Start heartbeat monitoring
        startHeartbeat()

        // Replay any queued messages
        replayQueuedMessages()

        // Show toast only after reconnection
        if (hasConnectedOnceRef.current) {
          toast.success('Reconnected to real-time updates')
        }
        hasConnectedOnceRef.current = true
      }

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as WebSocketMessage

          // Handle pong response
          if (message.type === 'pong') {
            lastPongRef.current = Date.now()
            if (heartbeatTimeoutRef.current) {
              clearTimeout(heartbeatTimeoutRef.current)
              heartbeatTimeoutRef.current = undefined
            }
            return
          }

          setLastMessage(message)
          onMessage?.(message)
        } catch (error) {
          console.error('[WebSocket] Failed to parse message:', error)
        }
      }

      ws.onerror = (error) => {
        console.error('[WebSocket] Error:', error)
        onError?.(error)
      }

      ws.onclose = (event) => {
        stopHeartbeat()

        const disconnectDetails = logDisconnection(event.code, event.reason, event.wasClean)
        updateConnectionState('disconnected')
        onDisconnect?.(disconnectDetails.reason)

        // Don't reconnect if intentionally disconnected
        if (intentionalDisconnectRef.current) {
          return
        }

        // Don't reconnect if max attempts reached
        if (reconnectAttemptRef.current >= maxReconnectAttempts) {
          console.error('[WebSocket] Max reconnect attempts reached')
          toast.error('Connection lost. Please refresh the page.')
          return
        }

        // Schedule reconnection with exponential backoff
        const delay = getReconnectDelay(reconnectAttemptRef.current)
        reconnectAttemptRef.current++
        setReconnectAttempt(reconnectAttemptRef.current)

        console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${reconnectAttemptRef.current})`)

        // Persist state for cross-navigation recovery
        if (enablePersistence) {
          persistState({
            lastConnectedUrl: url,
            reconnectAttempt: reconnectAttemptRef.current,
            timestamp: Date.now()
          })
        }

        // Show visual countdown
        updateConnectionState('reconnecting')
        let remaining = Math.ceil(delay / 1000)
        setReconnectCountdown(remaining)

        countdownIntervalRef.current = setInterval(() => {
          remaining--
          setReconnectCountdown(remaining > 0 ? remaining : null)
        }, 1000)

        // Show toast for longer delays
        if (delay >= 5000) {
          toast.info(`Reconnecting in ${Math.ceil(delay / 1000)}s...`)
        }

        reconnectTimeoutRef.current = setTimeout(() => {
          if (countdownIntervalRef.current) {
            clearInterval(countdownIntervalRef.current)
            countdownIntervalRef.current = undefined
          }
          setReconnectCountdown(null)
          connect()
        }, delay)
      }

      wsRef.current = ws
    } catch (error) {
      console.error('[WebSocket] Failed to create connection:', error)
      updateConnectionState('disconnected')
    }
  }, [
    url,
    onMessage,
    onError,
    onConnect,
    onDisconnect,
    maxReconnectAttempts,
    getReconnectDelay,
    updateConnectionState,
    logDisconnection,
    startHeartbeat,
    stopHeartbeat,
    replayQueuedMessages,
    enablePersistence
  ])

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    intentionalDisconnectRef.current = true
    stopHeartbeat()

    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = undefined
    }
    if (countdownIntervalRef.current) {
      clearInterval(countdownIntervalRef.current)
      countdownIntervalRef.current = undefined
    }
    setReconnectCountdown(null)

    if (wsRef.current) {
      wsRef.current.close(1000, 'User disconnected')
      wsRef.current = null
    }

    updateConnectionState('disconnected')
    clearPersistedState()
  }, [stopHeartbeat, updateConnectionState])

  // Manually trigger reconnection
  const reconnect = useCallback(() => {
    intentionalDisconnectRef.current = false
    reconnectAttemptRef.current = 0
    setReconnectAttempt(0)
    connect()
  }, [connect])

  // Send message (queues if disconnected)
  const sendMessage = useCallback((message: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message))
      return true
    } else {
      // Queue message for later delivery
      console.log('[WebSocket] Queueing message for later delivery')
      const queuedMessage: QueuedMessage = {
        message,
        timestamp: Date.now()
      }

      messageQueueRef.current.push(queuedMessage)

      // Limit queue size
      if (messageQueueRef.current.length > messageQueueMaxSize) {
        messageQueueRef.current = messageQueueRef.current.slice(-messageQueueMaxSize)
      }

      // Persist queue
      if (enablePersistence) {
        persistQueuedMessages(url, messageQueueRef.current)
      }

      return false
    }
  }, [url, messageQueueMaxSize, enablePersistence])

  // Initialize connection and handle cleanup
  useEffect(() => {
    intentionalDisconnectRef.current = false
    hasConnectedOnceRef.current = false

    // Restore persisted state
    if (enablePersistence) {
      const persistedState = getPersistedState()
      if (persistedState && persistedState.lastConnectedUrl === url) {
        reconnectAttemptRef.current = persistedState.reconnectAttempt
        setReconnectAttempt(persistedState.reconnectAttempt)
        console.log(`[WebSocket] Restoring connection state (attempt ${persistedState.reconnectAttempt})`)
      }

      // Restore queued messages
      const queuedMessages = getQueuedMessages(url)
      if (queuedMessages.length > 0) {
        messageQueueRef.current = queuedMessages
        console.log(`[WebSocket] Restored ${queuedMessages.length} queued messages`)
      }
    }

    connect()

    return () => {
      disconnect()
    }
  }, [url]) // Only reconnect when URL changes

  return {
    isConnected,
    connectionState,
    lastMessage,
    sendMessage,
    disconnect,
    reconnect,
    reconnectAttempt,
    reconnectCountdown,
    queuedMessageCount: messageQueueRef.current.length
  }
}
