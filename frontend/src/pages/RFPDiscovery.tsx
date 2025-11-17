import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../services/api'
import toast from 'react-hot-toast'
import RFPCard from '../components/RFPCard'
import FilterBar from '../components/FilterBar'

export default function RFPDiscovery() {
  const queryClient = useQueryClient()
  const [filters, setFilters] = useState({
    category: '',
    minScore: 60
  })

  const { data: rfps, isLoading } = useQuery({
    queryKey: ['discovered-rfps', filters],
    queryFn: () => api.getDiscoveredRFPs(filters)
  })

  const triageMutation = useMutation({
    mutationFn: ({ rfpId, decision }: { rfpId: string, decision: string }) =>
      api.updateTriageDecision(rfpId, decision),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['discovered-rfps'] })
      toast.success('Triage decision updated')
    },
    onError: () => {
      toast.error('Failed to update decision')
    }
  })

  const handleTriageDecision = (rfpId: string, decision: string) => {
    triageMutation.mutate({ rfpId, decision })
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">RFP Discovery</h2>
        <p className="mt-1 text-sm text-gray-500">
          Review and triage discovered RFP opportunities
        </p>
      </div>

      <FilterBar filters={filters} onFilterChange={setFilters} />

      {isLoading ? (
        <div className="text-center py-12">Loading RFPs...</div>
      ) : (
        <div className="grid grid-cols-1 gap-6">
          {rfps?.map((rfp: any) => (
            <RFPCard
              key={rfp.id}
              rfp={rfp}
              onTriageDecision={handleTriageDecision}
            />
          ))}
          {rfps?.length === 0 && (
            <div className="text-center py-12 text-gray-500">
              No RFPs found matching your criteria
            </div>
          )}
        </div>
      )}
    </div>
  )
}
