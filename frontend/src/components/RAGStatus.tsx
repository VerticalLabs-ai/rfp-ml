import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Database, AlertCircle, CheckCircle2, Loader2, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { Progress } from '@/components/ui/progress'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'

interface RAGStatusResponse {
  is_available: boolean
  is_building: boolean
  build_progress: number
  index_info: {
    files: {
      faiss_exists: boolean
      faiss_size_mb: number
      metadata_valid: boolean
    }
    vectors: {
      total: number
      dimension: number
      documents_with_metadata: number
    }
  } | null
  statistics: {
    embedding_model: string
    total_vectors: number
  } | null
  last_build: {
    started_at: string | null
    completed_at: string | null
    error: string | null
    duration_seconds: number | null
  } | null
}

interface RAGHealthResponse {
  healthy: boolean
  issues: string[]
  recommendations: string[]
}

export function RAGStatus() {
  const queryClient = useQueryClient()

  const { data: status, isLoading } = useQuery<RAGStatusResponse>({
    queryKey: ['rag-status'],
    queryFn: async () => {
      const response = await fetch('/api/v1/rag/status')
      if (!response.ok) throw new Error('Failed to fetch RAG status')
      return response.json()
    },
    refetchInterval: (query) => {
      // Poll more frequently if building
      return query.state.data?.is_building ? 2000 : 30000
    },
  })

  const { data: health } = useQuery<RAGHealthResponse>({
    queryKey: ['rag-health'],
    queryFn: async () => {
      const response = await fetch('/api/v1/rag/health')
      if (!response.ok) throw new Error('Failed to fetch RAG health')
      return response.json()
    },
    refetchInterval: 60000, // Check health every minute
  })

  const rebuildMutation = useMutation({
    mutationFn: async () => {
      const response = await fetch('/api/v1/rag/rebuild', { method: 'POST' })
      if (!response.ok) throw new Error('Failed to trigger rebuild')
      return response.json()
    },
    onSuccess: () => {
      toast.success('RAG index rebuild started', {
        description: 'This may take up to an hour. Check status for progress.',
      })
      queryClient.invalidateQueries({ queryKey: ['rag-status'] })
    },
    onError: (error) => {
      toast.error('Failed to start rebuild', {
        description: error instanceof Error ? error.message : 'Unknown error',
      })
    },
  })

  const isHealthy = health?.healthy ?? false
  const isBuilding = status?.is_building ?? false
  const isAvailable = status?.is_available ?? false

  // Determine status color
  const getStatusColor = () => {
    if (isBuilding) return 'text-yellow-500'
    if (!isAvailable) return 'text-red-500'
    if (!isHealthy) return 'text-orange-500'
    return 'text-green-500'
  }

  const getStatusIcon = () => {
    if (isLoading) return <Loader2 className="h-4 w-4 animate-spin" />
    if (isBuilding) return <Loader2 className="h-4 w-4 animate-spin" />
    if (!isAvailable || !isHealthy) return <AlertCircle className="h-4 w-4" />
    return <CheckCircle2 className="h-4 w-4" />
  }

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className={cn('gap-2', getStatusColor())}
        >
          <Database className="h-4 w-4" />
          {getStatusIcon()}
          <span className="hidden sm:inline text-xs">RAG</span>
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-80" align="end">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h4 className="font-semibold">RAG Index Status</h4>
            <span
              className={cn(
                'text-xs px-2 py-1 rounded-full',
                isBuilding
                  ? 'bg-yellow-100 text-yellow-800'
                  : isHealthy
                  ? 'bg-green-100 text-green-800'
                  : 'bg-red-100 text-red-800'
              )}
            >
              {isBuilding ? 'Building' : isHealthy ? 'Healthy' : 'Issues'}
            </span>
          </div>

          {isBuilding && (
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Build Progress</span>
                <span>{status?.build_progress?.toFixed(0) ?? 0}%</span>
              </div>
              <Progress value={status?.build_progress ?? 0} className="h-2" />
            </div>
          )}

          {status?.statistics && (
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <span className="text-muted-foreground">Vectors:</span>{' '}
                <span className="font-medium">
                  {status.statistics.total_vectors.toLocaleString()}
                </span>
              </div>
              <div>
                <span className="text-muted-foreground">Model:</span>{' '}
                <span className="font-medium text-xs">
                  {status.statistics.embedding_model?.split('-').slice(-2).join('-')}
                </span>
              </div>
            </div>
          )}

          {status?.index_info?.files && (
            <div className="text-sm space-y-1">
              <div className="flex items-center gap-2">
                {status.index_info.files.faiss_exists ? (
                  <CheckCircle2 className="h-3 w-3 text-green-500" />
                ) : (
                  <AlertCircle className="h-3 w-3 text-red-500" />
                )}
                <span>
                  FAISS Index ({status.index_info.files.faiss_size_mb.toFixed(0)} MB)
                </span>
              </div>
              <div className="flex items-center gap-2">
                {status.index_info.files.metadata_valid ? (
                  <CheckCircle2 className="h-3 w-3 text-green-500" />
                ) : (
                  <AlertCircle className="h-3 w-3 text-orange-500" />
                )}
                <span>
                  Metadata {status.index_info.files.metadata_valid ? 'Valid' : 'Needs Rebuild'}
                </span>
              </div>
            </div>
          )}

          {health?.issues && health.issues.length > 0 && (
            <div className="space-y-1">
              <span className="text-sm font-medium text-orange-600">Issues:</span>
              <ul className="text-xs text-muted-foreground space-y-1">
                {health.issues.slice(0, 3).map((issue, i) => (
                  <li key={i} className="flex items-start gap-1">
                    <span className="text-orange-500">•</span>
                    {issue}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="pt-2 border-t">
            <Button
              size="sm"
              variant={isHealthy ? 'outline' : 'default'}
              className="w-full"
              onClick={() => rebuildMutation.mutate()}
              disabled={isBuilding || rebuildMutation.isPending}
            >
              {isBuilding ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Building...
                </>
              ) : (
                <>
                  <RefreshCw className="h-4 w-4 mr-2" />
                  {isHealthy ? 'Rebuild Index' : 'Fix Issues (Rebuild)'}
                </>
              )}
            </Button>
            {!isHealthy && (
              <p className="text-xs text-muted-foreground mt-2 text-center">
                Rebuild will fix metadata issues (~1 hour)
              </p>
            )}
          </div>
        </div>
      </PopoverContent>
    </Popover>
  )
}
