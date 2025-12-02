import { useEffect, useRef, useState, useCallback } from 'react'
import { toast } from 'sonner'

interface WebSocketMessage {
  type: string
  data: any
  timestamp?: string
}

interface UseWebSocketOptions {
  url: string
  onMessage?: (message: WebSocketMessage) => void
  onError?: (error: Event) => void
  onConnect?: () => void
  onDisconnect?: () => void
  reconnectAttempts?: number
  reconnectInterval?: number
}

export function useWebSocket({
  url,
  onMessage,
  onError,
  onConnect,
  onDisconnect,
  reconnectAttempts = 5,
  reconnectInterval = 1000 // Faster initial reconnect
}: UseWebSocketOptions) {
  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectCountRef = useRef(0)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout>>()
  const intentionalDisconnectRef = useRef(false)
  const hasConnectedOnceRef = useRef(false)

  const connect = useCallback(() => {
    // Don't reconnect if intentionally disconnected
    if (intentionalDisconnectRef.current) {
      return
    }

    try {
      // Close existing connection if any
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.close()
      }

      const ws = new WebSocket(url)

      ws.onopen = () => {
        setIsConnected(true)
        reconnectCountRef.current = 0
        onConnect?.()

        // Only show toast on first connection or after an error
        if (!hasConnectedOnceRef.current) {
          hasConnectedOnceRef.current = true
          // Silently connect on first load - no toast needed
        } else if (reconnectCountRef.current > 0) {
          toast.success('Reconnected to real-time updates')
        }
      }

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as WebSocketMessage
          setLastMessage(message)
          onMessage?.(message)
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        onError?.(error)
        // Only show error toast if we were previously connected
        if (hasConnectedOnceRef.current) {
          toast.error('WebSocket connection error')
        }
      }

      ws.onclose = () => {
        setIsConnected(false)
        onDisconnect?.()

        // Don't reconnect if intentionally disconnected (component unmount/navigation)
        if (intentionalDisconnectRef.current) {
          return
        }

        // Attempt to reconnect with exponential backoff
        if (reconnectCountRef.current < reconnectAttempts) {
          reconnectCountRef.current++
          const delay = Math.min(reconnectInterval * Math.pow(1.5, reconnectCountRef.current - 1), 10000)

          // Only show reconnecting toast after multiple attempts
          if (reconnectCountRef.current >= 2) {
            toast.info(`Reconnecting... (${reconnectCountRef.current}/${reconnectAttempts})`)
          }

          reconnectTimeoutRef.current = setTimeout(() => {
            connect()
          }, delay)
        } else if (reconnectCountRef.current >= reconnectAttempts) {
          toast.error('Lost connection to real-time updates. Refresh to reconnect.')
        }
      }

      wsRef.current = ws
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error)
    }
  }, [url, onMessage, onError, onConnect, onDisconnect, reconnectAttempts, reconnectInterval])

  const disconnect = useCallback(() => {
    intentionalDisconnectRef.current = true
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
  }, [])

  const reconnect = useCallback(() => {
    intentionalDisconnectRef.current = false
    reconnectCountRef.current = 0
    connect()
  }, [connect])

  const sendMessage = useCallback((message: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message))
    } else {
      console.warn('WebSocket is not connected')
    }
  }, [])

  useEffect(() => {
    intentionalDisconnectRef.current = false
    hasConnectedOnceRef.current = false
    reconnectCountRef.current = 0
    connect()

    return () => {
      disconnect()
    }
  }, [url])

  return {
    isConnected,
    lastMessage,
    sendMessage,
    disconnect,
    reconnect
  }
}
