import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Slider } from '@/components/ui/slider';
import { Skeleton } from '@/components/ui/skeleton';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import {
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  Sparkles,
  Target,
} from 'lucide-react';
import { api } from '@/services/api';
import type { StrategyRecommendation } from '@/types/pricing';

interface AIRecommendationsProps {
  rfpId: string;
  currentPricing?: { total_price?: number; base_cost?: number } | null;
  onApplyRecommendation: (price: number, strategy: string) => void;
}

const STRATEGY_LABELS: Record<string, { label: string; description: string }> = {
  aggressive: {
    label: 'Aggressive',
    description: 'Lower price to maximize win probability',
  },
  competitive: {
    label: 'Competitive',
    description: 'Balanced approach for competitive bids',
  },
  value_based: {
    label: 'Value-Based',
    description: 'Price based on delivered value',
  },
  cost_plus: {
    label: 'Cost-Plus',
    description: 'Standard markup over costs',
  },
};

export function AIRecommendations({
  rfpId,
  currentPricing,
  onApplyRecommendation,
}: AIRecommendationsProps) {
  const [targetWinProb, setTargetWinProb] = useState(70);

  const {
    data,
    isLoading,
    error,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ['ai-recommendation', rfpId, targetWinProb],
    queryFn: () =>
      api.getAIRecommendation(rfpId, currentPricing?.total_price, targetWinProb / 100),
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

  const getRiskColor = (level: string) => {
    switch (level) {
      case 'Low':
        return 'bg-green-100 text-green-800';
      case 'Medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'High':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  if (error) {
    return (
      <Card>
        <CardContent className="py-8 text-center">
          <p className="text-muted-foreground">Failed to load AI recommendations</p>
          <Button variant="outline" onClick={() => refetch()} className="mt-4">
            <RefreshCw className="h-4 w-4 mr-2" />
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Optimal Price Recommendation */}
      <Card className="border-2 border-blue-200 bg-blue-50/30">
        <CardHeader className="flex flex-row items-center justify-between py-4">
          <CardTitle className="text-lg flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-blue-500" />
            AI Recommended Price
          </CardTitle>
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isFetching}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${isFetching ? 'animate-spin' : ''}`} />
            Regenerate
          </Button>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-4">
              <Skeleton className="h-12 w-48" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
            </div>
          ) : data?.optimal ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-4xl font-bold text-blue-600">
                    {formatCurrency(data.optimal.price)}
                  </p>
                  <p className="text-sm text-muted-foreground mt-1">
                    Strategy: {STRATEGY_LABELS[data.optimal.strategy]?.label || data.optimal.strategy}
                  </p>
                </div>
                <div className="text-right">
                  <div className="flex items-center gap-2 justify-end">
                    <span className="text-sm text-muted-foreground">Confidence</span>
                    <Badge variant="secondary" className="text-lg px-3 py-1">
                      {(data.optimal.confidence * 100).toFixed(0)}%
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground mt-1">
                    Margin: {data.optimal.margin.toFixed(1)}%
                  </p>
                </div>
              </div>

              {data.optimal.reasoning && data.optimal.reasoning.length > 0 && (
                <div className="bg-white rounded-lg p-4 space-y-2">
                  <p className="text-sm font-medium">Why this price?</p>
                  <ul className="text-sm text-muted-foreground space-y-1">
                    {data.optimal.reasoning.map((reason: string, index: number) => (
                      <li key={index} className="flex items-start gap-2">
                        <span className="text-blue-500 mt-0.5">•</span>
                        {reason}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <Button
                className="w-full"
                onClick={() => onApplyRecommendation(data.optimal.price, data.optimal.strategy)}
              >
                <CheckCircle2 className="h-4 w-4 mr-2" />
                Apply This Price
              </Button>
            </div>
          ) : (
            <p className="text-muted-foreground">No recommendation available</p>
          )}
        </CardContent>
      </Card>

      {/* Strategy Comparison */}
      <Card>
        <CardHeader className="py-4">
          <CardTitle className="text-lg">Alternative Strategies</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[1, 2, 3, 4].map((i) => (
                <Skeleton key={i} className="h-40" />
              ))}
            </div>
          ) : data?.strategies ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {(Object.entries(data.strategies) as [string, StrategyRecommendation][]).map(([strategyName, strategy]) => {
                const isOptimal = strategyName === data.optimal?.strategy;
                const strategyInfo = STRATEGY_LABELS[strategyName] || { label: strategyName, description: '' };

                return (
                  <Card
                    key={strategyName}
                    className={`cursor-pointer transition-all hover:shadow-md ${
                      isOptimal ? 'ring-2 ring-blue-500 bg-blue-50/50' : ''
                    }`}
                    onClick={() => onApplyRecommendation(strategy.price, strategyName)}
                  >
                    <CardContent className="pt-4 text-center space-y-2">
                      <p className="text-xs font-semibold uppercase text-muted-foreground">
                        {strategyInfo.label}
                      </p>
                      <p className="text-xl font-bold">
                        {formatCurrency(strategy.price)}
                      </p>
                      {isOptimal && (
                        <Badge className="bg-blue-500">Optimal</Badge>
                      )}
                      <div className="space-y-1 text-sm">
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Win Prob</span>
                          <span className="font-medium">
                            {(strategy.win_probability * 100).toFixed(0)}%
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Margin</span>
                          <span className="font-medium">
                            {strategy.margin.toFixed(1)}%
                          </span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-muted-foreground">Risk</span>
                          <Badge
                            variant="secondary"
                            className={`text-xs ${getRiskColor(strategy.risk_level)}`}
                          >
                            {strategy.risk_level}
                          </Badge>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          ) : null}
        </CardContent>
      </Card>

      {/* What-If Scenario */}
      <Card>
        <CardHeader className="py-4">
          <CardTitle className="text-lg flex items-center gap-2">
            <Target className="h-5 w-5" />
            Win Probability Target
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <div className="flex justify-between">
              <span>Target Win Probability</span>
              <span className="font-medium">{targetWinProb}%</span>
            </div>
            <Slider
              value={[targetWinProb]}
              onValueChange={([v]) => setTargetWinProb(v)}
              min={40}
              max={90}
              step={5}
            />
          </div>

          {data?.price_to_win && (
            <div className="bg-muted rounded-lg p-4 space-y-2">
              <div className="flex justify-between">
                <span>Maximum Price at {targetWinProb}%:</span>
                <span className="font-bold">
                  {formatCurrency(data.price_to_win.maximum_price)}
                </span>
              </div>
              <div className="flex justify-between text-sm text-muted-foreground">
                <span>Expected Margin:</span>
                <span>{data.price_to_win.expected_margin?.toFixed(1) || '—'}%</span>
              </div>
            </div>
          )}

          {/* Win/Price Curve */}
          {data?.win_price_curve && data.win_price_curve.length > 0 && (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data.win_price_curve}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="price"
                    tickFormatter={(value) =>
                      `$${(value / 1000).toFixed(0)}K`
                    }
                    label={{ value: 'Price', position: 'bottom', offset: -5 }}
                  />
                  <YAxis
                    tickFormatter={(value) => `${(value * 100).toFixed(0)}%`}
                    domain={[0, 1]}
                    label={{
                      value: 'Win Probability',
                      angle: -90,
                      position: 'insideLeft',
                    }}
                  />
                  <Tooltip
                    formatter={(value: number) => [
                      `${(value * 100).toFixed(0)}%`,
                      'Win Probability',
                    ]}
                    labelFormatter={(label) => `Price: ${formatCurrency(label)}`}
                  />
                  <Line
                    type="monotone"
                    dataKey="probability"
                    stroke="#3b82f6"
                    strokeWidth={2}
                    dot={{ fill: '#3b82f6' }}
                  />
                  {currentPricing?.total_price && (
                    <ReferenceLine
                      x={currentPricing.total_price}
                      stroke="#10b981"
                      strokeDasharray="5 5"
                      label="Current"
                    />
                  )}
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Risk Assessment */}
      {data?.risk_factors && data.risk_factors.length > 0 && (
        <Card>
          <CardHeader className="py-4">
            <CardTitle className="text-lg flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" />
              Risk Factors
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {data.risk_factors.map((risk: string, index: number) => (
                <li
                  key={index}
                  className="flex items-start gap-2 text-sm p-2 rounded bg-yellow-50"
                >
                  <AlertTriangle className="h-4 w-4 text-yellow-600 mt-0.5 shrink-0" />
                  <span>{risk}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
