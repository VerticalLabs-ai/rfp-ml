import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { Skeleton } from '@/components/ui/skeleton';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { RefreshCw, Gamepad2, TrendingUp } from 'lucide-react';
import { api } from '@/services/api';
import type { ScenarioParams, ScenarioResult } from '@/types/pricing';

interface ScenarioModelerProps {
  rfpId: string;
  basePricing?: { total_price?: number; base_cost?: number } | null;
}

const DEFAULT_PARAMS: ScenarioParams = {
  labor_cost_multiplier: 1.0,
  material_cost_multiplier: 1.0,
  risk_contingency_percent: 0,
  desired_margin: 0,
};

export function ScenarioModeler({ rfpId }: ScenarioModelerProps) {
  const [params, setParams] = useState<ScenarioParams>(DEFAULT_PARAMS);

  const {
    data,
    isLoading,
    error,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ['pricing-scenarios', rfpId, params],
    queryFn: () => api.runPricingScenarios(rfpId, params),
    enabled: !!rfpId,
    staleTime: 1 * 60 * 1000,
  });

  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);

  const updateParams = (key: keyof ScenarioParams, value: number) => {
    setParams((prev) => ({ ...prev, [key]: value }));
  };

  const resetParams = () => {
    setParams(DEFAULT_PARAMS);
  };

  // Prepare chart data
  const chartData = data?.scenarios
    ? data.scenarios.map((scenario: ScenarioResult) => ({
        name: scenario.scenario_name,
        cost: scenario.base_cost,
        profit: scenario.profit,
        total: scenario.total_price,
      }))
    : [];

  if (error) {
    return (
      <Card>
        <CardContent className="py-8 text-center">
          <p className="text-muted-foreground">Failed to load scenarios</p>
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
      {/* Scenario Controls */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between py-4">
          <CardTitle className="text-lg flex items-center gap-2">
            <Gamepad2 className="h-5 w-5" />
            War Gaming Parameters
          </CardTitle>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={resetParams}>
              Reset
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetch()}
              disabled={isFetching}
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${isFetching ? 'animate-spin' : ''}`} />
              Run Scenarios
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-sm font-medium">Labor Cost Multiplier</span>
                <span className="text-sm text-muted-foreground">
                  {params.labor_cost_multiplier.toFixed(2)}x
                </span>
              </div>
              <Slider
                value={[params.labor_cost_multiplier]}
                onValueChange={([v]) => updateParams('labor_cost_multiplier', v)}
                min={0.8}
                max={1.5}
                step={0.05}
              />
              <p className="text-xs text-muted-foreground">
                Adjust labor costs (0.8x = 20% lower, 1.5x = 50% higher)
              </p>
            </div>

            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-sm font-medium">Material Cost Multiplier</span>
                <span className="text-sm text-muted-foreground">
                  {params.material_cost_multiplier.toFixed(2)}x
                </span>
              </div>
              <Slider
                value={[params.material_cost_multiplier]}
                onValueChange={([v]) => updateParams('material_cost_multiplier', v)}
                min={0.8}
                max={1.5}
                step={0.05}
              />
              <p className="text-xs text-muted-foreground">
                Adjust material costs (0.8x = 20% lower, 1.5x = 50% higher)
              </p>
            </div>

            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-sm font-medium">Risk Contingency</span>
                <span className="text-sm text-muted-foreground">
                  {params.risk_contingency_percent}%
                </span>
              </div>
              <Slider
                value={[params.risk_contingency_percent]}
                onValueChange={([v]) => updateParams('risk_contingency_percent', v)}
                min={0}
                max={30}
                step={1}
              />
              <p className="text-xs text-muted-foreground">
                Additional buffer for unexpected costs
              </p>
            </div>

            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-sm font-medium">Target Margin Override</span>
                <span className="text-sm text-muted-foreground">
                  {params.desired_margin === 0 ? 'Default' : `${params.desired_margin}%`}
                </span>
              </div>
              <Slider
                value={[params.desired_margin]}
                onValueChange={([v]) => updateParams('desired_margin', v)}
                min={0}
                max={50}
                step={1}
              />
              <p className="text-xs text-muted-foreground">
                Override default margin (0 = use strategy default)
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Scenario Comparison Chart */}
      <Card>
        <CardHeader className="py-4">
          <CardTitle className="text-lg flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            Scenario Comparison
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-72 w-full" />
          ) : chartData.length > 0 ? (
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis
                    tickFormatter={(value) =>
                      `$${(value / 1000).toFixed(0)}K`
                    }
                  />
                  <Tooltip
                    formatter={(value: number, name: string) => [
                      formatCurrency(value),
                      name === 'cost' ? 'Base Cost' : name === 'profit' ? 'Profit' : 'Total',
                    ]}
                  />
                  <Legend />
                  <Bar dataKey="cost" name="Base Cost" stackId="a" fill="#94a3b8" />
                  <Bar dataKey="profit" name="Profit" stackId="a" fill="#22c55e" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="text-muted-foreground text-center py-8">
              Adjust parameters and click "Run Scenarios" to see comparison
            </p>
          )}
        </CardContent>
      </Card>

      {/* Scenario Details */}
      {data?.scenarios && data.scenarios.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {data.scenarios.map((scenario: ScenarioResult, index: number) => (
            <Card key={index}>
              <CardHeader className="py-3">
                <CardTitle className="text-sm font-medium">
                  {scenario.scenario_name}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="text-center">
                  <p className="text-2xl font-bold text-green-600">
                    {formatCurrency(scenario.total_price)}
                  </p>
                  <p className="text-sm text-muted-foreground">Total Price</p>
                </div>

                <div className="space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Base Cost</span>
                    <span>{formatCurrency(scenario.base_cost)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Profit</span>
                    <span className="text-green-600">
                      {formatCurrency(scenario.profit)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Margin</span>
                    <span>{scenario.margin_percentage.toFixed(1)}%</span>
                  </div>
                </div>

                {scenario.price_breakdown && (
                  <div className="pt-2 border-t space-y-1 text-xs text-muted-foreground">
                    <div className="flex justify-between">
                      <span>Labor</span>
                      <span>{formatCurrency(scenario.price_breakdown.labor)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Materials</span>
                      <span>{formatCurrency(scenario.price_breakdown.materials)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Overhead</span>
                      <span>{formatCurrency(scenario.price_breakdown.overhead)}</span>
                    </div>
                    {scenario.price_breakdown.contingency > 0 && (
                      <div className="flex justify-between">
                        <span>Contingency</span>
                        <span>{formatCurrency(scenario.price_breakdown.contingency)}</span>
                      </div>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Recommendation */}
      {data?.recommendation && (
        <Card className="bg-blue-50 border-blue-200">
          <CardContent className="py-4">
            <div className="flex items-start gap-3">
              <div className="p-2 bg-blue-100 rounded-full">
                <TrendingUp className="h-5 w-5 text-blue-600" />
              </div>
              <div>
                <p className="font-medium text-blue-900">Recommendation</p>
                <p className="text-sm text-blue-700">{data.recommendation}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
