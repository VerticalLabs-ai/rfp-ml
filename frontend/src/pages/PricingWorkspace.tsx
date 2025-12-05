import { useState, useEffect, useCallback } from 'react';
import { useParams, useSearchParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import {
  ArrowLeft,
  Save,
  Download,
  Calculator,
  TrendingUp,
  Sparkles,
  Target,
  Gamepad2,
  FileText,
} from 'lucide-react';
import { toast } from 'sonner';
import { api } from '@/services/api';
import { CostBuilder } from '@/components/pricing/CostBuilder';
import { MarketIntelligence } from '@/components/pricing/MarketIntelligence';
import { AIRecommendations } from '@/components/pricing/AIRecommendations';
import { PTWAnalysis } from '@/components/pricing/PTWAnalysis';
import { ScenarioModeler } from '@/components/pricing/ScenarioModeler';
import { PricingSummaryCards } from '@/components/pricing/PricingSummaryCards';
import { SimilarContractsSidebar } from '@/components/pricing/SimilarContractsSidebar';
import { ProposalPricingIntegration } from '@/components/pricing/ProposalPricingIntegration';
import type { CostBreakdown } from '@/types/pricing';

export default function PricingWorkspace() {
  const { rfpId } = useParams<{ rfpId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState(searchParams.get('tab') || 'cost-builder');
  const [costBreakdown, setCostBreakdown] = useState<CostBreakdown | null>(null);
  const [isDirty, setIsDirty] = useState(false);
  const [showSidebar, setShowSidebar] = useState(true);

  // Fetch RFP details
  const { data: rfp, isLoading: rfpLoading } = useQuery({
    queryKey: ['rfp', rfpId],
    queryFn: () => api.getRFP(rfpId!),
    enabled: !!rfpId,
  });

  // Fetch existing pricing result
  const { data: pricing, isLoading: pricingLoading } = useQuery({
    queryKey: ['pricing-result', rfpId],
    queryFn: () => api.getPricingResult(rfpId!).catch(() => null),
    enabled: !!rfpId,
  });

  // Save cost breakdown mutation
  const saveMutation = useMutation({
    mutationFn: (breakdown: CostBreakdown) =>
      api.saveCostBreakdown(rfpId!, breakdown),
    onSuccess: () => {
      setIsDirty(false);
      queryClient.invalidateQueries({ queryKey: ['pricing-result', rfpId] });
      toast.success('Pricing saved successfully');
    },
    onError: () => {
      toast.error('Failed to save pricing');
    },
  });

  // Update URL when tab changes
  useEffect(() => {
    const currentTab = searchParams.get('tab');
    if (currentTab !== activeTab) {
      setSearchParams({ tab: activeTab });
    }
  }, [activeTab, searchParams, setSearchParams]);

  // Initialize cost breakdown from existing pricing
  useEffect(() => {
    if (pricing?.price_breakdown && !costBreakdown) {
      const breakdown: CostBreakdown = {
        labor: pricing.price_breakdown.labor?.items?.map((item: any, idx: number) => ({
          id: `labor-${idx}`,
          role: item.role || 'Developer',
          hours: item.hours || 0,
          ratePerHour: item.rate_per_hour || 0,
        })) || [],
        materials: pricing.price_breakdown.materials?.items?.map((item: any, idx: number) => ({
          id: `material-${idx}`,
          description: item.description || 'Item',
          quantity: item.quantity || 0,
          unitPrice: item.unit_price || 0,
          unit: item.unit || 'each',
        })) || [],
        subcontractors: pricing.price_breakdown.subcontractors?.items?.map((item: any, idx: number) => ({
          id: `sub-${idx}`,
          vendor: item.vendor || 'Vendor',
          scope: item.scope || 'TBD',
          quoteAmount: item.quote_amount || 0,
        })) || [],
        overhead: {
          overheadRate: pricing.price_breakdown.overhead
            ? (pricing.price_breakdown.overhead / pricing.base_cost) * 100
            : 15,
          gaRate: pricing.price_breakdown.ga
            ? (pricing.price_breakdown.ga / pricing.base_cost) * 100
            : 8,
          profitMargin: pricing.margin_percentage || 12,
        },
      };
      setCostBreakdown(breakdown);
    }
  }, [pricing, costBreakdown]);

  const handleCostUpdate = useCallback((data: CostBreakdown) => {
    setCostBreakdown(data);
    setIsDirty(true);
  }, []);

  const handleSave = () => {
    if (costBreakdown) {
      saveMutation.mutate(costBreakdown);
    }
  };

  const handleApplyRecommendation = (price: number, strategy: string) => {
    toast.success(`Applied ${strategy} strategy: ${price.toLocaleString('en-US', { style: 'currency', currency: 'USD' })}`);
    // Could update cost breakdown to achieve target price
    queryClient.invalidateQueries({ queryKey: ['pricing-result', rfpId] });
  };

  const handlePriceChange = (price: number) => {
    toast.info(`Selected price point: ${price.toLocaleString('en-US', { style: 'currency', currency: 'USD' })}`);
  };

  const handleExport = async (format: 'json' | 'csv' | 'pdf') => {
    try {
      if (format === 'csv') {
        const blob = await api.downloadPricingTableCSV(rfpId!);
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `pricing_${rfpId}_${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        URL.revokeObjectURL(url);
        toast.success('CSV downloaded');
      } else {
        toast.info(`${format.toUpperCase()} export coming soon`);
      }
    } catch (error) {
      toast.error('Export failed');
    }
  };

  // Calculate current totals from cost breakdown
  const currentTotals = costBreakdown ? (() => {
    const laborTotal = costBreakdown.labor.reduce((sum, item) => sum + item.hours * item.ratePerHour, 0);
    const materialsTotal = costBreakdown.materials.reduce((sum, item) => sum + item.quantity * item.unitPrice, 0);
    const subcontractorTotal = costBreakdown.subcontractors.reduce((sum, item) => sum + item.quoteAmount, 0);
    const directCosts = laborTotal + materialsTotal + subcontractorTotal;
    const overheadAmount = directCosts * (costBreakdown.overhead.overheadRate / 100);
    const gaAmount = (directCosts + overheadAmount) * (costBreakdown.overhead.gaRate / 100);
    const subtotalBeforeProfit = directCosts + overheadAmount + gaAmount;
    const profitAmount = subtotalBeforeProfit * (costBreakdown.overhead.profitMargin / 100);
    const totalPrice = subtotalBeforeProfit + profitAmount;

    return { totalPrice, directCosts, margin: costBreakdown.overhead.profitMargin };
  })() : null;

  const isLoading = rfpLoading || pricingLoading;

  return (
    <div className="flex h-[calc(100vh-180px)]">
      {/* Main Content */}
      <div className="flex-1 overflow-auto">
        <div className="p-6 space-y-6">
          {/* Header */}
          <header className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link to={`/rfps/${rfpId}`}>
                <Button variant="ghost" size="sm">
                  <ArrowLeft className="h-4 w-4 mr-2" />
                  Back to RFP
                </Button>
              </Link>
              <div>
                <h1 className="text-2xl font-bold">Pricing Workspace</h1>
                {isLoading ? (
                  <Skeleton className="h-4 w-64 mt-1" />
                ) : (
                  <p className="text-muted-foreground truncate max-w-lg">
                    {rfp?.title}
                  </p>
                )}
              </div>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowSidebar(!showSidebar)}
              >
                {showSidebar ? 'Hide' : 'Show'} Similar
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleExport('csv')}
              >
                <Download className="h-4 w-4 mr-2" />
                Export CSV
              </Button>
              <Button
                size="sm"
                onClick={handleSave}
                disabled={!isDirty || saveMutation.isPending}
              >
                <Save className="h-4 w-4 mr-2" />
                {saveMutation.isPending ? 'Saving...' : 'Save'}
              </Button>
            </div>
          </header>

          {/* Summary Cards */}
          <PricingSummaryCards
            totalPrice={currentTotals?.totalPrice ?? pricing?.total_price}
            baseCost={currentTotals?.directCosts ?? pricing?.base_cost}
            margin={currentTotals?.margin ?? pricing?.margin_percentage}
            winProbability={pricing?.confidence_score}
            isLoading={isLoading}
          />

          {/* Tabbed Interface */}
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="grid w-full grid-cols-6">
              <TabsTrigger value="cost-builder" className="flex items-center gap-2">
                <Calculator className="h-4 w-4" />
                <span className="hidden sm:inline">Cost Builder</span>
              </TabsTrigger>
              <TabsTrigger value="market-intel" className="flex items-center gap-2">
                <TrendingUp className="h-4 w-4" />
                <span className="hidden sm:inline">Market Intel</span>
              </TabsTrigger>
              <TabsTrigger value="ai-recommend" className="flex items-center gap-2">
                <Sparkles className="h-4 w-4" />
                <span className="hidden sm:inline">AI Recommend</span>
              </TabsTrigger>
              <TabsTrigger value="ptw-analysis" className="flex items-center gap-2">
                <Target className="h-4 w-4" />
                <span className="hidden sm:inline">PTW Analysis</span>
              </TabsTrigger>
              <TabsTrigger value="scenarios" className="flex items-center gap-2">
                <Gamepad2 className="h-4 w-4" />
                <span className="hidden sm:inline">Scenarios</span>
              </TabsTrigger>
              <TabsTrigger value="proposal" className="flex items-center gap-2">
                <FileText className="h-4 w-4" />
                <span className="hidden sm:inline">Proposal</span>
              </TabsTrigger>
            </TabsList>

            <div className="mt-6">
              <TabsContent value="cost-builder">
                <CostBuilder
                  rfpId={rfpId!}
                  initialData={costBreakdown}
                  onUpdate={handleCostUpdate}
                />
              </TabsContent>

              <TabsContent value="market-intel">
                <MarketIntelligence
                  rfpId={rfpId!}
                  naicsCode={rfp?.naics_code}
                  currentPrice={currentTotals?.totalPrice ?? pricing?.total_price}
                />
              </TabsContent>

              <TabsContent value="ai-recommend">
                <AIRecommendations
                  rfpId={rfpId!}
                  currentPricing={pricing}
                  onApplyRecommendation={handleApplyRecommendation}
                />
              </TabsContent>

              <TabsContent value="ptw-analysis">
                <PTWAnalysis
                  rfpId={rfpId!}
                  currentPrice={currentTotals?.totalPrice ?? pricing?.total_price}
                  onPriceChange={handlePriceChange}
                />
              </TabsContent>

              <TabsContent value="scenarios">
                <ScenarioModeler rfpId={rfpId!} basePricing={pricing} />
              </TabsContent>

              <TabsContent value="proposal">
                <ProposalPricingIntegration rfpId={rfpId!} />
              </TabsContent>
            </div>
          </Tabs>
        </div>
      </div>

      {/* Sidebar */}
      {showSidebar && (
        <SimilarContractsSidebar
          rfpId={rfpId!}
          naicsCode={rfp?.naics_code}
          agency={rfp?.agency}
        />
      )}
    </div>
  );
}
