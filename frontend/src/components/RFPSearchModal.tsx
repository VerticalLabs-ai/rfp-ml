import { useState, useCallback, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import {
  Search,
  Loader2,
  X,
  Building2,
  Calendar,
  DollarSign,
  Tag,
  Sparkles,
  ChevronRight,
} from 'lucide-react'
import { toast } from 'sonner'
import { formatDistanceToNow } from 'date-fns'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { api } from '@/services/api'

interface SearchResult {
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
  results: SearchResult[]
  total: number
  query_info: {
    original_query: string
    semantic_query: string
    extracted_filters: Record<string, any>
    keywords: string[]
    intent: string
    confidence: number
  }
  search_type: string
}

interface RFPSearchModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

const EXAMPLE_QUERIES = [
  'IT services for federal agencies',
  'Construction contracts in California',
  'Cybersecurity small business set-aside',
  'Healthcare services over $1M',
  'DOD software development',
]

export function RFPSearchModal({ open, onOpenChange }: RFPSearchModalProps) {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [searchType, setSearchType] = useState<'hybrid' | 'semantic' | 'keyword'>('hybrid')
  const [results, setResults] = useState<SearchResult[]>([])
  const [queryInfo, setQueryInfo] = useState<SearchResponse['query_info'] | null>(null)

  // Search mutation
  const searchMutation = useMutation({
    mutationFn: (searchQuery: string) =>
      api.searchRFPs({
        query: searchQuery,
        search_type: searchType,
        top_k: 20,
      }),
    onSuccess: (data: SearchResponse) => {
      setResults(data.results)
      setQueryInfo(data.query_info)
      if (data.results.length === 0) {
        toast.info('No results found', {
          description: 'Try adjusting your search terms',
        })
      }
    },
    onError: (error: Error) => {
      toast.error('Search failed', { description: error.message })
    },
  })

  // Handle search
  const handleSearch = useCallback(() => {
    if (!query.trim()) return
    searchMutation.mutate(query.trim())
  }, [query, searchMutation])

  // Handle keyboard enter
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !searchMutation.isPending) {
      handleSearch()
    }
  }

  // Navigate to RFP detail
  const handleSelectRFP = (rfpId: string) => {
    onOpenChange(false)
    navigate(`/rfps/${rfpId}`)
  }

  // Reset on close
  useEffect(() => {
    if (!open) {
      setQuery('')
      setResults([])
      setQueryInfo(null)
    }
  }, [open])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[85vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Search className="h-5 w-5" />
            Search RFPs
          </DialogTitle>
          <DialogDescription>
            Use natural language to find relevant RFP opportunities
          </DialogDescription>
        </DialogHeader>

        {/* Search Input */}
        <div className="flex gap-2">
          <div className="flex-1 relative">
            <Input
              placeholder="e.g., IT services for DOD over $500K"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              className="pr-10"
            />
            {query && (
              <button
                type="button"
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                onClick={() => setQuery('')}
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>
          <Select value={searchType} onValueChange={(v: 'hybrid' | 'semantic' | 'keyword') => setSearchType(v)}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="hybrid">Hybrid</SelectItem>
              <SelectItem value="semantic">Semantic</SelectItem>
              <SelectItem value="keyword">Keyword</SelectItem>
            </SelectContent>
          </Select>
          <Button onClick={handleSearch} disabled={!query.trim() || searchMutation.isPending}>
            {searchMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Search className="h-4 w-4" />
            )}
          </Button>
        </div>

        {/* Example Queries */}
        {!results.length && !searchMutation.isPending && (
          <div className="py-4">
            <p className="text-sm text-muted-foreground mb-2">Try searching for:</p>
            <div className="flex flex-wrap gap-2">
              {EXAMPLE_QUERIES.map((example) => (
                <Button
                  key={example}
                  variant="outline"
                  size="sm"
                  className="text-xs"
                  onClick={() => {
                    setQuery(example)
                    searchMutation.mutate(example)
                  }}
                >
                  {example}
                </Button>
              ))}
            </div>
          </div>
        )}

        {/* Query Analysis */}
        {queryInfo && queryInfo.confidence > 0 && (
          <div className="bg-muted/50 rounded-lg p-3 text-sm">
            <div className="flex items-center gap-2 text-muted-foreground mb-1">
              <Sparkles className="h-4 w-4 text-purple-500" />
              <span>Query Analysis</span>
              <Badge variant="outline" className="text-xs">
                {Math.round(queryInfo.confidence * 100)}% confidence
              </Badge>
            </div>
            <div className="flex flex-wrap gap-2">
              {queryInfo.keywords.map((keyword, i) => (
                <Badge key={i} variant="secondary" className="text-xs">
                  {keyword}
                </Badge>
              ))}
              {Object.entries(queryInfo.extracted_filters).map(([key, value]) => (
                <Badge key={key} className="text-xs bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                  {key}: {String(value)}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Results */}
        <ScrollArea className="flex-1 -mx-6 px-6">
          {searchMutation.isPending ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : results.length > 0 ? (
            <div className="space-y-2 py-2">
              <p className="text-sm text-muted-foreground mb-3">
                Found {results.length} results
              </p>
              {results.map((result) => (
                <button
                  key={result.rfp_id}
                  type="button"
                  className="w-full text-left p-4 rounded-lg border hover:bg-muted/50 transition-colors group"
                  onClick={() => handleSelectRFP(result.rfp_id)}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <Badge
                          variant={result.relevance_score > 0.7 ? 'default' : 'secondary'}
                          className="text-xs"
                        >
                          {Math.round(result.relevance_score * 100)}% match
                        </Badge>
                        {result.category && (
                          <Badge variant="outline" className="text-xs">
                            <Tag className="h-3 w-3 mr-1" />
                            {result.category}
                          </Badge>
                        )}
                      </div>
                      <h4 className="font-medium line-clamp-2 group-hover:text-blue-600">
                        {result.title}
                      </h4>
                      <div className="flex flex-wrap items-center gap-3 mt-2 text-sm text-muted-foreground">
                        {result.agency && (
                          <span className="flex items-center gap-1">
                            <Building2 className="h-3 w-3" />
                            {result.agency}
                          </span>
                        )}
                        {result.award_amount && (
                          <span className="flex items-center gap-1">
                            <DollarSign className="h-3 w-3" />
                            ${result.award_amount.toLocaleString()}
                          </span>
                        )}
                        {result.response_deadline && (
                          <span className="flex items-center gap-1">
                            <Calendar className="h-3 w-3" />
                            Due {formatDistanceToNow(new Date(result.response_deadline), { addSuffix: true })}
                          </span>
                        )}
                      </div>
                      {result.match_highlights.length > 0 && (
                        <p className="text-sm text-muted-foreground mt-2 line-clamp-2">
                          {result.match_highlights[0]}
                        </p>
                      )}
                    </div>
                    <ChevronRight className="h-5 w-5 text-muted-foreground group-hover:text-foreground" />
                  </div>
                </button>
              ))}
            </div>
          ) : queryInfo ? (
            <div className="text-center py-12 text-muted-foreground">
              <Search className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No matching RFPs found</p>
              <p className="text-sm mt-1">Try different keywords or broaden your search</p>
            </div>
          ) : null}
        </ScrollArea>
      </DialogContent>
    </Dialog>
  )
}
