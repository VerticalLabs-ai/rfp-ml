import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { formatDistance } from 'date-fns'
import { AlertTriangle, Check, ChevronRight, MessageSquare, Trash2, X } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import GenerateBidButton from './GenerateBidButton'
import { HighlightedText } from '../hooks/useRfpSearch'

interface RFPCardProps {
  rfp: any
  onTriageDecision: (rfpId: string, decision: string) => void
  onDelete?: (rfpId: string) => void
  searchTerm?: string
}

export default function RFPCard({ rfp, onTriageDecision, onDelete, searchTerm = '' }: RFPCardProps) {
  const navigate = useNavigate()

  const handleCardClick = (e: React.MouseEvent) => {
    // Don't navigate if clicking on a button or interactive element
    const target = e.target as HTMLElement
    if (
      target.closest('button') ||
      target.closest('a') ||
      target.closest('[role="button"]')
    ) {
      return
    }
    navigate(`/rfps/${rfp.rfp_id}`)
  }

  return (
    <Card
      className="cursor-pointer transition-all hover:shadow-md hover:border-primary-200 group"
      onClick={handleCardClick}
    >
      <CardContent className="p-6">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-start gap-2">
              <h3 className="text-lg font-medium text-gray-900 group-hover:text-primary-600 transition-colors">
                {searchTerm ? (
                  <HighlightedText text={rfp.title} searchTerm={searchTerm} />
                ) : (
                  rfp.title
                )}
              </h3>
              {onDelete && (
                <Button
                  onClick={() => {
                    if (confirm(`Delete "${rfp.title}"? This will remove all documents, Q&A, and bids.`)) {
                      onDelete(rfp.rfp_id)
                    }
                  }}
                  size="sm"
                  variant="ghost"
                  className="h-6 w-6 p-0 text-gray-400 hover:text-red-500"
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              )}
            </div>
            <p className="mt-1 text-sm text-gray-500">
              {searchTerm ? (
                <>
                  <HighlightedText text={rfp.agency || ''} searchTerm={searchTerm} />
                  {rfp.office && (
                    <>
                      {' • '}
                      <HighlightedText text={rfp.office} searchTerm={searchTerm} />
                    </>
                  )}
                </>
              ) : (
                <>
                  {rfp.agency}
                  {rfp.office && ` • ${rfp.office}`}
                </>
              )}
            </p>
            {rfp.description && (
              <p className="mt-2 text-sm text-gray-700 line-clamp-2">
                {searchTerm ? (
                  <HighlightedText text={rfp.description} searchTerm={searchTerm} />
                ) : (
                  rfp.description
                )}
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
              {searchTerm ? (
                <HighlightedText text={rfp.category || 'General'} searchTerm={searchTerm} />
              ) : (
                rfp.category || 'General'
              )}
            </Badge>
            {rfp.naics_code && (
              <span>
                NAICS:{' '}
                {searchTerm ? (
                  <HighlightedText text={rfp.naics_code} searchTerm={searchTerm} />
                ) : (
                  rfp.naics_code
                )}
              </span>
            )}
          </div>

          <div className="flex items-center space-x-2">
            <GenerateBidButton rfpId={rfp.rfp_id} rfpTitle={rfp.title} />
            <Button
              variant="ghost"
              size="sm"
              onClick={(e) => {
                e.stopPropagation()
                navigate(`/rfps/${rfp.rfp_id}?chat=open`)
              }}
              title="Chat with AI about this RFP"
            >
              <MessageSquare className="h-4 w-4" />
            </Button>
            <Button
              onClick={() => onTriageDecision(rfp.rfp_id, 'approve')}
              size="sm"
              variant="default"
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
            <div className="ml-2 flex items-center text-gray-400 group-hover:text-primary-500 transition-colors">
              <span className="text-xs mr-1 hidden sm:inline">View</span>
              <ChevronRight className="w-4 h-4" />
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
