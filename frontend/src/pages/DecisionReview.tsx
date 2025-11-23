import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../services/api'
import { toast } from 'sonner'
import DecisionCard from '../components/DecisionCard'

export default function DecisionReview() {
  const queryClient = useQueryClient()

  const { data: pendingDecisions, isLoading } = useQuery({
    queryKey: ['pending-decisions'],
    queryFn: () => api.getPendingDecisions()
  })

  const approveMutation = useMutation({
    mutationFn: (rfpId: string) => api.approveDecision(rfpId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pending-decisions'] })
      toast.success('Decision approved')
    }
  })

  const rejectMutation = useMutation({
    mutationFn: (rfpId: string) => api.rejectDecision(rfpId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pending-decisions'] })
      toast.success('Decision rejected')
    }
  })

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Decision Review</h2>
        <p className="mt-1 text-sm text-gray-500">
          Review Go/No-Go recommendations and approve bids
        </p>
      </div>

      {isLoading ? (
        <div className="text-center py-12">Loading decisions...</div>
      ) : (
        <div className="grid grid-cols-1 gap-6">
          {pendingDecisions?.map((rfp: any) => (
            <DecisionCard
              key={rfp.id}
              rfp={rfp}
              onApprove={() => approveMutation.mutate(rfp.rfp_id)}
              onReject={() => rejectMutation.mutate(rfp.rfp_id)}
            />
          ))}
          {pendingDecisions?.length === 0 && (
            <div className="text-center py-12 text-gray-500">
              No pending decisions
            </div>
          )}
        </div>
      )}
    </div>
  )
}
