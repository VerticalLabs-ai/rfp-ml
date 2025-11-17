import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../services/api'
import PipelineKanban from '../components/PipelineKanban'

export default function PipelineMonitor() {
  const { data: pipelineStatus, isLoading } = useQuery({
    queryKey: ['pipeline-status'],
    queryFn: () => api.getPipelineStatus()
  })

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Pipeline Monitor</h2>
        <p className="mt-1 text-sm text-gray-500">
          Real-time view of RFPs moving through the pipeline
        </p>
      </div>

      {isLoading ? (
        <div className="text-center py-12">Loading pipeline...</div>
      ) : (
        <PipelineKanban stages={pipelineStatus?.stages || {}} />
      )}
    </div>
  )
}
