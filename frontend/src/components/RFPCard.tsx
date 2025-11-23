import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { formatDistance } from 'date-fns'
import { AlertTriangle, Check, X } from 'lucide-react'
import GenerateBidButton from './GenerateBidButton'

interface RFPCardProps {
  rfp: any
  onTriageDecision: (rfpId: string, decision: string) => void
}

export default function RFPCard({ rfp, onTriageDecision }: RFPCardProps) {
  return (
    <Card>
      <CardContent className="p-6">
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
            <Badge variant="secondary">
              {rfp.category || 'General'}
            </Badge>
            {rfp.naics_code && (
              <span>NAICS: {rfp.naics_code}</span>
            )}
          </div>

          <div className="flex space-x-2">
            <GenerateBidButton rfpId={rfp.rfp_id} rfpTitle={rfp.title} />
            <Button
              onClick={() => onTriageDecision(rfp.rfp_id, 'approve')}
              size="sm"
              className="bg-green-600 hover:bg-green-700"
            >
              <Check className="w-4 h-4 mr-1" />
              Approve
            </Button>
            <Button
              onClick={() => onTriageDecision(rfp.rfp_id, 'flag')}
              size="sm"
              variant="outline"
            >
              <AlertTriangle className="w-4 h-4 mr-1" />
              Review
            </Button>
            <Button
              onClick={() => onTriageDecision(rfp.rfp_id, 'reject')}
              size="sm"
              variant="destructive"
            >
              <X className="w-4 h-4 mr-1" />
              Reject
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
