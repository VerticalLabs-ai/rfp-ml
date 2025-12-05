import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import WinLossAnalytics from '../WinLossAnalytics'

// Mock the API
vi.mock('@/services/api', () => ({
  api: {
    getAnalyticsOverview: vi.fn().mockResolvedValue({
      stats: {
        total_bids: 100,
        wins: 45,
        losses: 40,
        pending: 15,
        win_rate: 0.529,
        total_revenue_won: 5000000,
        total_revenue_lost: 3000000,
        average_deal_size: 111111,
      },
      trends: [],
      top_competitors: [],
      win_rate_by_category: {},
      win_rate_by_agency: {},
    }),
  },
}))

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
})

const renderWithProviders = (ui: React.ReactElement) => {
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{ui}</BrowserRouter>
    </QueryClientProvider>
  )
}

describe('WinLossAnalytics Page', () => {
  it('renders page title', async () => {
    renderWithProviders(<WinLossAnalytics />)

    expect(await screen.findByText('Win/Loss Analytics')).toBeInTheDocument()
  })

  it('displays stats cards with data', async () => {
    renderWithProviders(<WinLossAnalytics />)

    // Should show win rate
    expect(await screen.findByText(/52\.9%/)).toBeInTheDocument()

    // Should show total bids
    expect(await screen.findByText('100')).toBeInTheDocument()
  })
})
