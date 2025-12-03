/**
 * RFP Discovery page with Natural Language Search.
 *
 * Features:
 * - AI-powered natural language search (like GovGPT)
 * - Automatic filter extraction from queries
 * - Semantic + keyword hybrid search
 * - Real-time filtering with 300ms debounce
 * - Search across: title, description, agency, NAICS code, category
 * - Matching term highlighting in results
 * - URL query parameter persistence for shareable links
 * - Keyboard shortcut (Cmd/Ctrl+K) to focus search
 */
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Activity, Link2, Search, SearchX, Sparkles, List } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { useNavigate, useSearchParams } from 'react-router-dom'
import AddRFPDialog from '../components/AddRFPDialog'
import DiscoveryButton from '../components/DiscoveryButton'
import FilterBar from '../components/FilterBar'
import RFPCard from '../components/RFPCard'
import { ImportRFPDialog } from '../components/ImportRFPDialog'
import { NaturalLanguageSearch } from '../components/NaturalLanguageSearch'
import { useRfpSearch } from '../hooks/useRfpSearch'
import { api } from '../services/api'

export default function RFPDiscovery() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()

  // Search mode: 'ai' for natural language, 'filters' for traditional
  const [searchMode, setSearchMode] = useState<'ai' | 'filters'>(
    searchParams.get('mode') === 'filters' ? 'filters' : 'ai'
  )

  // Initialize filters from URL params
  const [filters, setFilters] = useState(() => ({
    stage: searchParams.get('stage') || 'all',
    search: searchParams.get('q') || '',
    sortBy: searchParams.get('sort') || 'score'
  }))

  // Use search hook for debouncing and keyboard shortcuts
  const {
    searchTerm,
    debouncedSearchTerm,
    setSearchTerm,
    clearSearch,
    inputRef,
    isSearching
  } = useRfpSearch({
    debounceMs: 300,
    urlParamName: 'q',
  })

  // Sync search term from URL on mount
  useEffect(() => {
    const urlSearch = searchParams.get('q') || ''
    if (urlSearch !== searchTerm) {
      setSearchTerm(urlSearch)
    }
  }, []) // Only on mount

  // Update filters when search term changes
  useEffect(() => {
    setFilters(prev => ({
      ...prev,
      search: debouncedSearchTerm
    }))
  }, [debouncedSearchTerm])

  // Sync all filters to URL
  useEffect(() => {
    const newParams = new URLSearchParams()

    if (filters.search) {
      newParams.set('q', filters.search)
    }
    if (filters.stage && filters.stage !== 'all') {
      newParams.set('stage', filters.stage)
    }
    if (filters.sortBy && filters.sortBy !== 'score') {
      newParams.set('sort', filters.sortBy)
    }

    // Only update if params changed
    const currentParams = searchParams.toString()
    const newParamsString = newParams.toString()
    if (currentParams !== newParamsString) {
      setSearchParams(newParams, { replace: true })
    }
  }, [filters, setSearchParams])

  // Handle filter changes from FilterBar
  const handleFilterChange = useCallback((newFilters: typeof filters) => {
    // If search changed, update via the hook for debouncing
    if (newFilters.search !== filters.search) {
      setSearchTerm(newFilters.search || '')
    }
    setFilters(newFilters)
  }, [filters.search, setSearchTerm])

  // Handle clear search
  const handleClearSearch = useCallback(() => {
    clearSearch()
    setFilters(prev => ({ ...prev, search: '' }))
  }, [clearSearch])

  // Query for RFPs with debounced search
  const { data: rfps, isLoading, isError } = useQuery({
    queryKey: ['discovered-rfps', {
      ...filters,
      search: debouncedSearchTerm // Use debounced value for query
    }],
    queryFn: () => api.getDiscoveredRFPs({
      ...filters,
      search: debouncedSearchTerm
    }),
    staleTime: 30000, // 30 seconds
  })

  const triageMutation = useMutation({
    mutationFn: ({ rfpId, decision }: { rfpId: string, decision: string }) =>
      api.updateTriageDecision(rfpId, decision),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['discovered-rfps'] })
      toast.success('Triage decision updated')
    },
    onError: () => {
      toast.error('Failed to update decision')
    }
  })

  const deleteMutation = useMutation({
    mutationFn: (rfpId: string) => api.deleteRFP(rfpId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['discovered-rfps'] })
      toast.success('RFP deleted successfully')
    },
    onError: () => {
      toast.error('Failed to delete RFP')
    }
  })

  const handleTriageDecision = (rfpId: string, decision: string) => {
    triageMutation.mutate({ rfpId, decision })
  }

  const handleDelete = (rfpId: string) => {
    deleteMutation.mutate(rfpId)
  }

  // Handle AI search result selection - navigate to RFP detail
  const handleAiResultSelect = useCallback((result: any) => {
    navigate(`/rfp/${result.rfp_id}`)
  }, [navigate])

  // Determine if we're showing search results
  const hasSearchTerm = debouncedSearchTerm.length > 0
  const hasResults = rfps && rfps.length > 0
  const showNoResults = hasSearchTerm && !isLoading && !hasResults

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">RFP Discovery</h2>
          <p className="mt-1 text-sm text-gray-500">
            Search and discover government contract opportunities with AI-powered natural language
          </p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" onClick={() => navigate('/discovery/live')}>
            <Activity className="mr-2 h-4 w-4" />
            Live View
          </Button>
          <ImportRFPDialog
            trigger={
              <Button variant="outline" className="gap-2">
                <Link2 className="h-4 w-4" />
                Import from URL
              </Button>
            }
            onSuccess={() => {
              queryClient.invalidateQueries({ queryKey: ['discovered-rfps'] })
            }}
          />
          <DiscoveryButton />
          <AddRFPDialog />
        </div>
      </div>

      {/* Search Tabs: AI Search vs Traditional Filters */}
      <Tabs value={searchMode} onValueChange={(v) => setSearchMode(v as 'ai' | 'filters')}>
        <TabsList className="grid w-full max-w-md grid-cols-2">
          <TabsTrigger value="ai" className="gap-2">
            <Sparkles className="h-4 w-4" />
            AI Search
          </TabsTrigger>
          <TabsTrigger value="filters" className="gap-2">
            <List className="h-4 w-4" />
            Browse & Filter
          </TabsTrigger>
        </TabsList>

        {/* AI Natural Language Search Tab */}
        <TabsContent value="ai" className="mt-4">
          <Card>
            <CardContent className="pt-6">
              <NaturalLanguageSearch
                onResultSelect={handleAiResultSelect}
                showResults={true}
                showExamples={true}
              />
            </CardContent>
          </Card>
        </TabsContent>

        {/* Traditional Browse & Filter Tab */}
        <TabsContent value="filters" className="mt-4">
          <FilterBar
            filters={{ ...filters, search: searchTerm }}
            onFilterChange={handleFilterChange}
            searchInputRef={inputRef}
            onClearSearch={handleClearSearch}
            isSearching={isSearching}
          />

          {/* Search results info */}
          {hasSearchTerm && hasResults && (
            <div className="flex items-center gap-2 text-sm text-gray-600 mt-4">
              <Search className="h-4 w-4" />
              <span>
                Found <strong>{rfps.length}</strong> result{rfps.length !== 1 ? 's' : ''} for "<strong>{debouncedSearchTerm}</strong>"
              </span>
              <button
                onClick={handleClearSearch}
                className="text-primary-600 hover:underline ml-2"
              >
                Clear search
              </button>
            </div>
          )}

          {isLoading ? (
            <div className="text-center py-12">
              <div className="animate-pulse space-y-4">
                <div className="h-32 bg-gray-200 rounded-lg" />
                <div className="h-32 bg-gray-200 rounded-lg" />
                <div className="h-32 bg-gray-200 rounded-lg" />
              </div>
              <p className="mt-4 text-gray-500">Loading RFPs...</p>
            </div>
          ) : isError ? (
            <div className="text-center py-12 text-red-500">
              Failed to load RFPs. Please try again.
            </div>
          ) : showNoResults ? (
            <div className="text-center py-12">
              <SearchX className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                No results found for "{debouncedSearchTerm}"
              </h3>
              <p className="text-sm text-gray-500 mb-4">
                Try adjusting your search terms or filters
              </p>
              <Button variant="outline" onClick={handleClearSearch}>
                Clear search
              </Button>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-6 mt-4">
              {rfps?.map((rfp: any) => (
                <RFPCard
                  key={rfp.id}
                  rfp={rfp}
                  onTriageDecision={handleTriageDecision}
                  onDelete={handleDelete}
                  searchTerm={debouncedSearchTerm}
                />
              ))}
              {!hasSearchTerm && rfps?.length === 0 && (
                <div className="text-center py-12 text-gray-500">
                  No RFPs found. Start by discovering or importing RFPs.
                </div>
              )}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
