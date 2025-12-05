import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from 'recharts';
import {
  RefreshCw,
  Users,
  TrendingDown,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Target,
} from 'lucide-react';
import { api } from '@/services/api';
import type { MarginImpactRow } from '@/types/pricing';

interface PTWAnalysisProps {
  rfpId: string;
  currentPrice?: number | null;
  onPriceChange?: (price: number) => void;
}

export function PTWAnalysis({ rfpId, currentPrice, onPriceChange }: PTWAnalysisProps) {
  const {
    data,
    isLoading,
    error,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ['ptw-analysis', rfpId, currentPrice],
    queryFn: () => api.getPTWAnalysis(rfpId, currentPrice || undefined),
    enabled: !!rfpId,
    staleTime: 2 * 60 * 1000,
  });

  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);

  const getRiskColor = (risk: string) => {
    if (risk.toLowerCase().includes('thin') || risk.toLowerCase().includes('low win'))
      return 'text-yellow-600';
    if (risk.toLowerCase().includes('high') || risk.toLowerCase().includes('❌'))
      return 'text-red-600';
    if (risk.toLowerCase().includes('good') || risk.toLowerCase().includes('acceptable'))
      return 'text-green-600';
    return 'text-muted-foreground';
  };

  const getRiskIcon = (risk: string) => {
    if (risk.toLowerCase().includes('good') || risk.toLowerCase().includes('acceptable'))
      return <CheckCircle2 className="h-4 w-4 text-green-500" />;
    if (risk.toLowerCase().includes('high') || risk.toLowerCase().includes('❌'))
      return <XCircle className="h-4 w-4 text-red-500" />;
    return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
  };

  if (error) {
    return (
      <Card>
        <CardContent className="py-8 text-center">
          <p className="text-muted-foreground">Failed to load PTW analysis</p>
          <Button variant="outline" onClick={() => refetch()} className="mt-4">
            <RefreshCw className="h-4 w-4 mr-2" />
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  // Prepare competitor bar chart data
  const competitorChartData = data?.competitor_estimates
    ? [
        {
          name: 'Low Bidder',
          price: data.competitor_estimates.low_bidder,
          fill: '#ef4444',
        },
        {
          name: 'Average',
          price: data.competitor_estimates.average,
          fill: '#f59e0b',
        },
        ...(currentPrice
          ? [
              {
                name: 'Your Price',
                price: currentPrice,
                fill: '#10b981',
              },
            ]
          : []),
        {
          name: 'High Bidder',
          price: data.competitor_estimates.high_bidder,
          fill: '#6b7280',
        },
      ]
    : [];

  return (
    <div className="space-y-6">
      {/* Competitor Estimation */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between py-4">
          <CardTitle className="text-lg flex items-center gap-2">
            <Users className="h-5 w-5" />
            Competitor Estimation
          </CardTitle>
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isFetching}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${isFetching ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-64 w-full" />
          ) : data?.competitor_estimates ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">
                  Expected Competitors:
                </span>
                <Badge variant="secondary">
                  {data.competitor_estimates.expected_bidders} bidders
                </Badge>
              </div>

              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={competitorChartData}
                    layout="vertical"
                    margin={{ left: 80 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      type="number"
                      tickFormatter={(value) =>
                        `$${(value / 1000).toFixed(0)}K`
                      }
                    />
                    <YAxis type="category" dataKey="name" />
                    <Tooltip
                      formatter={(value: number) => formatCurrency(value)}
                    />
                    <Bar dataKey="price" radius={[0, 4, 4, 0]}>
                      {competitorChartData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.fill} />
                      ))}
                    </Bar>
                    {currentPrice && (
                      <ReferenceLine
                        x={currentPrice}
                        stroke="#10b981"
                        strokeWidth={2}
                        strokeDasharray="5 5"
                      />
                    )}
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="grid grid-cols-3 gap-4 text-center">
                <div className="p-3 bg-red-50 rounded-lg">
                  <p className="text-sm text-muted-foreground">Low Bidder</p>
                  <p className="text-lg font-semibold text-red-600">
                    {formatCurrency(data.competitor_estimates.low_bidder)}
                  </p>
                </div>
                <div className="p-3 bg-yellow-50 rounded-lg">
                  <p className="text-sm text-muted-foreground">Average</p>
                  <p className="text-lg font-semibold text-yellow-600">
                    {formatCurrency(data.competitor_estimates.average)}
                  </p>
                </div>
                <div className="p-3 bg-gray-50 rounded-lg">
                  <p className="text-sm text-muted-foreground">High Bidder</p>
                  <p className="text-lg font-semibold text-gray-600">
                    {formatCurrency(data.competitor_estimates.high_bidder)}
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <p className="text-muted-foreground text-center py-4">
              No competitor data available
            </p>
          )}
        </CardContent>
      </Card>

      {/* Minimum Viable Price */}
      <Card>
        <CardHeader className="py-4">
          <CardTitle className="text-lg flex items-center gap-2">
            <TrendingDown className="h-5 w-5" />
            Minimum Viable Price
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-4">
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-16 w-full" />
            </div>
          ) : data?.minimum_viable ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 bg-red-50 rounded-lg">
                <div>
                  <p className="font-medium">Absolute Floor (0% margin)</p>
                  <p className="text-sm text-muted-foreground">
                    Break-even point, no profit
                  </p>
                </div>
                <p className="text-xl font-bold text-red-600">
                  {formatCurrency(data.minimum_viable.absolute_floor)}
                </p>
              </div>

              <div className="flex items-center justify-between p-4 bg-yellow-50 rounded-lg">
                <div>
                  <p className="font-medium">Minimum Viable (10% margin)</p>
                  <p className="text-sm text-muted-foreground">
                    Minimum acceptable profit
                  </p>
                </div>
                <p className="text-xl font-bold text-yellow-600">
                  {formatCurrency(data.minimum_viable.minimum_margin)}
                </p>
              </div>

              <div className="flex items-center justify-between p-4 bg-green-50 rounded-lg">
                <div>
                  <p className="font-medium">Recommended Floor (15% margin)</p>
                  <p className="text-sm text-muted-foreground">
                    Healthy profit margin
                  </p>
                </div>
                <p className="text-xl font-bold text-green-600">
                  {formatCurrency(data.minimum_viable.recommended_floor)}
                </p>
              </div>

              {currentPrice && currentPrice < data.minimum_viable.minimum_margin && (
                <div className="flex items-center gap-2 p-3 bg-red-100 rounded-lg text-red-800">
                  <AlertTriangle className="h-5 w-5" />
                  <span className="text-sm">
                    Warning: Current price is below minimum viable margin
                  </span>
                </div>
              )}
            </div>
          ) : null}
        </CardContent>
      </Card>

      {/* Margin Impact Analysis */}
      <Card>
        <CardHeader className="py-4">
          <CardTitle className="text-lg flex items-center gap-2">
            <Target className="h-5 w-5" />
            Margin Impact Analysis
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-64 w-full" />
          ) : data?.margin_impact_table && data.margin_impact_table.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Price Point</TableHead>
                  <TableHead className="text-right">Margin</TableHead>
                  <TableHead className="text-right">Profit</TableHead>
                  <TableHead className="text-right">Win Prob</TableHead>
                  <TableHead>Risk</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.margin_impact_table.map((row: MarginImpactRow, index: number) => {
                  const isCurrentPrice =
                    currentPrice &&
                    Math.abs(row.price - currentPrice) < currentPrice * 0.02;

                  return (
                    <TableRow
                      key={index}
                      className={`cursor-pointer hover:bg-muted/50 ${
                        isCurrentPrice ? 'bg-green-50' : ''
                      }`}
                      onClick={() => onPriceChange?.(row.price)}
                    >
                      <TableCell className="font-medium">
                        {formatCurrency(row.price)}
                        {isCurrentPrice && (
                          <Badge variant="secondary" className="ml-2 text-xs">
                            Current
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        {row.margin_percent.toFixed(1)}%
                      </TableCell>
                      <TableCell className="text-right">
                        {formatCurrency(row.profit)}
                      </TableCell>
                      <TableCell className="text-right">
                        {(row.win_probability * 100).toFixed(0)}%
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          {getRiskIcon(row.risk_assessment)}
                          <span className={getRiskColor(row.risk_assessment)}>
                            {row.risk_assessment}
                          </span>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          ) : (
            <p className="text-muted-foreground text-center py-4">
              No margin impact data available
            </p>
          )}
        </CardContent>
      </Card>

      {/* Overall Risk Assessment */}
      <Card>
        <CardHeader className="py-4">
          <CardTitle className="text-lg flex items-center gap-2">
            <AlertTriangle className="h-5 w-5" />
            Risk Assessment at Current Price
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-4">
              <Skeleton className="h-8 w-48" />
              <Skeleton className="h-20 w-full" />
            </div>
          ) : data?.risk_assessment ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-lg font-medium">Overall Risk Score</span>
                <div className="flex items-center gap-2">
                  <span className="text-2xl font-bold">
                    {data.risk_assessment.score}/100
                  </span>
                  <Badge
                    variant="secondary"
                    className={
                      data.risk_assessment.level === 'Low'
                        ? 'bg-green-100 text-green-800'
                        : data.risk_assessment.level === 'Medium'
                        ? 'bg-yellow-100 text-yellow-800'
                        : 'bg-red-100 text-red-800'
                    }
                  >
                    {data.risk_assessment.level}
                  </Badge>
                </div>
              </div>

              {/* Risk Progress Bar */}
              <div className="relative h-4 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className={`absolute h-full transition-all ${
                    data.risk_assessment.score < 30
                      ? 'bg-green-500'
                      : data.risk_assessment.score < 60
                      ? 'bg-yellow-500'
                      : 'bg-red-500'
                  }`}
                  style={{ width: `${data.risk_assessment.score}%` }}
                />
              </div>

              {data.risk_assessment.factors.length > 0 && (
                <div className="space-y-2">
                  {data.risk_assessment.factors.map((factor: string, index: number) => (
                    <div
                      key={index}
                      className="flex items-start gap-2 text-sm p-2 rounded bg-muted"
                    >
                      <AlertTriangle className="h-4 w-4 text-yellow-600 mt-0.5 shrink-0" />
                      <span>{factor}</span>
                    </div>
                  ))}
                </div>
              )}

              {data.current_position?.vs_market !== null && (
                <div className="p-4 bg-blue-50 rounded-lg">
                  <p className="text-sm">
                    Your price is{' '}
                    <span className="font-semibold">
                      {data.current_position.vs_market > 0 ? '+' : ''}
                      {data.current_position.vs_market?.toFixed(1)}%
                    </span>{' '}
                    {data.current_position.vs_market! > 0 ? 'above' : 'below'} market
                    median
                  </p>
                </div>
              )}
            </div>
          ) : (
            <p className="text-muted-foreground text-center py-4">
              Enter a price to see risk assessment
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
