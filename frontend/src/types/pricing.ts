// Pricing Types for the Pricing Workspace

// Cost Builder Types
export interface LaborLineItem {
  id: string;
  role: string;
  hours: number;
  ratePerHour: number;
}

export interface MaterialLineItem {
  id: string;
  description: string;
  quantity: number;
  unitPrice: number;
  unit: 'each' | 'monthly' | 'annual';
}

export interface SubcontractorQuote {
  id: string;
  vendor: string;
  scope: string;
  quoteAmount: number;
}

export interface OverheadConfig {
  overheadRate: number;
  gaRate: number;
  profitMargin: number;
}

export interface CostBreakdown {
  labor: LaborLineItem[];
  materials: MaterialLineItem[];
  subcontractors: SubcontractorQuote[];
  overhead: OverheadConfig;
}

// Pricing Result Types
export interface PriceBreakdownComponent {
  items?: { role?: string; hours?: number; rate_per_hour?: number; description?: string; quantity?: number; unit_price?: number; vendor?: string; scope?: string; quote_amount?: number }[];
  total: number;
}

export interface PricingResult {
  id: number;
  rfp_id: number;
  total_price: number;
  base_cost: number;
  margin_percentage: number;
  pricing_strategy: string;
  competitive_score: number;
  confidence_score: number;
  price_breakdown: {
    labor?: PriceBreakdownComponent;
    materials?: PriceBreakdownComponent;
    subcontractors?: PriceBreakdownComponent;
    overhead?: number;
    ga?: number;
    profit?: number;
  };
  risk_factors: string[];
  justification: string;
  created_at: string;
  updated_at: string;
}

// Market Intelligence Types
export interface AwardRange {
  min: number;
  p25: number;
  median: number;
  p75: number;
  max: number;
  count: number;
}

export interface SimilarContract {
  title: string;
  agency: string;
  award_amount: number;
  date: string;
  similarity: number;
  naics_code?: string;
}

export interface NAICSStats {
  naics_code: string;
  count: number;
  mean: number;
  median: number;
  std: number;
  min: number;
  max: number;
}

export interface CategoryStats {
  category: string;
  count: number;
  avg_price: number;
  median_price: number;
}

export interface AgencyInsights {
  average_award: number;
  contract_count: number;
  typical_duration: string;
  budget_peak: string;
}

export interface MarketIntelligenceData {
  naics_stats: NAICSStats | null;
  category_stats: CategoryStats | null;
  award_range: AwardRange | null;
  similar_contracts: SimilarContract[];
  agency_insights: AgencyInsights | null;
  analysis_date: string;
}

// AI Recommendations Types
export interface StrategyRecommendation {
  price: number;
  margin: number;
  confidence: number;
  win_probability: number;
  risk_level: 'Low' | 'Medium' | 'High';
}

export interface OptimalRecommendation {
  strategy: string;
  price: number;
  confidence: number;
  margin: number;
  reasoning: string[];
}

export interface WinPriceCurvePoint {
  probability: number;
  price: number;
}

export interface AIRecommendationData {
  optimal: OptimalRecommendation;
  strategies: Record<string, StrategyRecommendation>;
  price_to_win: {
    target_probability: number;
    maximum_price: number;
    expected_margin: number;
  };
  win_price_curve: WinPriceCurvePoint[];
  risk_factors: string[];
}

// Price-to-Win Types
export interface CompetitorEstimates {
  expected_bidders: string;
  low_bidder: number;
  average: number;
  high_bidder: number;
}

export interface MinimumViable {
  absolute_floor: number;
  minimum_margin: number;
  recommended_floor: number;
}

export interface MarginImpactRow {
  price: number;
  margin_percent: number;
  profit: number;
  win_probability: number;
  risk_assessment: string;
}

export interface RiskAssessment {
  score: number;
  level: 'Low' | 'Medium' | 'High';
  factors: string[];
}

export interface PTWAnalysisData {
  competitor_estimates: CompetitorEstimates;
  minimum_viable: MinimumViable;
  margin_impact_table: MarginImpactRow[];
  risk_assessment: RiskAssessment;
  current_position: {
    price: number | null;
    vs_market: number | null;
  };
}

// Scenario Modeling Types
export interface ScenarioParams {
  labor_cost_multiplier: number;
  material_cost_multiplier: number;
  risk_contingency_percent: number;
  desired_margin: number;
}

export interface ScenarioResult {
  scenario_name: string;
  total_price: number;
  base_cost: number;
  margin_percentage: number;
  profit: number;
  price_breakdown: {
    labor: number;
    materials: number;
    overhead: number;
    contingency: number;
    profit: number;
  };
}

export interface ScenarioComparisonData {
  scenarios: ScenarioResult[];
  recommendation: string;
}

// Pricing Trends Types
export interface TrendDataPoint {
  year: number;
  award_amount: {
    mean: number;
    median: number;
    count: number;
  };
}

export interface PricingTrendsData {
  naics_code: string;
  trends: TrendDataPoint[];
  yoy_change: number | null;
}

// Proposal Integration Types
export interface PricingNarrative {
  narrative: string;
  generated_at: string;
}

export interface BOESection {
  title: string;
  content: string;
  details?: {
    role?: string;
    hours?: number;
    rate?: number;
    basis?: string;
  }[];
}

export interface BasisOfEstimate {
  document_title: string;
  rfp_number: string;
  date_prepared: string;
  sections: BOESection[];
  total_price: number;
  confidence_level: string;
}

// Default Labor Rates
export const DEFAULT_LABOR_RATES: Record<string, number> = {
  'Project Manager': 150,
  'Senior Developer': 175,
  'Developer': 125,
  'Junior Developer': 85,
  'Designer': 135,
  'QA Engineer': 110,
  'DevOps Engineer': 160,
  'Technical Writer': 95,
  'Subject Matter Expert': 200,
  'Security Specialist': 185,
  'Data Analyst': 130,
  'Business Analyst': 140,
};
