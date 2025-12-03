import { Link, useLocation } from 'react-router-dom'
import { Bookmark, LayoutDashboard, Search, GitBranch, CheckSquare, Send, Zap, TrendingUp, Settings, Building2 } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/services/api'
import { WebSocketStatus } from '@/components/WebSocketStatus'
import { RAGStatus } from '@/components/RAGStatus'
import { useWebSocket } from '@/hooks/useWebSocket'

interface LayoutProps {
  children: React.ReactNode
}

const navigation = [
  { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
  { name: 'RFP Discovery', path: '/discovery', icon: Search },
  { name: 'Saved', path: '/saved', icon: Bookmark },
  { name: 'Forecasts', path: '/forecasts', icon: TrendingUp },
  { name: 'Pipeline', path: '/pipeline', icon: GitBranch },
  { name: 'Decisions', path: '/decisions', icon: CheckSquare },
  { name: 'Submissions', path: '/submissions', icon: Send },
  { name: 'Profiles', path: '/profiles', icon: Building2 },
  { name: 'Settings', path: '/settings', icon: Settings }
]

export default function Layout({ children }: LayoutProps) {
  const location = useLocation()

  // Fetch saved RFPs count for badge
  const { data: savedData } = useQuery({
    queryKey: ['saved-rfps-count'],
    queryFn: () => api.savedRfps.list({ limit: 1 }),
    staleTime: 60000, // Cache for 1 minute
  })
  const savedCount = savedData?.total ?? 0

  // WebSocket connection for real-time updates
  // Use dynamic URL based on current host (supports both localhost and production)
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = import.meta.env.VITE_WS_URL || `${wsProtocol}//${window.location.host}/ws/pipeline`
  const {
    isConnected,
    connectionState,
    reconnect,
    reconnectAttempt,
    reconnectCountdown,
    queuedMessageCount
  } = useWebSocket({
    url: wsUrl,
    onMessage: (message) => {
      console.log('WebSocket message:', message)
      // Handle real-time updates here
    }
  })

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-purple-600 rounded-lg flex items-center justify-center">
                <Zap className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900 dark:text-white">
                  RFP Bid Generation System
                </h1>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  AI-Powered Proposal Management
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <RAGStatus />
              <WebSocketStatus
                isConnected={isConnected}
                connectionState={connectionState}
                reconnectAttempt={reconnectAttempt}
                reconnectCountdown={reconnectCountdown}
                queuedMessageCount={queuedMessageCount}
                onReconnect={reconnect}
              />
            </div>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <nav className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-1">
            {navigation.map((item) => {
              const isActive = location.pathname === item.path
              const Icon = item.icon
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`
                    inline-flex items-center gap-2 px-4 py-4 border-b-2 text-sm font-medium
                    transition-colors duration-200
                    ${isActive
                      ? 'border-blue-600 text-blue-600 dark:border-blue-400 dark:text-blue-400 bg-blue-50/50 dark:bg-blue-900/10'
                      : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:border-gray-300 dark:hover:border-gray-600'
                    }
                  `}
                >
                  <Icon className="w-4 h-4" />
                  <span>{item.name}</span>
                  {item.name === 'Saved' && savedCount > 0 && (
                    <span className="ml-1 px-1.5 py-0.5 text-xs font-medium bg-blue-100 text-blue-600 dark:bg-blue-900 dark:text-blue-300 rounded-full">
                      {savedCount}
                    </span>
                  )}
                </Link>
              )
            })}
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>
    </div>
  )
}
