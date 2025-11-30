/**
 * Centralized React Query key definitions.
 *
 * Using a structured object pattern ensures:
 * - Type-safe query keys throughout the app
 * - Consistent invalidation patterns
 * - Easy refactoring without magic strings
 *
 * Usage:
 *   useQuery({ queryKey: queryKeys.rfps.all, queryFn: ... })
 *   queryClient.invalidateQueries({ queryKey: queryKeys.rfps.all })
 */
export const queryKeys = {
  // RFP queries
  rfps: {
    all: ['rfps'] as const,
    discovered: (filters?: { category?: string; minScore?: number }) =>
      ['rfps', 'discovered', filters] as const,
    recent: (limit?: number) => ['rfps', 'recent', limit] as const,
    detail: (rfpId: string) => ['rfps', rfpId] as const,
    stats: ['rfps', 'stats'] as const,

    // Sub-resources
    competitors: (rfpId: string) => ['rfps', rfpId, 'competitors'] as const,
    partners: (rfpId: string) => ['rfps', rfpId, 'partners'] as const,
    checklist: (rfpId: string) => ['rfps', rfpId, 'checklist'] as const,

    // Pricing
    pricing: {
      scenarios: (rfpId: string) => ['rfps', rfpId, 'pricing', 'scenarios'] as const,
      subcontractors: (rfpId: string) => ['rfps', rfpId, 'pricing', 'subcontractors'] as const,
      ptw: (rfpId: string, targetProb?: number) =>
        ['rfps', rfpId, 'pricing', 'ptw', targetProb] as const,
    },
  },

  // Bid documents
  bids: {
    all: ['bids'] as const,
    detail: (bidId: string) => ['bids', bidId] as const,
  },

  // Pipeline
  pipeline: {
    status: ['pipeline', 'status'] as const,
    events: (rfpId?: string) => ['pipeline', 'events', rfpId] as const,
  },

  // Company profiles
  profiles: {
    all: ['profiles'] as const,
    detail: (profileId: string) => ['profiles', profileId] as const,
    default: ['profiles', 'default'] as const,
  },

  // Submissions
  submissions: {
    all: ['submissions'] as const,
    detail: (submissionId: string) => ['submissions', submissionId] as const,
    byRfp: (rfpId: string) => ['submissions', 'rfp', rfpId] as const,
  },

  // Predictions
  predictions: {
    all: ['predictions'] as const,
    byRfp: (rfpId: string) => ['predictions', 'rfp', rfpId] as const,
  },

  // Scraper
  scraper: {
    status: ['scraper', 'status'] as const,
    jobs: ['scraper', 'jobs'] as const,
    job: (jobId: string) => ['scraper', 'jobs', jobId] as const,
  },

  // Background tasks
  tasks: {
    status: (taskId: string) => ['tasks', taskId] as const,
  },
} as const

// Type helper for extracting query key types
export type QueryKeys = typeof queryKeys
