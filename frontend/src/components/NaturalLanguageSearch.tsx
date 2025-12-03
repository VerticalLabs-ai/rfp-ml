import * as React from 'react'
import { useCallback, useState, useEffect, useRef } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import {
  Search,
  Sparkles,
  X,
  Filter,
  MapPin,
  Building2,
  DollarSign,
  Tag,
  Loader2,
  ChevronDown,
  Clock,
} from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { cn } from '@/lib/utils'
import { apiClient } from '@/services/api'

// Types
interface ParsedQueryInfo {
  original_query: string
  semantic_query: string
  extracted_filters: Record<string, unknown>
  keywords: string[]
  intent: string
  confidence: number
}

interface SearchResultItem {
  rfp_id: string
  title: string
  agency: string | null
  description: string | null
  naics_code: string | null
  category: string | null
  award_amount: number | null
  response_deadline: string | null
  triage_score: number | null
  relevance_score: number
  match_highlights: string[]
}

interface SearchResponse {
  results: SearchResultItem[]
  total: number
  query_info: ParsedQueryInfo
  search_type: string
}

interface SearchSuggestionsResponse {
  suggestions: string[]
  recent_searches: string[]
  popular_categories: string[]
}

interface ExampleQuery {
  query: string
  description: string
}

interface ExampleQueriesResponse {
  examples: ExampleQuery[]
  categories: string[]
}

// Static example queries for when API is not available
const FALLBACK_EXAMPLES: ExampleQuery[] = [
  { query: 'IT contracts for small businesses in Texas', description: 'Location + set-aside + industry' },
  { query: 'Construction projects over $1M closing this month', description: 'Industry + amount + deadline' },
  { query: 'Healthcare tenders from VA', description: 'Industry + agency' },
  { query: 'Woman-owned small business set-asides for software', description: 'Set-aside + industry' },
]

interface NaturalLanguageSearchProps {
  onResultSelect?: (rfp: SearchResultItem) => void
  onResultsChange?: (results: SearchResultItem[]) => void
  className?: string
  showResults?: boolean
  showExamples?: boolean
  placeholder?: string
  compact?: boolean
}

/**
 * Natural Language Search component for RFP Discovery.
 *
 * Features:
 * - Semantic search powered by RAG
 * - Auto-extracts filters from natural language
 * - Shows parsed query interpretation
 * - Relevance scoring and highlights
 */
