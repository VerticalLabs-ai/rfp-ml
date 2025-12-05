import { describe, it, expect } from 'vitest'
import type {
  BidOutcome,
  WinLossStats,
  AnalyticsDashboard,
  CompetitorStats,
} from '../analytics'

describe('Analytics Types', () => {
  it('BidOutcome has required fields', () => {
    const outcome: BidOutcome = {
      id: 1,
      rfp_id: 1,
      status: 'won',
      created_at: '2024-01-01',
      updated_at: '2024-01-01',
    }
    expect(outcome.status).toBe('won')
  })

  it('WinLossStats has correct structure', () => {
    const stats: WinLossStats = {
      total_bids: 100,
      wins: 45,
      losses: 40,
      pending: 15,
      win_rate: 0.529,
      total_revenue_won: 5000000,
      total_revenue_lost: 3000000,
      average_deal_size: 111111,
    }
    expect(stats.win_rate).toBe(0.529)
  })
})
