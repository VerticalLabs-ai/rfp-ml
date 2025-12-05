/**
 * Win/Loss Analytics Dashboard
 *
 * Comprehensive analytics for tracking proposal outcomes,
 * competitor analysis, and bid strategy optimization.
 */
import { useQuery } from '@tanstack/react-query'
import {
  TrendingUp,
  TrendingDown,
  Target,
  DollarSign,
  Users,
  Clock,
  Trophy,
  XCircle,
} from 'lucide-react'

import { api } from '@/services/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import type { AnalyticsDashboard } from '@/types/analytics'

export default function WinLossAnalytics() {
  const { data, isLoading, error } = useQuery<AnalyticsDashboard>({
    queryKey: ['analytics-overview'],
    queryFn: () => api.getAnalyticsOverview(),
    staleTime: 60 * 1000, // 1 minute
  })

  if (error) {
    return (
      <div className="p-6">
        <div className="text-center text-red-500">
          Failed to load analytics data. Please try again.
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Win/Loss Analytics</h1>
          <p className="text-muted-foreground">
            Track proposal outcomes and optimize your bid strategy
          </p>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {/* Win Rate */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Win Rate</CardTitle>
            <Target className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-24" />
            ) : (
              <>
                <div className="text-2xl font-bold">
                  {((data?.stats.win_rate ?? 0) * 100).toFixed(1)}%
                </div>
                <p className="text-xs text-muted-foreground">
                  {data?.stats.wins ?? 0} wins / {(data?.stats.wins ?? 0) + (data?.stats.losses ?? 0)} decided
                </p>
              </>
            )}
          </CardContent>
        </Card>

        {/* Total Bids */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Bids</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-24" />
            ) : (
              <>
                <div className="text-2xl font-bold">{data?.stats.total_bids ?? 0}</div>
                <p className="text-xs text-muted-foreground">
                  {data?.stats.pending ?? 0} pending decisions
                </p>
              </>
            )}
          </CardContent>
        </Card>

        {/* Revenue Won */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Revenue Won</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-24" />
            ) : (
              <>
                <div className="text-2xl font-bold">
                  ${((data?.stats.total_revenue_won ?? 0) / 1000000).toFixed(1)}M
                </div>
                <p className="text-xs text-muted-foreground">
                  Avg deal: ${((data?.stats.average_deal_size ?? 0) / 1000).toFixed(0)}K
                </p>
              </>
            )}
          </CardContent>
        </Card>

        {/* Wins vs Losses */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Wins vs Losses</CardTitle>
            <Trophy className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-24" />
            ) : (
              <>
                <div className="text-2xl font-bold flex items-center gap-2">
                  <span className="text-green-600">{data?.stats.wins ?? 0}</span>
                  <span className="text-muted-foreground">/</span>
                  <span className="text-red-600">{data?.stats.losses ?? 0}</span>
                </div>
                <div className="flex items-center gap-4 text-xs">
                  <span className="flex items-center text-green-600">
                    <TrendingUp className="h-3 w-3 mr-1" />
                    Won
                  </span>
                  <span className="flex items-center text-red-600">
                    <TrendingDown className="h-3 w-3 mr-1" />
                    Lost
                  </span>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Placeholder for charts - will be added in next task */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Win Rate Trends</CardTitle>
          </CardHeader>
          <CardContent className="h-[300px] flex items-center justify-center text-muted-foreground">
            {isLoading ? (
              <Skeleton className="h-full w-full" />
            ) : (
              'Chart coming in next task'
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Top Competitors</CardTitle>
          </CardHeader>
          <CardContent className="h-[300px] flex items-center justify-center text-muted-foreground">
            {isLoading ? (
              <Skeleton className="h-full w-full" />
            ) : (
              'Competitor table coming in next task'
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
