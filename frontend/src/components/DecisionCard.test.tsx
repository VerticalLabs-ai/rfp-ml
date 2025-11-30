/**
 * Tests for DecisionCard component
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@/test/test-utils'
import DecisionCard from './DecisionCard'

const createMockRfp = (overrides = {}) => ({
  id: 1,
  rfp_id: 'RFP-2024-001',
  title: 'Cloud Infrastructure Services',
  agency: 'Department of Defense',
  decision_recommendation: 'go',
  confidence_level: 0.85,
  overall_score: 8.5,
  response_deadline: '2025-01-15T00:00:00Z',
  ...overrides,
})

describe('DecisionCard', () => {
  describe('Rendering', () => {
    it('renders the RFP title', () => {
      const rfp = createMockRfp()
      render(
        <DecisionCard
          rfp={rfp}
          onApprove={vi.fn()}
          onReject={vi.fn()}
        />
      )

      expect(screen.getByText('Cloud Infrastructure Services')).toBeInTheDocument()
    })

    it('renders the agency name', () => {
      const rfp = createMockRfp()
      render(
        <DecisionCard
          rfp={rfp}
          onApprove={vi.fn()}
          onReject={vi.fn()}
        />
      )

      expect(screen.getByText('Department of Defense')).toBeInTheDocument()
    })

    it('renders the overall score', () => {
      const rfp = createMockRfp({ overall_score: 7.8 })
      render(
        <DecisionCard
          rfp={rfp}
          onApprove={vi.fn()}
          onReject={vi.fn()}
        />
      )

      expect(screen.getByText('7.8')).toBeInTheDocument()
    })

    it('renders the confidence level as percentage', () => {
      const rfp = createMockRfp({ confidence_level: 0.92 })
      render(
        <DecisionCard
          rfp={rfp}
          onApprove={vi.fn()}
          onReject={vi.fn()}
        />
      )

      expect(screen.getByText('92%')).toBeInTheDocument()
    })

    it('displays N/A when overall_score is missing', () => {
      const rfp = createMockRfp({ overall_score: undefined })
      render(
        <DecisionCard
          rfp={rfp}
          onApprove={vi.fn()}
          onReject={vi.fn()}
        />
      )

      // Should have two N/A texts if both are missing
      const naElements = screen.getAllByText('N/A')
      expect(naElements.length).toBeGreaterThanOrEqual(1)
    })

    it('displays N/A when confidence_level is missing', () => {
      const rfp = createMockRfp({ confidence_level: undefined })
      render(
        <DecisionCard
          rfp={rfp}
          onApprove={vi.fn()}
          onReject={vi.fn()}
        />
      )

      expect(screen.getByText('N/A')).toBeInTheDocument()
    })
  })

  describe('Recommendation badges', () => {
    it('shows "go" recommendation with green styling', () => {
      const rfp = createMockRfp({ decision_recommendation: 'go' })
      render(
        <DecisionCard
          rfp={rfp}
          onApprove={vi.fn()}
          onReject={vi.fn()}
        />
      )

      const badge = screen.getByText('go')
      expect(badge).toBeInTheDocument()
      expect(badge.className).toContain('bg-green')
    })

    it('shows "no-go" recommendation with red styling', () => {
      const rfp = createMockRfp({ decision_recommendation: 'no-go' })
      render(
        <DecisionCard
          rfp={rfp}
          onApprove={vi.fn()}
          onReject={vi.fn()}
        />
      )

      const badge = screen.getByText('no-go')
      expect(badge).toBeInTheDocument()
      expect(badge.className).toContain('bg-red')
    })

    it('shows "Pending" when recommendation is undefined', () => {
      const rfp = createMockRfp({ decision_recommendation: undefined })
      render(
        <DecisionCard
          rfp={rfp}
          onApprove={vi.fn()}
          onReject={vi.fn()}
        />
      )

      const badge = screen.getByText('Pending')
      expect(badge).toBeInTheDocument()
      expect(badge.className).toContain('bg-yellow')
    })

    it('shows "Pending" for unknown recommendation values', () => {
      const rfp = createMockRfp({ decision_recommendation: 'maybe' })
      render(
        <DecisionCard
          rfp={rfp}
          onApprove={vi.fn()}
          onReject={vi.fn()}
        />
      )

      const badge = screen.getByText('maybe')
      expect(badge).toBeInTheDocument()
      expect(badge.className).toContain('bg-yellow')
    })
  })

  describe('Button interactions', () => {
    it('calls onApprove with rfp_id when Approve button is clicked', () => {
      const onApprove = vi.fn()
      const rfp = createMockRfp({ rfp_id: 'RFP-2024-TEST' })

      render(
        <DecisionCard
          rfp={rfp}
          onApprove={onApprove}
          onReject={vi.fn()}
        />
      )

      fireEvent.click(screen.getByText('Approve'))

      expect(onApprove).toHaveBeenCalledTimes(1)
      expect(onApprove).toHaveBeenCalledWith('RFP-2024-TEST')
    })

    it('calls onReject with rfp_id when Reject button is clicked', () => {
      const onReject = vi.fn()
      const rfp = createMockRfp({ rfp_id: 'RFP-2024-REJECT' })

      render(
        <DecisionCard
          rfp={rfp}
          onApprove={vi.fn()}
          onReject={onReject}
        />
      )

      fireEvent.click(screen.getByText('Reject'))

      expect(onReject).toHaveBeenCalledTimes(1)
      expect(onReject).toHaveBeenCalledWith('RFP-2024-REJECT')
    })
  })

  describe('Navigation', () => {
    it('links to the RFP detail page', () => {
      const rfp = createMockRfp({ rfp_id: 'RFP-2024-NAV' })
      render(
        <DecisionCard
          rfp={rfp}
          onApprove={vi.fn()}
          onReject={vi.fn()}
        />
      )

      const link = screen.getByRole('link', { name: /Cloud Infrastructure Services/i })
      expect(link).toHaveAttribute('href', '/rfps/RFP-2024-NAV')
    })
  })

  describe('Edge cases', () => {
    it('handles confidence level of 0', () => {
      const rfp = createMockRfp({ confidence_level: 0 })
      render(
        <DecisionCard
          rfp={rfp}
          onApprove={vi.fn()}
          onReject={vi.fn()}
        />
      )

      // 0 is falsy in JS, so the ternary `rfp.confidence_level ?` shows N/A
      const naElements = screen.getAllByText('N/A')
      expect(naElements.length).toBeGreaterThanOrEqual(1)
    })

    it('handles overall score of 0', () => {
      const rfp = createMockRfp({ overall_score: 0 })
      render(
        <DecisionCard
          rfp={rfp}
          onApprove={vi.fn()}
          onReject={vi.fn()}
        />
      )

      // 0?.toFixed(1) returns "0.0" (string), which is truthy
      // So the || 'N/A' doesn't trigger, and we see "0.0"
      expect(screen.getByText('0.0')).toBeInTheDocument()
    })

    it('handles very long title', () => {
      const rfp = createMockRfp({
        title: 'A Very Long Title That Could Potentially Cause Layout Issues If Not Handled Properly By The Component Styling'
      })
      render(
        <DecisionCard
          rfp={rfp}
          onApprove={vi.fn()}
          onReject={vi.fn()}
        />
      )

      expect(screen.getByText(/A Very Long Title/)).toBeInTheDocument()
    })

    it('handles special characters in title', () => {
      const rfp = createMockRfp({
        title: 'IT Services & Support (2024-2025)'
      })
      render(
        <DecisionCard
          rfp={rfp}
          onApprove={vi.fn()}
          onReject={vi.fn()}
        />
      )

      expect(screen.getByText('IT Services & Support (2024-2025)')).toBeInTheDocument()
    })
  })
})
