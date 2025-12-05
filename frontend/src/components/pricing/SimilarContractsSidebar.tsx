import { useQuery } from '@tanstack/react-query';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { FileText, Building2, Calendar, TrendingUp } from 'lucide-react';
import { api } from '@/services/api';

interface SimilarContractsSidebarProps {
  rfpId: string;
  naicsCode?: string | null;
  agency?: string | null;
}

interface SimilarContract {
  title: string;
  agency: string;
  award_amount: number;
  date: string;
  similarity: number;
  naics_code?: string;
}

export function SimilarContractsSidebar({
  rfpId,
  naicsCode,
}: SimilarContractsSidebarProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['market-intelligence', rfpId],
    queryFn: () => api.getMarketIntelligence(rfpId),
    enabled: !!rfpId,
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  });

  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);

  const formatRelevance = (similarity: number) => {
    const percent = Math.round(similarity * 100);
    if (percent >= 90) return { label: 'High', color: 'bg-green-100 text-green-800' };
    if (percent >= 70) return { label: 'Medium', color: 'bg-yellow-100 text-yellow-800' };
    return { label: 'Low', color: 'bg-gray-100 text-gray-800' };
  };

  if (error) {
    return (
      <aside className="w-80 border-l bg-muted/20 p-4">
        <p className="text-sm text-muted-foreground">
          Failed to load similar contracts
        </p>
      </aside>
    );
  }

  return (
    <aside className="w-80 border-l bg-muted/20 overflow-hidden flex flex-col">
      <div className="p-4 border-b">
        <h3 className="font-semibold flex items-center gap-2">
          <FileText className="h-4 w-4" />
          Similar Contracts
        </h3>
        {naicsCode && (
          <p className="text-xs text-muted-foreground mt-1">
            NAICS: {naicsCode}
          </p>
        )}
      </div>

      <ScrollArea className="flex-1 p-4">
        <div className="space-y-3">
          {isLoading ? (
            Array.from({ length: 5 }).map((_, i) => (
              <Card key={i} className="p-3">
                <Skeleton className="h-4 w-3/4 mb-2" />
                <Skeleton className="h-3 w-1/2 mb-1" />
                <Skeleton className="h-3 w-1/3" />
              </Card>
            ))
          ) : data?.similar_contracts?.length > 0 ? (
            data.similar_contracts.map((contract: SimilarContract, index: number) => {
              const relevance = formatRelevance(contract.similarity);
              return (
                <Card key={index} className="p-3 hover:bg-muted/50 transition-colors">
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <h4 className="text-sm font-medium line-clamp-2">
                      {contract.title}
                    </h4>
                    <Badge variant="secondary" className={`shrink-0 text-xs ${relevance.color}`}>
                      {Math.round(contract.similarity * 100)}%
                    </Badge>
                  </div>
                  <div className="space-y-1 text-xs text-muted-foreground">
                    <div className="flex items-center gap-1">
                      <Building2 className="h-3 w-3" />
                      <span className="truncate">{contract.agency}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <TrendingUp className="h-3 w-3" />
                      <span className="font-medium text-foreground">
                        {formatCurrency(contract.award_amount)}
                      </span>
                    </div>
                    {contract.date && (
                      <div className="flex items-center gap-1">
                        <Calendar className="h-3 w-3" />
                        <span>{contract.date}</span>
                      </div>
                    )}
                  </div>
                </Card>
              );
            })
          ) : (
            <p className="text-sm text-muted-foreground text-center py-4">
              No similar contracts found
            </p>
          )}
        </div>
      </ScrollArea>

      {data?.award_range && (
        <div className="p-4 border-t bg-muted/30">
          <h4 className="text-xs font-semibold text-muted-foreground uppercase mb-2">
            Award Range
          </h4>
          <div className="space-y-1 text-sm">
            <div className="flex justify-between">
              <span>Median</span>
              <span className="font-medium">{formatCurrency(data.award_range.median)}</span>
            </div>
            <div className="flex justify-between text-muted-foreground">
              <span>Range</span>
              <span>
                {formatCurrency(data.award_range.min)} - {formatCurrency(data.award_range.max)}
              </span>
            </div>
            <div className="flex justify-between text-muted-foreground">
              <span>Sample Size</span>
              <span>{data.award_range.count} contracts</span>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
