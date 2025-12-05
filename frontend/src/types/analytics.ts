/**
 * TypeScript types for Win/Loss Analytics feature.
 */

export type BidStatus = 'won' | 'lost' | 'pending' | 'no_bid' | 'withdrawn'

export interface BidOutcome {
  id: number
  rfp_id: number
  status: BidStatus
  award_amount?: number
  our_bid_amount?: number
  winning_bidder?: string
  winning_bid_amount?: number
  loss_reason?: string
  debrief_notes?: string
  lessons_learned?: string
  price_delta_percentage?: number
  award_date?: string
  created_at: string
  updated_at: string
}

export interface BidOutcomeCreate {
  rfp_id: number
  status: BidStatus
  award_amount?: number
  our_bid_amount?: number
  winning_bidder?: string
  winning_bid_amount?: number
  loss_reason?: string
  debrief_notes?: string
  award_date?: string
}

export interface BidOutcomeUpdate {
  status?: BidStatus
  award_amount?: number
  our_bid_amount?: number
  winning_bidder?: string
  winning_bid_amount?: number
  loss_reason?: string
  debrief_notes?: string
  lessons_learned?: string
  award_date?: string
}

export interface WinLossStats {
  total_bids: number
  wins: number
  losses: number
  pending: number
  no_bid?: number
  withdrawn?: number
  win_rate: number
  total_revenue_won: number
  total_revenue_lost: number
  average_deal_size: number
  average_margin?: number
}

export interface WinLossTrend {
  period: string
  wins: number
  losses: number
  win_rate: number
  revenue: number
}

export interface CompetitorStats {
  competitor_name: string
  encounters: number
  wins_against_us: number
  losses_against_us: number
  win_rate: number
  categories: string[]
  agencies: string[]
  average_winning_margin?: number
}

export interface AnalyticsDashboard {
  stats: WinLossStats
  trends: WinLossTrend[]
  top_competitors: CompetitorStats[]
  win_rate_by_category: Record<string, number>
  win_rate_by_agency: Record<string, number>
}

export interface AnalyticsFilters {
  start_date?: string
  end_date?: string
  agency?: string
  naics_code?: string
  min_value?: number
  max_value?: number
  status?: BidStatus
}

export interface PaginatedOutcomes {
  items: BidOutcome[]
  total: number
  page: number
  page_size: number
}
