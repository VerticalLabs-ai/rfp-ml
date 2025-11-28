import { api } from '@/services/api'
import { useQuery } from '@tanstack/react-query'
import { format, isValid } from 'date-fns'
import { ArrowDownToLine, CheckSquare, ListChecks, Loader2, Tag } from 'lucide-react'
import React from 'react'
import { useParams } from 'react-router-dom'
import { toast } from 'sonner'

interface ChecklistItem {
  id: string
  description: string
  status: string // pending, in_progress, completed, waived
  assigned_to?: string
  due_date?: string
  notes?: string
  meta?: Record<string, any>
}

interface PostAwardChecklist {
  id: number
  rfp_id: number // This is the internal DB ID, not the string rfp_id
  bid_document_id?: string
  generated_at: string
  status: string
  items: ChecklistItem[]
  summary: Record<string, any>
}

export default function ProjectKickoffPage() {
  const { rfpId } = useParams<{ rfpId: string }>()

  const { data: rfp, isLoading: isLoadingRfp } = useQuery({
    queryKey: ['rfps', rfpId],
    queryFn: () => api.getRFP(rfpId!),
    enabled: !!rfpId,
    meta: { errorMessage: "Failed to load RFP." }, // Generic error message for toast
  })

  const { data: checklist, isLoading: isLoadingChecklist } = useQuery<PostAwardChecklist>({
    queryKey: ['postAwardChecklist', rfp?.id],
    queryFn: ({ queryKey }) => api.getPostAwardChecklist(queryKey[1] as number),
    enabled: !!rfp?.id,
    meta: { errorMessage: "Failed to load checklist." },
  })

  const handleExport = (format: 'json' | 'csv') => {
    if (!checklist) {
      toast.error("No checklist data to export.")
      return
    }
    try {
      const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(checklist, null, 2))
      const downloadAnchorNode = document.createElement('a')
      downloadAnchorNode.setAttribute("href", dataStr)
      downloadAnchorNode.setAttribute("download", `post_award_checklist_${rfpId}.${format}`)
      document.body.appendChild(downloadAnchorNode)
      downloadAnchorNode.click()
      downloadAnchorNode.remove()
      toast.success(`Checklist exported as ${format.toUpperCase()}`)
    } catch (error) {
      console.error("Export failed:", error)
      toast.error("Failed to export checklist.")
    }
  }

  if (isLoadingRfp || isLoadingChecklist) {
    return (
      <div className="flex justify-center items-center h-full">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
        <p className="ml-2 text-slate-600 dark:text-slate-300">Loading Project Kickoff...</p>
      </div>
    )
  }

  if (!rfp) {
    return <div className="text-center text-red-500">RFP not found.</div>
  }

  if (!checklist) {
    return <div className="text-center text-slate-500">No post-award checklist found for this RFP.</div>
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 dark:text-white flex items-center gap-3">
            <ListChecks className="w-8 h-8 text-green-600" />
            Project Kickoff: {rfp.title}
          </h1>
          <p className="text-slate-500 dark:text-slate-400 mt-2">
            Post-award compliance and task management for RFP ID: <span className="font-medium">{rfp.rfp_id}</span>
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => handleExport('json')}
            className="inline-flex items-center px-4 py-2 border border-slate-300 dark:border-slate-600 text-sm font-medium rounded-md text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-700 hover:bg-slate-50 dark:hover:bg-slate-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <ArrowDownToLine className="h-4 w-4 mr-2" />
            Export JSON
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <InfoCard title="Checklist Status" value={checklist.status?.toUpperCase() || 'N/A'} colorClass="text-green-600" />
        <InfoCard title="Total Items" value={checklist.summary?.total_items || 0} />
        <InfoCard title="Pending Items" value={checklist.summary?.pending_items || 0} colorClass="text-yellow-600" />
      </div>

      <div className="bg-white dark:bg-slate-800 shadow rounded-lg overflow-hidden">
        <div className="p-4 border-b border-slate-200 dark:border-slate-700">
          <h2 className="text-xl font-semibold text-slate-900 dark:text-white">Compliance Checklist Items</h2>
        </div>
        <ul className="divide-y divide-slate-200 dark:divide-slate-700">
          {checklist.items?.map((item) => (
            <li key={item.id} className="p-4 flex items-start space-x-3">
              <CheckSquare
                className={`h-6 w-6 flex-shrink-0 ${item.status === 'completed' ? 'text-green-500' : 'text-slate-300 dark:text-slate-600'}`}
              />
              <div className="flex-1">
                <p className="text-lg font-medium text-slate-900 dark:text-white">{item.description}</p>
                <div className="flex items-center text-sm text-slate-500 dark:text-slate-400 mt-1 gap-2">
                  {item.assigned_to && (
                    <span className="inline-flex items-center rounded-full bg-blue-50 dark:bg-blue-900/20 px-2.5 py-0.5 text-xs font-medium text-blue-700 dark:text-blue-300">
                      <Tag className="-ml-0.5 mr-1 h-3 w-3" />
                      {item.assigned_to}
                    </span>
                  )}
                  {item.due_date && (() => {
                    const parsedDate = new Date(item.due_date)
                    return isValid(parsedDate) ? (
                      <span>Due: {format(parsedDate, 'PPP')}</span>
                    ) : null
                  })()}
                  {item.status && (
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium 
                      ${item.status === 'completed' ? 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-300' :
                        item.status === 'in_progress' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-300' :
                          'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-300'}
                     `}>
                      {item.status.replace(/_/g, ' ').toUpperCase()}
                    </span>
                  )}
                </div>
                {item.notes && <p className="text-sm text-slate-600 dark:text-slate-300 mt-2">Notes: {item.notes}</p>}
                {item.meta && Object.keys(item.meta).length > 0 && (
                  <div className="text-xs text-slate-400 dark:text-slate-500 mt-2">
                    <span className="font-medium">Meta:</span> {JSON.stringify(item.meta)}
                  </div>
                )}
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

interface InfoCardProps {
  title: string
  value: string | number | undefined // Value can be undefined
  colorClass?: string
}

const InfoCard: React.FC<InfoCardProps> = ({ title, value, colorClass = "text-slate-900 dark:text-white" }) => (
  <div className="bg-white dark:bg-slate-800 shadow rounded-lg p-5 border border-slate-200 dark:border-slate-700">
    <p className="text-sm font-medium text-slate-500 dark:text-slate-400 truncate">{title}</p>
    <p className={`mt-1 text-3xl font-semibold ${colorClass}`}>{value !== undefined ? value : 'N/A'}</p>
  </div>
)
