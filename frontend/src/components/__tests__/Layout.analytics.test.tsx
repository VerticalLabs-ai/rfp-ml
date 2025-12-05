/**
 * Tests for Layout component - Win/Loss Analytics navigation
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import Layout from '../Layout'

// Mock the API
vi.mock('@/services/api', () => ({
  api: {
    savedRfps: {
      list: vi.fn().mockResolvedValue({ total: 0, items: [] })
    }
  }
}))

// Mock WebSocket hook
vi.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: vi.fn(() => ({
    isConnected: false,
    connectionState: 'disconnected',
    reconnect: vi.fn(),
    reconnectAttempt: 0,
    reconnectCountdown: 0,
    queuedMessageCount: 0
  }))
}))

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  })

const renderWithRouter = (ui: React.ReactElement, { route = '/dashboard' } = {}) => {
  const queryClient = createTestQueryClient()
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]}>
        {ui}
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('Layout - Win/Loss Analytics Navigation', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the Win/Loss navigation item', () => {
    renderWithRouter(
      <Layout>
        <div>Test content</div>
      </Layout>
    )

    const navItem = screen.getByText('Win/Loss')
    expect(navItem).toBeInTheDocument()
  })

  it('navigates to /analytics when Win/Loss is clicked', () => {
    renderWithRouter(
      <Layout>
        <div>Test content</div>
      </Layout>
    )

    const navLink = screen.getByText('Win/Loss').closest('a')
    expect(navLink).toHaveAttribute('href', '/analytics')
  })

  it('highlights Win/Loss nav item when on /analytics route', () => {
    renderWithRouter(
      <Layout>
        <div>Test content</div>
      </Layout>,
      { route: '/analytics' }
    )

    const navLink = screen.getByText('Win/Loss').closest('a')
    expect(navLink).toHaveClass('border-blue-600')
  })

  it('does not highlight Win/Loss nav item when on other routes', () => {
    renderWithRouter(
      <Layout>
        <div>Test content</div>
      </Layout>,
      { route: '/dashboard' }
    )

    const navLink = screen.getByText('Win/Loss').closest('a')
    expect(navLink).toHaveClass('border-transparent')
    expect(navLink).not.toHaveClass('border-blue-600')
  })

  it('renders Win/Loss navigation item with BarChart3 icon', () => {
    renderWithRouter(
      <Layout>
        <div>Test content</div>
      </Layout>
    )

    const navLink = screen.getByText('Win/Loss').closest('a')
    const icon = navLink?.querySelector('svg')
    expect(icon).toBeInTheDocument()
  })
})
