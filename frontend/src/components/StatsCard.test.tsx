/**
 * Tests for StatsCard component
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@/test/test-utils'
import { TrendingUp, FileText, DollarSign, Users } from 'lucide-react'
import StatsCard from './StatsCard'

describe('StatsCard', () => {
  describe('Rendering', () => {
    it('renders the title', () => {
      render(
        <StatsCard
          title="Total RFPs"
          value={42}
          icon={FileText}
        />
      )

      expect(screen.getByText('Total RFPs')).toBeInTheDocument()
    })

    it('renders numeric values', () => {
      render(
        <StatsCard
          title="Active Projects"
          value={128}
          icon={TrendingUp}
        />
      )

      expect(screen.getByText('128')).toBeInTheDocument()
    })

    it('renders string values', () => {
      render(
        <StatsCard
          title="Revenue"
          value="$1.2M"
          icon={DollarSign}
        />
      )

      expect(screen.getByText('$1.2M')).toBeInTheDocument()
    })

    it('renders with zero value', () => {
      render(
        <StatsCard
          title="Pending"
          value={0}
          icon={Users}
        />
      )

      expect(screen.getByText('0')).toBeInTheDocument()
    })
  })

  describe('Trend indicator', () => {
    it('displays positive trend with up arrow', () => {
      render(
        <StatsCard
          title="Growth"
          value={100}
          icon={TrendingUp}
          trend={{ value: '12%', positive: true }}
        />
      )

      expect(screen.getByText('↑')).toBeInTheDocument()
      expect(screen.getByText('12%')).toBeInTheDocument()
    })

    it('displays negative trend with down arrow', () => {
      render(
        <StatsCard
          title="Decline"
          value={50}
          icon={TrendingUp}
          trend={{ value: '8%', positive: false }}
        />
      )

      expect(screen.getByText('↓')).toBeInTheDocument()
      expect(screen.getByText('8%')).toBeInTheDocument()
    })

    it('does not display trend when not provided', () => {
      render(
        <StatsCard
          title="Static"
          value={25}
          icon={FileText}
        />
      )

      expect(screen.queryByText('↑')).not.toBeInTheDocument()
      expect(screen.queryByText('↓')).not.toBeInTheDocument()
    })
  })

  describe('Color variants', () => {
    it('renders with blue color (default)', () => {
      const { container } = render(
        <StatsCard
          title="Blue Card"
          value={10}
          icon={FileText}
        />
      )

      // Check for blue gradient class in the accent bar
      const gradientBar = container.querySelector('.bg-gradient-to-r')
      expect(gradientBar?.className).toContain('from-blue-500')
    })

    it('renders with green color', () => {
      const { container } = render(
        <StatsCard
          title="Green Card"
          value={10}
          icon={FileText}
          color="green"
        />
      )

      const gradientBar = container.querySelector('.bg-gradient-to-r')
      expect(gradientBar?.className).toContain('from-green-500')
    })

    it('renders with purple color', () => {
      const { container } = render(
        <StatsCard
          title="Purple Card"
          value={10}
          icon={FileText}
          color="purple"
        />
      )

      const gradientBar = container.querySelector('.bg-gradient-to-r')
      expect(gradientBar?.className).toContain('from-purple-500')
    })

    it('renders with orange color', () => {
      const { container } = render(
        <StatsCard
          title="Orange Card"
          value={10}
          icon={FileText}
          color="orange"
        />
      )

      const gradientBar = container.querySelector('.bg-gradient-to-r')
      expect(gradientBar?.className).toContain('from-orange-500')
    })

    it('renders with red color', () => {
      const { container } = render(
        <StatsCard
          title="Red Card"
          value={10}
          icon={FileText}
          color="red"
        />
      )

      const gradientBar = container.querySelector('.bg-gradient-to-r')
      expect(gradientBar?.className).toContain('from-red-500')
    })
  })

  describe('Highlight feature', () => {
    it('applies highlight ring when highlight is true', () => {
      const { container } = render(
        <StatsCard
          title="Highlighted"
          value={99}
          icon={TrendingUp}
          highlight={true}
        />
      )

      // Look for the ring class on the card
      const card = container.querySelector('.ring-2')
      expect(card).toBeInTheDocument()
    })

    it('does not apply highlight ring when highlight is false', () => {
      const { container } = render(
        <StatsCard
          title="Not Highlighted"
          value={99}
          icon={TrendingUp}
          highlight={false}
        />
      )

      const card = container.querySelector('.ring-2')
      expect(card).not.toBeInTheDocument()
    })
  })

  describe('Icon rendering', () => {
    it('renders the provided icon', () => {
      const { container } = render(
        <StatsCard
          title="With Icon"
          value={5}
          icon={FileText}
        />
      )

      // The icon should be rendered as an SVG
      const svg = container.querySelector('svg')
      expect(svg).toBeInTheDocument()
    })
  })
})
