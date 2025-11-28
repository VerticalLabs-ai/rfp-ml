import { Button } from '@/components/ui/button'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Activity, Link2 } from 'lucide-react'
import { useState } from 'react'
import toast from 'react-hot-toast'
import { useNavigate } from 'react-router-dom'
import AddRFPDialog from '../components/AddRFPDialog'
import DiscoveryButton from '../components/DiscoveryButton'
import FilterBar from '../components/FilterBar'
import RFPCard from '../components/RFPCard'
import { ImportRFPDialog } from '../components/ImportRFPDialog'
import { api } from '../services/api'

export default function RFPDiscovery() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [filters, setFilters] = useState({
    stage: 'all',
    search: '',
    sortBy: 'score'
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
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">RFP Discovery</h2>
          <p className="mt-1 text-sm text-gray-500">
            Review and triage discovered RFP opportunities
          </p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" onClick={() => navigate('/discovery/live')}>
            <Activity className="mr-2 h-4 w-4" />
            Live View
          </Button>
          <ImportRFPDialog
            trigger={
              <Button variant="outline" className="gap-2">
                <Link2 className="h-4 w-4" />
                Import from URL
              </Button>
            }
            onSuccess={() => {
              queryClient.invalidateQueries({ queryKey: ['discovered-rfps'] })
            }}
          />
          <DiscoveryButton />
          <AddRFPDialog />
        </div>
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
