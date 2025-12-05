/**
 * Win/Loss Analytics Dashboard
 *
 * Comprehensive analytics for tracking proposal outcomes,
 * competitor analysis, and bid strategy optimization.
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  TrendingUp,
  TrendingDown,
  Target,
  DollarSign,
  Users,
  Trophy,
  Plus,
  Filter,
  X,
  Download,
} from 'lucide-react'
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'

import { api } from '@/services/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { toast } from 'sonner'
import RecordOutcomeDialog from '@/components/RecordOutcomeDialog'
import type { AnalyticsDashboard, AnalyticsFilters } from '@/types/analytics'

export default function WinLossAnalytics() {
  const [recordDialogOpen, setRecordDialogOpen] = useState(false)
  const [filters, setFilters] = useState<AnalyticsFilters>({})
  const [showFilters, setShowFilters] = useState(false)
  const [isExporting, setIsExporting] = useState(false)

  const { data, isLoading, error } = useQuery<AnalyticsDashboard>({
    queryKey: ['analytics-overview', filters],
    queryFn: () => api.getAnalyticsOverview(filters),
    staleTime: 60 * 1000, // 1 minute
  })

  const handleFilterChange = (key: keyof AnalyticsFilters, value: string) => {
    setFilters(prev => ({
      ...prev,
      [key]: value === '' ? undefined : value,
    }))
  }

  const clearFilters = () => {
    setFilters({})
  }

  const handleExport = async () => {
    setIsExporting(true)
    try {
      const blob = await api.exportAnalytics('csv')
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `analytics-export-${new Date().toISOString().split('T')[0]}.csv`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      toast.success('Analytics exported successfully')
    } catch (error) {
      console.error('Export failed:', error)
      toast.error('Failed to export analytics')
    } finally {
      setIsExporting(false)
    }
  }

  const activeFilterCount = Object.values(filters).filter(v => v !== undefined && v !== '').length

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
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={() => setShowFilters(!showFilters)}
            className="relative"
          >
            <Filter className="w-4 h-4 mr-2" />
            Filters
            {activeFilterCount > 0 && (
              <Badge
                variant="destructive"
                className="ml-2 h-5 w-5 rounded-full p-0 flex items-center justify-center text-xs"
              >
                {activeFilterCount}
              </Badge>
            )}
          </Button>
          <Button
            variant="outline"
            onClick={handleExport}
            disabled={isExporting}
          >
            {isExporting ? (
              <>
                <div className="w-4 h-4 mr-2 animate-spin rounded-full border-2 border-current border-t-transparent" />
                Exporting...
              </>
            ) : (
              <>
                <Download className="w-4 h-4 mr-2" />
                Export CSV
              </>
            )}
          </Button>
          <Button onClick={() => setRecordDialogOpen(true)}>
            <Plus className="w-4 h-4 mr-2" />
            Record Outcome
          </Button>
        </div>
      </div>

      {/* Filter Bar */}
      {showFilters && (
        <Card>
          <CardContent className="pt-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="space-y-2">
                <label htmlFor="start_date" className="text-sm font-medium">
                  Start Date
                </label>
                <Input
                  id="start_date"
                  type="date"
                  value={filters.start_date || ''}
                  onChange={(e) => handleFilterChange('start_date', e.target.value)}
                  placeholder="Start date"
                />
              </div>
              <div className="space-y-2">
                <label htmlFor="end_date" className="text-sm font-medium">
                  End Date
                </label>
                <Input
                  id="end_date"
                  type="date"
                  value={filters.end_date || ''}
                  onChange={(e) => handleFilterChange('end_date', e.target.value)}
                  placeholder="End date"
                />
              </div>
              <div className="space-y-2">
                <label htmlFor="agency" className="text-sm font-medium">
                  Agency
                </label>
                <Input
                  id="agency"
                  type="text"
                  value={filters.agency || ''}
                  onChange={(e) => handleFilterChange('agency', e.target.value)}
                  placeholder="Filter by agency"
                />
              </div>
              <div className="space-y-2">
                <label htmlFor="naics_code" className="text-sm font-medium">
                  NAICS Code
                </label>
                <Input
                  id="naics_code"
                  type="text"
                  value={filters.naics_code || ''}
                  onChange={(e) => handleFilterChange('naics_code', e.target.value)}
                  placeholder="Filter by NAICS"
                />
              </div>
            </div>
            {activeFilterCount > 0 && (
              <div className="flex items-center justify-end mt-4 pt-4 border-t">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={clearFilters}
                  className="text-muted-foreground"
                >
                  <X className="w-4 h-4 mr-2" />
                  Clear All Filters
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Record Outcome Dialog */}
      <RecordOutcomeDialog
        open={recordDialogOpen}
        onOpenChange={setRecordDialogOpen}
      />

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

      {/* Charts Section */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* Win Rate Trend Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Win Rate Trend</CardTitle>
          </CardHeader>
          <CardContent className="h-[300px]">
            {isLoading ? (
              <Skeleton className="h-full w-full" />
            ) : !data?.trends || data.trends.length === 0 ? (
              <div className="h-full flex items-center justify-center text-muted-foreground">
                No trend data available
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={data.trends.map((trend) => ({
                    ...trend,
                    win_rate_percent: trend.win_rate * 100,
                  }))}
                  margin={{ top: 5, right: 30, left: 0, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis
                    dataKey="period"
                    className="text-xs"
                    tick={{ fill: 'currentColor' }}
                  />
                  <YAxis
                    className="text-xs"
                    tick={{ fill: 'currentColor' }}
                    label={{ value: 'Win Rate (%)', angle: -90, position: 'insideLeft' }}
                    domain={[0, 100]}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'hsl(var(--background))',
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '6px',
                    }}
                    formatter={(value: number, name: string) => {
                      if (name === 'win_rate_percent') {
                        return [`${value.toFixed(1)}%`, 'Win Rate']
                      }
                      if (name === 'wins') {
                        return [value, 'Wins']
                      }
                      if (name === 'losses') {
                        return [value, 'Losses']
                      }
                      return [value, name]
                    }}
                  />
                  <Legend
                    wrapperStyle={{ fontSize: '12px' }}
                    formatter={(value: string) => {
                      if (value === 'win_rate_percent') return 'Win Rate'
                      if (value === 'wins') return 'Wins'
                      if (value === 'losses') return 'Losses'
                      return value
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="win_rate_percent"
                    stroke="hsl(142, 76%, 36%)"
                    strokeWidth={2}
                    dot={{ fill: 'hsl(142, 76%, 36%)', r: 4 }}
                    activeDot={{ r: 6 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="wins"
                    stroke="hsl(142, 76%, 60%)"
                    strokeWidth={1.5}
                    strokeDasharray="5 5"
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="losses"
                    stroke="hsl(0, 84%, 60%)"
                    strokeWidth={1.5}
                    strokeDasharray="5 5"
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        {/* Top Competitors Table */}
        <Card>
          <CardHeader>
            <CardTitle>Top Competitors</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-[300px] w-full" />
            ) : !data?.top_competitors || data.top_competitors.length === 0 ? (
              <div className="h-[300px] flex items-center justify-center text-muted-foreground">
                No competitor data available
              </div>
            ) : (
              <div className="max-h-[300px] overflow-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Competitor Name</TableHead>
                      <TableHead className="text-right">Encounters</TableHead>
                      <TableHead className="text-right">Their Win Rate</TableHead>
                      <TableHead className="text-right">Avg Price Difference</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.top_competitors.slice(0, 10).map((competitor) => {
                      const winRatePercent = competitor.win_rate * 100

                      // Determine badge variant based on win rate
                      // Red (destructive) if they win > 60%
                      // Yellow-ish (outline) if balanced 40-60%
                      // Green (secondary with custom color) if we win more < 40%
                      let badgeVariant: 'destructive' | 'outline' | 'default' = 'outline'
                      let badgeClassName = ''

                      if (winRatePercent > 60) {
                        badgeVariant = 'destructive'
                      } else if (winRatePercent < 40) {
                        badgeVariant = 'default'
                        badgeClassName = 'bg-green-600 hover:bg-green-700'
                      }

                      return (
                        <TableRow key={competitor.competitor_name}>
                          <TableCell className="font-medium">
                            {competitor.competitor_name}
                          </TableCell>
                          <TableCell className="text-right">
                            {competitor.encounters}
                          </TableCell>
                          <TableCell className="text-right">
                            <Badge variant={badgeVariant} className={badgeClassName}>
                              {winRatePercent.toFixed(1)}%
                            </Badge>
                          </TableCell>
                          <TableCell className="text-right">
                            {competitor.average_winning_margin !== null &&
                            competitor.average_winning_margin !== undefined
                              ? `${(competitor.average_winning_margin * 100).toFixed(1)}%`
                              : 'N/A'}
                          </TableCell>
                        </TableRow>
                      )
                    })}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Win Rate by Agency Chart */}
      <Card>
        <CardHeader>
          <CardTitle>Win Rate by Agency</CardTitle>
        </CardHeader>
        <CardContent className="h-[400px]">
          {isLoading ? (
            <Skeleton className="h-full w-full" />
          ) : !data?.win_rate_by_agency || Object.keys(data.win_rate_by_agency).length === 0 ? (
            <div className="h-full flex items-center justify-center text-muted-foreground">
              No agency data available
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={Object.entries(data.win_rate_by_agency)
                  .map(([name, rate]) => ({ name, win_rate: rate * 100 }))
                  .sort((a, b) => b.win_rate - a.win_rate)
                  .slice(0, 8)}
                layout="vertical"
                margin={{ top: 5, right: 30, left: 100, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis
                  type="number"
                  domain={[0, 100]}
                  className="text-xs"
                  tick={{ fill: 'currentColor' }}
                  label={{ value: 'Win Rate (%)', position: 'insideBottom', offset: -5 }}
                />
                <YAxis
                  type="category"
                  dataKey="name"
                  className="text-xs"
                  tick={{ fill: 'currentColor' }}
                  width={90}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'hsl(var(--background))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '6px',
                  }}
                  formatter={(value: number) => [`${value.toFixed(1)}%`, 'Win Rate']}
                />
                <Bar dataKey="win_rate" radius={[0, 4, 4, 0]}>
                  {Object.entries(data.win_rate_by_agency)
                    .map(([name, rate]) => ({ name, win_rate: rate * 100 }))
                    .sort((a, b) => b.win_rate - a.win_rate)
                    .slice(0, 8)
                    .map((entry, index) => {
                      // Color gradient from red (low) to yellow (medium) to green (high)
                      const getBarColor = (winRate: number) => {
                        if (winRate >= 70) return 'hsl(142, 76%, 36%)' // Green
                        if (winRate >= 50) return 'hsl(142, 76%, 50%)' // Light green
                        if (winRate >= 30) return 'hsl(45, 93%, 47%)' // Yellow
                        if (winRate >= 15) return 'hsl(25, 95%, 53%)' // Orange
                        return 'hsl(0, 84%, 60%)' // Red
                      }

                      return <Cell key={`cell-${index}`} fill={getBarColor(entry.win_rate)} />
                    })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
