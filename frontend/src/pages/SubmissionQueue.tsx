import React from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../services/api'
import toast from 'react-hot-toast'
import SubmissionCard from '../components/SubmissionCard'

export default function SubmissionQueue() {
  const queryClient = useQueryClient()

  const { data: submissions, isLoading } = useQuery({
    queryKey: ['submission-queue'],
    queryFn: () => api.getSubmissionQueue()
  })

  const retryMutation = useMutation({
    mutationFn: (submissionId: string) => api.retrySubmission(submissionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['submission-queue'] })
      toast.success('Submission queued for retry')
    }
  })

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Submission Queue</h2>
        <p className="mt-1 text-sm text-gray-500">
          Monitor and manage bid submissions to government portals
        </p>
      </div>

      {isLoading ? (
        <div className="text-center py-12">Loading submissions...</div>
      ) : (
        <div className="grid grid-cols-1 gap-6">
          {submissions?.map((submission: any) => (
            <SubmissionCard
              key={submission.id}
              submission={submission}
              onRetry={() => retryMutation.mutate(submission.submission_id)}
            />
          ))}
          {submissions?.length === 0 && (
            <div className="text-center py-12 text-gray-500">
              No submissions in queue
            </div>
          )}
        </div>
      )}
    </div>
  )
}
