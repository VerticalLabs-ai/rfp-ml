import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../services/api'
import { toast } from 'sonner'
import DecisionCard from '../components/DecisionCard'

export default function DecisionReview() {
  const queryClient = useQueryClient()
  const [analyzingRfpId, setAnalyzingRfpId] = useState<string | null>(null)

  const { data: pendingDecisions, isLoading } = useQuery({
    queryKey: ['pending-decisions'],
    queryFn: () => api.getPendingDecisions()
  })

  const analyzeMutation = useMutation({
    mutationFn: (rfpId: string) => {
      setAnalyzingRfpId(rfpId)
      return api.analyzeRfp(rfpId)
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['pending-decisions'] })
      toast.success(`Analysis complete: ${data.decision_recommendation?.toUpperCase() || 'Review'} recommendation`)
      setAnalyzingRfpId(null)
    },
    onError: () => {
      toast.error('Analysis failed. Please try again.')
      setAnalyzingRfpId(null)
    }
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

  const needsAnalysis = pendingDecisions?.filter((rfp: any) => rfp.overall_score == null).length || 0

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Decision Review</h2>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Review Go/No-Go recommendations and approve bids
          </p>
        </div>
        {needsAnalysis > 0 && (
          <span className="px-3 py-1 bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200 rounded-full text-sm">
            {needsAnalysis} need{needsAnalysis > 1 ? '' : 's'} analysis
          </span>
        )}
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
              onAnalyze={() => analyzeMutation.mutate(rfp.rfp_id)}
              isAnalyzing={analyzingRfpId === rfp.rfp_id}
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
