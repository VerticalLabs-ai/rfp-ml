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
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
} from 'recharts';
import { RefreshCw, TrendingUp, Building2 } from 'lucide-react';
import { api } from '@/services/api';
import type { MarketIntelligenceData, SimilarContract } from '@/types/pricing';

interface MarketIntelligenceProps {
  rfpId: string;
  naicsCode?: string | null;
  currentPrice?: number | null;
}

export function MarketIntelligence({ rfpId, naicsCode, currentPrice }: MarketIntelligenceProps) {
  const {
    data,
    isLoading,
    error,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ['market-intelligence', rfpId],
    queryFn: () => api.getMarketIntelligence(rfpId),
    enabled: !!rfpId,
    staleTime: 5 * 60 * 1000,
  });

  const { data: trendsData } = useQuery({
    queryKey: ['pricing-trends', naicsCode],
    queryFn: () => api.getPricingTrends(naicsCode!),
    enabled: !!naicsCode,
    staleTime: 10 * 60 * 1000,
  });

  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);

  const formatCompactCurrency = (amount: number) => {
    if (amount >= 1000000) return `$${(amount / 1000000).toFixed(1)}M`;
    if (amount >= 1000) return `$${(amount / 1000).toFixed(0)}K`;
    return `$${amount}`;
  };

  const calculatePercentile = (price: number, range: MarketIntelligenceData['award_range']) => {
    if (!range || !price) return null;
    if (price <= range.min) return 0;
    if (price >= range.max) return 100;
    if (price <= range.p25) return ((price - range.min) / (range.p25 - range.min)) * 25;
    if (price <= range.median) return 25 + ((price - range.p25) / (range.median - range.p25)) * 25;
    if (price <= range.p75) return 50 + ((price - range.median) / (range.p75 - range.median)) * 25;
    return 75 + ((price - range.p75) / (range.max - range.p75)) * 25;
  };

  if (error) {
    return (
      <Card>
        <CardContent className="py-8 text-center">
          <p className="text-muted-foreground">Failed to load market intelligence</p>
          <Button variant="outline" onClick={() => refetch()} className="mt-4">
            <RefreshCw className="h-4 w-4 mr-2" />
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  const percentile = data?.award_range && currentPrice
    ? calculatePercentile(currentPrice, data.award_range)
    : null;

  return (
    <div className="space-y-6">
      {/* Award Range Analysis */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between py-4">
          <CardTitle className="text-lg">Award Range Analysis</CardTitle>
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
            <div className="space-y-4">
              <Skeleton className="h-4 w-64" />
              <Skeleton className="h-32 w-full" />
            </div>
          ) : data?.award_range ? (
            <div className="space-y-6">
              <div className="flex items-center gap-2">
                <Badge variant="secondary">{naicsCode || 'All Categories'}</Badge>
                <span className="text-sm text-muted-foreground">
                  Based on {data.award_range.count} comparable contracts
                </span>
              </div>

              {/* Range Visualization */}
              <div className="space-y-2">
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>Min</span>
                  <span>25th</span>
                  <span>Median</span>
                  <span>75th</span>
                  <span>Max</span>
                </div>
                <div className="flex justify-between text-sm font-medium">
                  <span>{formatCompactCurrency(data.award_range.min)}</span>
                  <span>{formatCompactCurrency(data.award_range.p25)}</span>
                  <span>{formatCompactCurrency(data.award_range.median)}</span>
                  <span>{formatCompactCurrency(data.award_range.p75)}</span>
                  <span>{formatCompactCurrency(data.award_range.max)}</span>
                </div>
                <div className="relative h-8 bg-muted rounded-full overflow-hidden">
                  {/* Range bar */}
                  <div
                    className="absolute h-full bg-blue-200"
                    style={{
                      left: '10%',
                      right: '10%',
                    }}
                  />
                  {/* IQR (25th-75th) */}
                  <div
                    className="absolute h-full bg-blue-400"
                    style={{
                      left: '25%',
                      right: '25%',
                    }}
                  />
                  {/* Median marker */}
                  <div
                    className="absolute h-full w-1 bg-blue-600"
                    style={{ left: '50%', transform: 'translateX(-50%)' }}
                  />
                  {/* Current price marker */}
                  {percentile !== null && (
                    <div
                      className="absolute h-full w-2 bg-green-500 rounded-full border-2 border-white shadow"
                      style={{ left: `${percentile}%`, transform: 'translateX(-50%)' }}
                      title={`Your Price: ${formatCurrency(currentPrice!)}`}
                    />
                  )}
                </div>
                {percentile !== null && (
                  <p className="text-center text-sm">
                    Your Price: <span className="font-semibold">{formatCurrency(currentPrice!)}</span>
                    {' '}({percentile.toFixed(0)}th percentile)
                  </p>
                )}
              </div>
            </div>
          ) : (
            <p className="text-muted-foreground text-center py-4">
              No comparable contract data available
            </p>
          )}
        </CardContent>
      </Card>

      {/* Pricing Trends */}
      {trendsData?.trends && trendsData.trends.length > 0 && (
        <Card>
          <CardHeader className="py-4">
            <CardTitle className="text-lg flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              Pricing Trends
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trendsData.trends}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="year" />
                  <YAxis
                    tickFormatter={(value) => formatCompactCurrency(value)}
                  />
                  <Tooltip
                    formatter={(value: number) => formatCurrency(value)}
                    labelFormatter={(label) => `Year: ${label}`}
                  />
                  <Line
                    type="monotone"
                    dataKey="award_amount.median"
                    name="Median Award"
                    stroke="#3b82f6"
                    strokeWidth={2}
                    dot={{ fill: '#3b82f6' }}
                  />
                  <Line
                    type="monotone"
                    dataKey="award_amount.mean"
                    name="Average Award"
                    stroke="#10b981"
                    strokeWidth={2}
                    strokeDasharray="5 5"
                    dot={{ fill: '#10b981' }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
            {trendsData.yoy_change !== null && (
              <div className="flex items-center justify-center mt-4 gap-2">
                <TrendingUp
                  className={`h-4 w-4 ${
                    trendsData.yoy_change >= 0 ? 'text-green-500' : 'text-red-500'
                  }`}
                />
                <span className="text-sm">
                  {trendsData.yoy_change >= 0 ? '+' : ''}
                  {trendsData.yoy_change.toFixed(1)}% year-over-year change
                </span>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Agency Insights */}
      {data?.agency_insights && (
        <Card>
          <CardHeader className="py-4">
            <CardTitle className="text-lg flex items-center gap-2">
              <Building2 className="h-5 w-5" />
              Agency Insights
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center p-4 bg-muted rounded-lg">
                <p className="text-2xl font-bold">
                  {formatCompactCurrency(data.agency_insights.average_award)}
                </p>
                <p className="text-sm text-muted-foreground">Avg Award</p>
              </div>
              <div className="text-center p-4 bg-muted rounded-lg">
                <p className="text-2xl font-bold">
                  {data.agency_insights.contract_count}
                </p>
                <p className="text-sm text-muted-foreground">Contracts</p>
              </div>
              <div className="text-center p-4 bg-muted rounded-lg">
                <p className="text-2xl font-bold">
                  {data.agency_insights.typical_duration}
                </p>
                <p className="text-sm text-muted-foreground">Typical Duration</p>
              </div>
              <div className="text-center p-4 bg-muted rounded-lg">
                <p className="text-2xl font-bold">
                  {data.agency_insights.budget_peak}
                </p>
                <p className="text-sm text-muted-foreground">Budget Peak</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Comparable Contracts Table */}
      {data?.similar_contracts && data.similar_contracts.length > 0 && (
        <Card>
          <CardHeader className="py-4">
            <CardTitle className="text-lg">Comparable Contracts</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Contract</TableHead>
                  <TableHead>Agency</TableHead>
                  <TableHead className="text-right">Award</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead className="text-right">Relevance</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.similar_contracts.slice(0, 10).map((contract: SimilarContract, index: number) => (
                  <TableRow key={index}>
                    <TableCell className="max-w-[250px]">
                      <span className="line-clamp-2">{contract.title}</span>
                    </TableCell>
                    <TableCell>{contract.agency}</TableCell>
                    <TableCell className="text-right font-medium">
                      {formatCurrency(contract.award_amount)}
                    </TableCell>
                    <TableCell>{contract.date || '—'}</TableCell>
                    <TableCell className="text-right">
                      <Badge
                        variant="secondary"
                        className={
                          contract.similarity >= 0.9
                            ? 'bg-green-100 text-green-800'
                            : contract.similarity >= 0.7
                            ? 'bg-yellow-100 text-yellow-800'
                            : 'bg-gray-100 text-gray-800'
                        }
                      >
                        {(contract.similarity * 100).toFixed(0)}%
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
