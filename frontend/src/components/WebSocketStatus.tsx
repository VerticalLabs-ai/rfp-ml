
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Wifi, WifiOff, RefreshCw } from 'lucide-react'
import { cn } from '@/lib/utils'

interface WebSocketStatusProps {
  isConnected: boolean
  onReconnect?: () => void
  showReconnect?: boolean
}

export function WebSocketStatus({
  isConnected,
  onReconnect,
  showReconnect = true
}: WebSocketStatusProps) {
  return (
    <div className="flex items-center gap-2">
      <Badge
        variant="outline"
        className={cn(
          'transition-colors',
          isConnected
            ? 'bg-green-50 text-green-700 border-green-200'
            : 'bg-red-50 text-red-700 border-red-200'
        )}
      >
        {isConnected ? (
          <Wifi className="w-3 h-3 mr-1" />
        ) : (
          <WifiOff className="w-3 h-3 mr-1" />
        )}
        <span className={cn(
          "w-2 h-2 rounded-full mr-2 animate-pulse",
          isConnected ? "bg-green-500" : "bg-red-500"
        )} />
        {isConnected ? 'Live' : 'Disconnected'}
      </Badge>

      {!isConnected && showReconnect && onReconnect && (
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
