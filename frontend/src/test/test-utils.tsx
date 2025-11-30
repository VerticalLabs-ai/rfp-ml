/**
 * Custom test utilities for React Testing Library with providers
 */
import { ReactElement, ReactNode } from 'react'
import { render, RenderOptions } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'

// Create a new query client for each test
const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  })

interface AllProvidersProps {
  children: ReactNode
}

function AllProviders({ children }: AllProvidersProps) {
  const queryClient = createTestQueryClient()

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        {children}
      </BrowserRouter>
    </QueryClientProvider>
  )
}

function customRender(
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) {
  return render(ui, { wrapper: AllProviders, ...options })
}

// Re-export everything from React Testing Library
export * from '@testing-library/react'

// Override render method
export { customRender as render }

// Mock API response helpers
export function createMockRFP(overrides = {}) {
  return {
    id: 1,
    rfp_id: 'RFP-2024-001',
    title: 'IT Infrastructure Support Services',
    description: 'Cloud computing and cybersecurity services',
    agency: 'Department of Defense',
    office: 'DISA',
    naics_code: '541512',
    category: 'IT Services',
    posted_date: '2024-12-01T00:00:00',
    response_deadline: '2025-01-15T00:00:00',
    estimated_value: 5000000,
    current_stage: 'discovered',
    triage_score: 0.85,
    overall_score: 0.78,
    decision_recommendation: 'GO',
    source_platform: 'sam.gov',
    ...overrides,
  }
}

export function createMockAlertRule(overrides = {}) {
  return {
    id: 1,
    name: 'High-Value IT Contracts',
    description: 'Alert for IT contracts above threshold',
    alert_type: 'keyword_match',
    priority: 'high',
    criteria: {
      keywords: ['cybersecurity', 'cloud'],
      match_title: true,
      match_description: true,
    },
    notification_channels: ['in_app'],
    is_active: true,
    created_at: '2024-12-01T00:00:00',
    ...overrides,
  }
}

export function createMockNotification(overrides = {}) {
  return {
    id: 1,
    rule_id: 1,
    rfp_id: 1,
    title: 'New matching RFP found',
    message: 'A new RFP matching your criteria was discovered.',
    priority: 'high',
    is_read: false,
    is_dismissed: false,
    is_archived: false,
    created_at: '2024-12-15T10:00:00',
    ...overrides,
  }
}

export function createMockCompanyProfile(overrides = {}) {
  return {
    id: 1,
    name: 'IBYTE Enterprises',
    legal_name: 'IBYTE Enterprises LLC',
    is_default: true,
    uei: 'ABC123XYZ789',
    cage_code: '1A2B3',
    headquarters: 'Washington, DC',
    website: 'https://ibyte.com',
    established_year: 2010,
    employee_count: '50-100',
    certifications: ['8(a)', 'HUBZone', 'ISO 9001:2015'],
    naics_codes: ['541512', '541519', '518210'],
    core_competencies: ['Cloud Computing', 'Cybersecurity', 'AI/ML'],
    ...overrides,
  }
}

export function createMockWriterCommand(overrides = {}) {
  return {
    command: 'executive-summary',
    name: 'Executive Summary',
    description: 'Generate a comprehensive executive summary',
    default_max_words: 500,
    shortcut: '/exec',
    ...overrides,
  }
}
