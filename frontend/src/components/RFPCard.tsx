import React from 'react'
import { formatDistance } from 'date-fns'

interface RFPCardProps {
  rfp: any
  onTriageDecision: (rfpId: string, decision: string) => void
}

export default function RFPCard({ rfp, onTriageDecision }: RFPCardProps) {
  return (
    <div className="bg-white shadow rounded-lg p-6">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <h3 className="text-lg font-medium text-gray-900">
            {rfp.title}
          </h3>
          <p className="mt-1 text-sm text-gray-500">
            {rfp.agency} • {rfp.office}
          </p>
          {rfp.description && (
            <p className="mt-2 text-sm text-gray-700 line-clamp-2">
              {rfp.description}
            </p>
          )}
        </div>

        <div className="ml-4 flex flex-col items-end">
          <div className="flex items-center">
            <span className="text-2xl font-bold text-primary-600">
              {rfp.triage_score?.toFixed(1) || 'N/A'}
            </span>
            <span className="ml-1 text-sm text-gray-500">/ 100</span>
          </div>
          {rfp.response_deadline && (
            <span className="mt-1 text-xs text-gray-500">
              Due {formatDistance(new Date(rfp.response_deadline), new Date(), { addSuffix: true })}
            </span>
          )}
        </div>
      </div>

      <div className="mt-4 flex items-center justify-between">
        <div className="flex items-center space-x-2 text-sm text-gray-500">
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
            {rfp.category || 'General'}
          </span>
          {rfp.naics_code && (
            <span>NAICS: {rfp.naics_code}</span>
          )}
        </div>

        <div className="flex space-x-2">
          <button
            onClick={() => onTriageDecision(rfp.rfp_id, 'approve')}
            className="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded-md text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
          >
            ✓ Approve
          </button>
          <button
            onClick={() => onTriageDecision(rfp.rfp_id, 'flag')}
            className="inline-flex items-center px-3 py-1.5 border border-gray-300 text-xs font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
          >
            ⚠ Review
          </button>
          <button
            onClick={() => onTriageDecision(rfp.rfp_id, 'reject')}
            className="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded-md text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
          >
            × Reject
          </button>
        </div>
      </div>
    </div>
  )
}
