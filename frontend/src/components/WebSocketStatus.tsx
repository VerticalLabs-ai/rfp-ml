import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Wifi, WifiOff, RefreshCw, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ConnectionState } from '@/hooks/useWebSocket'

interface WebSocketStatusProps {
  isConnected: boolean
  connectionState?: ConnectionState
  reconnectAttempt?: number
  reconnectCountdown?: number | null
  queuedMessageCount?: number
  onReconnect?: () => void
  showReconnect?: boolean
}

export function WebSocketStatus({
  isConnected,
  connectionState = isConnected ? 'connected' : 'disconnected',
  reconnectAttempt = 0,
  reconnectCountdown = null,
  queuedMessageCount = 0,
  onReconnect,
  showReconnect = true
}: WebSocketStatusProps) {
  const isReconnecting = connectionState === 'reconnecting'
  const isConnecting = connectionState === 'connecting'

  // Determine status display
  const getStatusConfig = () => {
    if (isConnected) {
      return {
        icon: <Wifi className="w-3 h-3 mr-1" />,
        label: 'Live',
        badgeClass: 'bg-green-50 text-green-700 border-green-200 dark:bg-green-900/20 dark:text-green-400 dark:border-green-800',
        dotClass: 'bg-green-500',
        showSpinner: false
      }
    }

    if (isReconnecting) {
      return {
        icon: <Loader2 className="w-3 h-3 mr-1 animate-spin" />,
        label: reconnectCountdown ? `Reconnecting (${reconnectCountdown}s)` : `Reconnecting...`,
        badgeClass: 'bg-yellow-50 text-yellow-700 border-yellow-200 dark:bg-yellow-900/20 dark:text-yellow-400 dark:border-yellow-800',
        dotClass: 'bg-yellow-500',
        showSpinner: true
      }
    }

    if (isConnecting) {
      return {
        icon: <Loader2 className="w-3 h-3 mr-1 animate-spin" />,
        label: 'Connecting...',
        badgeClass: 'bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-900/20 dark:text-blue-400 dark:border-blue-800',
        dotClass: 'bg-blue-500',
        showSpinner: true
      }
    }

    // Disconnected
    return {
      icon: <WifiOff className="w-3 h-3 mr-1" />,
      label: 'Disconnected',
      badgeClass: 'bg-red-50 text-red-700 border-red-200 dark:bg-red-900/20 dark:text-red-400 dark:border-red-800',
      dotClass: 'bg-red-500',
      showSpinner: false
    }
  }

  const statusConfig = getStatusConfig()

  return (
    <div className="flex items-center gap-2">
      <Badge
        variant="outline"
        className={cn(
          'transition-all duration-300',
          statusConfig.badgeClass
        )}
      >
        {statusConfig.icon}
        {!statusConfig.showSpinner && (
          <span className={cn(
            "w-2 h-2 rounded-full mr-2",
            statusConfig.dotClass,
            isConnected && "animate-pulse"
          )} />
        )}
        {statusConfig.label}
        {reconnectAttempt > 0 && isReconnecting && (
          <span className="ml-1 text-xs opacity-70">
            #{reconnectAttempt}
          </span>
        )}
      </Badge>

      {/* Show queued message indicator */}
      {queuedMessageCount > 0 && !isConnected && (
        <Badge
          variant="outline"
          className="bg-orange-50 text-orange-700 border-orange-200 dark:bg-orange-900/20 dark:text-orange-400 dark:border-orange-800"
        >
          {queuedMessageCount} queued
        </Badge>
      )}

      {/* Only show reconnect button if fully disconnected (not auto-reconnecting) */}
      {!isConnected && !isReconnecting && !isConnecting && showReconnect && onReconnect && (
        <Button
          variant="ghost"
          size="sm"
          onClick={onReconnect}
          className="h-7 text-xs"
        >
          <RefreshCw className="w-3 h-3 mr-1" />
          Reconnect
        </Button>
      )}
    </div>
  )
}