export function NaturalLanguageSearch({
  onResultSelect,
  onResultsChange,
  className,
  showResults = true,
  showExamples = true,
  placeholder = 'Try "Construction contracts in California over $1M" or "IT services for DOD"',
  compact = false,
}: NaturalLanguageSearchProps) {
  const [query, setQuery] = useState('')
  const [searchType, setSearchType] = useState<'hybrid' | 'semantic' | 'keyword'>('hybrid')
  const [showFilters, setShowFilters] = useState(false)
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)
  const suggestionsRef = useRef<HTMLDivElement>(null)

  // Fetch example queries
  const { data: exampleData } = useQuery<ExampleQueriesResponse>({
    queryKey: ['search-examples'],
    queryFn: async () => {
      try {
        const response = await apiClient.get<ExampleQueriesResponse>('/discovery/search/examples')
        return response.data
      } catch {
        return { examples: FALLBACK_EXAMPLES, categories: [] }
      }
    },
    staleTime: 1000 * 60 * 30, // 30 minutes
  })

  const examples = exampleData?.examples || FALLBACK_EXAMPLES

  // Click-outside handler for suggestions dropdown
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (suggestionsRef.current && !suggestionsRef.current.contains(event.target as Node)) {
        setShowSuggestions(false)
      }
    }

    if (showSuggestions) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [showSuggestions])

  // Search mutation
  const searchMutation = useMutation({
    mutationFn: async (searchQuery: string) => {
      const response = await apiClient.post<SearchResponse>('/discovery/search', {
        query: searchQuery,
        search_type: searchType,
        top_k: 20,
        skip: 0,
        min_score: 0,
      })
      return response.data
    },
    onSuccess: (data) => {
      setHasSearched(true)
      onResultsChange?.(data.results)
    },
  })

  // Suggestions query
  const { data: suggestions } = useQuery<SearchSuggestionsResponse>({
    queryKey: ['search-suggestions', query],
    queryFn: async () => {
      if (!query || query.length < 2) {
        return { suggestions: [], recent_searches: [], popular_categories: [] }
      }
      const response = await apiClient.get<SearchSuggestionsResponse>(
        `/discovery/search/suggestions?q=${encodeURIComponent(query)}`
      )
      return response.data
    },
    enabled: query.length >= 2 && showSuggestions,
  })

  const { mutate: searchMutate } = searchMutation

  const handleSearch = useCallback(
    (e?: React.FormEvent) => {
      e?.preventDefault()
      if (query.trim()) {
        setShowSuggestions(false)
        searchMutate(query.trim())
      }
    },
    [query, searchMutate]
  )

  const handleSuggestionClick = useCallback(
    (suggestion: string) => {
      setQuery(suggestion)
      setShowSuggestions(false)
      searchMutate(suggestion)
    },
    [searchMutate]
  )

  const handleClear = useCallback(() => {
    setQuery('')
    setHasSearched(false)
    onResultsChange?.([])
  }, [onResultsChange])

  const handleExampleClick = useCallback(
    (exampleQuery: string) => {
      setQuery(exampleQuery)
      setShowSuggestions(false)
      searchMutate(exampleQuery)
    },
    [searchMutate]
  )

  const parsedFilters = searchMutation.data?.query_info?.extracted_filters || {}
  const hasExtractedFilters = Object.keys(parsedFilters).length > 0

  return (
    <div className={cn('space-y-4', className)}>
      {/* Search Input */}
      <form onSubmit={handleSearch} className="relative">
        <div className="relative flex items-center gap-2">
          <div className="relative flex-1">
            <Sparkles className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-primary" />
            <Input
              value={query}
              onChange={(e) => {
                setQuery(e.target.value)
                setShowSuggestions(true)
              }}
              onFocus={() => setShowSuggestions(true)}
              placeholder={placeholder}
              className="pl-10 pr-10 h-12 text-base"
            />
            {query && (
              <button
                type="button"
                onClick={handleClear}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>

          {/* Search Type Selector */}
          {!compact && (
            <Select
              value={searchType}
              onValueChange={(v) => setSearchType(v as typeof searchType)}
            >
              <SelectTrigger className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="hybrid">Hybrid</SelectItem>
                <SelectItem value="semantic">Semantic</SelectItem>
                <SelectItem value="keyword">Keyword</SelectItem>
              </SelectContent>
            </Select>
          )}

          <Button type="submit" disabled={!query.trim() || searchMutation.isPending} size={compact ? 'default' : 'lg'}>
            {searchMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Search className="h-4 w-4" />
            )}
            <span className="ml-2 hidden sm:inline">Search</span>
          </Button>
        </div>

        {/* Suggestions Dropdown */}
        {showSuggestions && suggestions && (suggestions.suggestions.length > 0 || suggestions.popular_categories.length > 0) && (
          <Card ref={suggestionsRef} className="absolute z-50 mt-1 w-full">
            <CardContent className="p-2">
              {suggestions.suggestions.length > 0 && (
                <div className="mb-2">
                  <p className="mb-1 px-2 text-xs font-medium text-muted-foreground">
                    Suggestions
                  </p>
                  {suggestions.suggestions.map((suggestion) => (
                    <button
                      key={suggestion}
                      type="button"
                      onClick={() => handleSuggestionClick(suggestion)}
                      className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-muted"
                    >
                      <Search className="h-3 w-3 text-muted-foreground" />
                      {suggestion}
                    </button>
                  ))}
                </div>
              )}
              {suggestions.popular_categories.length > 0 && (
                <div>
                  <p className="mb-1 px-2 text-xs font-medium text-muted-foreground">
                    Popular Categories
                  </p>
                  <div className="flex flex-wrap gap-1 px-2">
                    {suggestions.popular_categories.slice(0, 6).map((category) => (
                      <Badge
                        key={category}
                        variant="secondary"
                        className="cursor-pointer"
                        onClick={() => handleSuggestionClick(category)}
                      >
                        {category}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </form>

      {/* AI Understanding Loading State */}
      {searchMutation.isPending && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground animate-pulse">
          <Sparkles className="h-4 w-4 text-primary" />
          <span>AI is understanding your query...</span>
        </div>
      )}

      {/* Example Queries Section - shown when no search has been performed */}
      {showExamples && !hasSearched && !searchMutation.isPending && !query && (
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Sparkles className="h-4 w-4" />
            <span>Try these example searches:</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {examples.slice(0, compact ? 2 : 4).map((example) => (
              <button
                key={example.query}
                type="button"
                onClick={() => handleExampleClick(example.query)}
                className="group flex items-center gap-2 rounded-lg border border-dashed px-3 py-2 text-sm transition-colors hover:border-primary hover:bg-muted"
              >
                <Search className="h-3 w-3 text-muted-foreground group-hover:text-primary" />
                <span className="text-left">
                  <span className="block font-medium">{example.query}</span>
                  <span className="block text-xs text-muted-foreground">{example.description}</span>
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Extracted Filters Display */}
      {hasExtractedFilters && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-muted-foreground">Detected filters:</span>
          {parsedFilters.location != null && (
            <Badge variant="outline" className="gap-1">
              <MapPin className="h-3 w-3" />
              <span>{String(parsedFilters.location)}</span>
            </Badge>
          )}
          {parsedFilters.agency != null && (
            <Badge variant="outline" className="gap-1">
              <Building2 className="h-3 w-3" />
              <span>{String(parsedFilters.agency)}</span>
            </Badge>
          )}
          {parsedFilters.naics_code != null && (
            <Badge variant="outline" className="gap-1">
              <Tag className="h-3 w-3" />
              <span>NAICS {String(parsedFilters.naics_code)}</span>
            </Badge>
          )}
          {parsedFilters.amount_range != null && (
            <Badge variant="outline" className="gap-1">
              <DollarSign className="h-3 w-3" />
              <span>{formatAmountRange(parsedFilters.amount_range as { min?: number; max?: number })}</span>
            </Badge>
          )}
          {parsedFilters.set_aside != null && (
            <Badge variant="outline" className="gap-1">
              <span>{String(parsedFilters.set_aside)}</span>
            </Badge>
          )}
          <Popover open={showFilters} onOpenChange={setShowFilters}>
            <PopoverTrigger asChild>
              <Button variant="ghost" size="sm" className="h-6 gap-1 px-2 text-xs">
                <Filter className="h-3 w-3" />
                Query Info
                <ChevronDown className="h-3 w-3" />
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-80">
              <div className="space-y-2 text-sm">
                <div>
                  <span className="font-medium">Semantic Query:</span>
                  <p className="text-muted-foreground">
                    {searchMutation.data?.query_info?.semantic_query}
                  </p>
                </div>
                <div>
                  <span className="font-medium">Keywords:</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {searchMutation.data?.query_info?.keywords.map((kw: string) => (
                      <Badge key={kw} variant="secondary" className="text-xs">
                        {kw}
                      </Badge>
                    ))}
                  </div>
                </div>
                <div>
                  <span className="font-medium">Confidence:</span>{' '}
                  {Math.round((searchMutation.data?.query_info?.confidence || 0) * 100)}%
                </div>
              </div>
            </PopoverContent>
          </Popover>
        </div>
      )}

      {/* Search Results */}
      {showResults && searchMutation.data && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              Found {searchMutation.data.total} results
              {searchMutation.data.search_type !== 'keyword' && (
                <span className="ml-1">
                  (using {searchMutation.data.search_type} search)
                </span>
              )}
            </p>
          </div>

          <div className="space-y-2">
            {searchMutation.data.results.map((result: SearchResultItem) => (
              <SearchResultCard
                key={result.rfp_id}
                result={result}
                onClick={() => onResultSelect?.(result)}
              />
            ))}
          </div>

          {searchMutation.data.results.length === 0 && (
            <div className="py-8 text-center text-muted-foreground">
              <Search className="mx-auto h-12 w-12 opacity-50" />
              <p className="mt-2">No RFPs match your search</p>
              <p className="text-sm">Try different keywords or broader filters</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/**
 * Individual search result card
 */
function SearchResultCard({
  result,
  onClick,
}: {
  result: SearchResultItem
  onClick?: () => void
}) {
  return (
    <Card
      className={cn(
        'cursor-pointer transition-colors hover:bg-muted/50',
        onClick && 'hover:border-primary'
      )}
      onClick={onClick}
    >
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-base font-medium line-clamp-2">
            {result.title}
          </CardTitle>
          <div className="flex shrink-0 items-center gap-2">
            <Badge
              variant={result.relevance_score > 0.7 ? 'default' : 'secondary'}
              className="shrink-0"
            >
              {Math.round(result.relevance_score * 100)}% match
            </Badge>
            {result.triage_score && (
              <Badge variant="outline" className="shrink-0">
                Score: {result.triage_score}
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground">
          {result.agency && (
            <span className="flex items-center gap-1">
              <Building2 className="h-3 w-3" />
              {result.agency}
            </span>
          )}
          {result.naics_code && (
            <span className="flex items-center gap-1">
              <Tag className="h-3 w-3" />
              {result.naics_code}
            </span>
          )}
          {result.award_amount && (
            <span className="flex items-center gap-1">
              <DollarSign className="h-3 w-3" />
              {formatCurrency(result.award_amount)}
            </span>
          )}
          {result.response_deadline && (
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              Due: {formatDate(result.response_deadline)}
            </span>
          )}
        </div>

        {result.match_highlights.length > 0 && (
          <div className="text-sm">
            {result.match_highlights.map((highlight, i) => (
              <p key={i} className="text-muted-foreground line-clamp-2">
                ...{highlight}...
              </p>
            ))}
          </div>
        )}

        {result.category && (
          <Badge variant="outline" className="mt-2">
            {result.category}
          </Badge>
        )}
      </CardContent>
    </Card>
  )
}

// Utility functions
function formatCurrency(amount: number): string {
  if (amount >= 1_000_000_000) {
    return `$${(amount / 1_000_000_000).toFixed(1)}B`
  }
  if (amount >= 1_000_000) {
    return `$${(amount / 1_000_000).toFixed(1)}M`
  }
  if (amount >= 1_000) {
    return `$${(amount / 1_000).toFixed(0)}K`
  }
  return `$${amount.toFixed(0)}`
}

function formatDate(dateStr: string): string {
  try {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    })
  } catch {
    return dateStr
  }
}

function formatAmountRange(range: { min?: number; max?: number }): string {
  if (range.min != null && range.max != null) {
    return `${formatCurrency(range.min)} - ${formatCurrency(range.max)}`
  }
  if (range.min != null) {
    return `Over ${formatCurrency(range.min)}`
  }
  if (range.max != null) {
    return `Under ${formatCurrency(range.max)}`
  }
  return ''
}

export default NaturalLanguageSearch
