import { Card, CardContent } from '@/components/ui/card';
import { DollarSign, TrendingUp, Percent, Target } from 'lucide-react';

interface PricingSummaryCardsProps {
  totalPrice?: number | null;
  baseCost?: number | null;
  margin?: number | null;
  winProbability?: number | null;
  isLoading?: boolean;
}

export function PricingSummaryCards({
  totalPrice,
  baseCost,
  margin,
  winProbability,
  isLoading = false,
}: PricingSummaryCardsProps) {
  const formatCurrency = (amount: number | null | undefined) => {
    if (amount == null) return '—';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const formatPercent = (value: number | null | undefined) => {
    if (value == null) return '—';
    return `${value.toFixed(1)}%`;
  };

  const cards = [
    {
      title: 'Total Price',
      value: formatCurrency(totalPrice),
      icon: DollarSign,
      color: 'text-green-600',
      bgColor: 'bg-green-50',
    },
    {
      title: 'Base Cost',
      value: formatCurrency(baseCost),
      icon: TrendingUp,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
    },
    {
      title: 'Target Margin',
      value: formatPercent(margin),
      icon: Percent,
      color: 'text-purple-600',
      bgColor: 'bg-purple-50',
    },
    {
      title: 'Win Probability',
      value: winProbability != null ? `${(winProbability * 100).toFixed(0)}%` : '—',
      icon: Target,
      color: 'text-orange-600',
      bgColor: 'bg-orange-50',
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((card) => (
        <Card key={card.title}>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">
                  {card.title}
                </p>
                <p className={`text-2xl font-bold ${isLoading ? 'animate-pulse' : ''}`}>
                  {isLoading ? '...' : card.value}
                </p>
              </div>
              <div className={`p-3 rounded-full ${card.bgColor}`}>
                <card.icon className={`h-6 w-6 ${card.color}`} />
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
