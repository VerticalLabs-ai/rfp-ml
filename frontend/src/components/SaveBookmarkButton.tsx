import { Bookmark, BookmarkCheck, Loader2 } from 'lucide-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { api } from '@/services/api'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'

interface SaveBookmarkButtonProps {
  rfpId: number
  size?: 'sm' | 'default' | 'lg' | 'icon'
  variant?: 'ghost' | 'outline' | 'default'
  showLabel?: boolean
  className?: string
}

export function SaveBookmarkButton({
  rfpId,
  size = 'sm',
  variant = 'ghost',
  showLabel = false,
  className,
}: SaveBookmarkButtonProps) {
  const queryClient = useQueryClient()

  // Check if RFP is saved
  const { data: savedStatus, isLoading: isChecking } = useQuery({
    queryKey: ['saved-rfp-check', rfpId],
    queryFn: () => api.savedRfps.checkIfSaved(rfpId),
    staleTime: 30000, // Cache for 30 seconds
  })

  // Save mutation
  const saveMutation = useMutation({
    mutationFn: () => api.savedRfps.save({ rfp_id: rfpId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['saved-rfp-check', rfpId] })
      queryClient.invalidateQueries({ queryKey: ['saved-rfps'] })
      toast.success('RFP saved to your list')
    },
    onError: () => {
      toast.error('Failed to save RFP')
    },
  })

  // Unsave mutation
  const unsaveMutation = useMutation({
    mutationFn: () => api.savedRfps.unsaveByRfpId(rfpId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['saved-rfp-check', rfpId] })
      queryClient.invalidateQueries({ queryKey: ['saved-rfps'] })
      toast.success('RFP removed from saved list')
    },
    onError: () => {
      toast.error('Failed to unsave RFP')
    },
  })

  const isSaved = savedStatus?.is_saved ?? false
  const isLoading = isChecking || saveMutation.isPending || unsaveMutation.isPending

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation() // Prevent card click
    if (isSaved) {
      unsaveMutation.mutate()
    } else {
      saveMutation.mutate()
    }
  }

  return (
    <Button
      onClick={handleClick}
      size={size}
      variant={variant}
      disabled={isLoading}
      className={cn(
        isSaved && 'text-yellow-500 hover:text-yellow-600',
        className
      )}
      title={isSaved ? 'Remove from saved' : 'Save for later'}
    >
      {isLoading ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : isSaved ? (
        <BookmarkCheck className="h-4 w-4" />
      ) : (
        <Bookmark className="h-4 w-4" />
      )}
      {showLabel && (
        <span className="ml-1">{isSaved ? 'Saved' : 'Save'}</span>
      )}
    </Button>
  )
}
