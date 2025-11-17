import React from 'react'
import { formatDistance } from 'date-fns'

interface SubmissionCardProps {
  submission: any
  onRetry: () => void
}

const statusColors: Record<string, string> = {
  queued: 'bg-yellow-100 text-yellow-800',
  submitting: 'bg-blue-100 text-blue-800',
  submitted: 'bg-green-100 text-green-800',
  confirmed: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800'
}

export default function SubmissionCard({ submission, onRetry }: SubmissionCardProps) {
  return (
    <div className="bg-white shadow rounded-lg p-6">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center space-x-2">
            <h3 className="text-lg font-medium text-gray-900">
              {submission.portal}
            </h3>
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusColors[submission.status] || 'bg-gray-100 text-gray-800'}`}>
              {submission.status}
            </span>
          </div>
          <p className="mt-1 text-sm text-gray-500">
            Submission ID: {submission.submission_id}
          </p>
          {submission.confirmation_number && (
            <p className="mt-1 text-sm font-medium text-green-600">
              ✓ Confirmation: {submission.confirmation_number}
            </p>
          )}
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
        <div>
          <span className="text-gray-500">Created:</span>
          <span className="ml-2 text-gray-900">
            {formatDistance(new Date(submission.created_at), new Date(), { addSuffix: true })}
          </span>
        </div>
        {submission.submitted_at && (
          <div>
            <span className="text-gray-500">Submitted:</span>
            <span className="ml-2 text-gray-900">
              {formatDistance(new Date(submission.submitted_at), new Date(), { addSuffix: true })}
            </span>
          </div>
        )}
        <div>
          <span className="text-gray-500">Attempts:</span>
          <span className="ml-2 text-gray-900">
            {submission.attempts} / {submission.max_retries || 3}
          </span>
        </div>
      </div>

      {submission.status === 'failed' && submission.attempts < 3 && (
        <div className="mt-4">
          <button
            onClick={onRetry}
            className="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
          >
            🔄 Retry Submission
          </button>
        </div>
      )}
    </div>
  )
}
