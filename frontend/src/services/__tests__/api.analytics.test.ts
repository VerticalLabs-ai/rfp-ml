import { describe, it, expect, vi, beforeEach } from 'vitest'
import { api } from '../api'

// Mock axios
vi.mock('axios', () => ({
  default: {
    create: () => ({
      get: vi.fn(),
      post: vi.fn(),
      patch: vi.fn(),
      interceptors: {
        response: { use: vi.fn() },
        request: { use: vi.fn() },
      },
    }),
  },
}))

describe('Analytics API Methods', () => {
  it('has getAnalyticsOverview method', () => {
    expect(api.getAnalyticsOverview).toBeDefined()
    expect(typeof api.getAnalyticsOverview).toBe('function')
  })

  it('has createBidOutcome method', () => {
    expect(api.createBidOutcome).toBeDefined()
    expect(typeof api.createBidOutcome).toBe('function')
  })

  it('has updateBidOutcome method', () => {
    expect(api.updateBidOutcome).toBeDefined()
    expect(typeof api.updateBidOutcome).toBe('function')
  })

  it('has listBidOutcomes method', () => {
    expect(api.listBidOutcomes).toBeDefined()
    expect(typeof api.listBidOutcomes).toBe('function')
  })

  it('has getBidOutcome method', () => {
    expect(api.getBidOutcome).toBeDefined()
    expect(typeof api.getBidOutcome).toBe('function')
  })

  it('has exportAnalytics method', () => {
    expect(api.exportAnalytics).toBeDefined()
    expect(typeof api.exportAnalytics).toBe('function')
  })
})
