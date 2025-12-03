import { useState, useRef, useCallback, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft,
  RefreshCw,
  FileText,
  MessageSquare,
  Building2,
  Clock,
  ExternalLink,
  Download,
  Sparkles,
  AlertCircle,
  CheckCircle2,
  Loader2,
  FileIcon,
  FileOutput,
  Copy,
  Check,
  DollarSign,
  Wand2,
  Upload,
  Trash2,
  FileUp,
  Archive,
  Edit3,
  Send,
  Bot,
  User,
  CalendarDays,
  Shield,
  History,
  Play,
  XCircle,
  ChevronRight,
  MoreVertical,
} from 'lucide-react'
import { toast } from 'sonner'
import { format, formatDistanceToNow } from 'date-fns'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Skeleton } from '@/components/ui/skeleton'
import { Input } from '@/components/ui/input'
import { Progress } from '@/components/ui/progress'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { api } from '@/services/api'
import PricingTable from '@/components/PricingTable'

interface RFPDocument {
  id: number
  filename: string
  file_type: string | null
  file_size: number | null
  document_type: string | null
  source_url: string | null
  downloaded_at: string | null
  download_status: 'completed' | 'pending' | 'failed'
}

interface UploadedDocument {
  id: string
  filename: string
  file_type: string
  file_size: number
  uploaded_at: string
  status: string
  chunks_count: number | null
  error: string | null
}

interface RFPQandA {
  id: number
  question_number: string | null
  question_text: string
  answer_text: string | null
  asked_date: string | null
  answered_date: string | null
  category: string | null
  key_insights: string[]
  is_new: boolean
}

interface CompanyProfile {
  id: number
  name: string
  is_default: boolean
}

interface ComplianceRequirement {
  id: string
  requirement_text: string
  category: string
  priority: 'high' | 'medium' | 'low'
  status: 'met' | 'partial' | 'not_met' | 'pending'
  response_notes?: string
  source_section?: string
}

interface ActivityEvent {
  id: number
  from_stage: string | null
  to_stage: string
  timestamp: string
  user: string | null
  automated: boolean
  notes: string | null
  event_metadata: Record<string, any>
}

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

type GenerationMode = 'template' | 'claude_standard' | 'claude_enhanced' | 'claude_premium'

interface BidDocument {
  bid_id: string
  rfp_id: string
  generated_at: string
  preview: {
    markdown: string
    sections: string[]
  }
  metadata: {
    generated_at: string
    processing_mode?: string
    generation_mode?: string
    claude_enhanced?: boolean
    thinking_enabled?: boolean
  }
}

const GENERATION_MODES: { value: GenerationMode; label: string; description: string; icon: string }[] = [
  {
    value: 'template',
    label: 'Fast Draft',
    description: 'Quick template-based generation (no AI)',
    icon: '⚡'
  },
  {
    value: 'claude_standard',
    label: 'AI Standard',
    description: 'Claude Sonnet 4.5 without thinking',
    icon: '🤖'
  },
  {
    value: 'claude_enhanced',
    label: 'AI Enhanced',
    description: 'Claude Sonnet 4.5 with extended thinking (recommended)',
    icon: '✨'
  },
  {
    value: 'claude_premium',
    label: 'AI Premium',
    description: 'Claude Opus 4.5 with thinking (highest quality)',
    icon: '👑'
  }
]

const categoryColors: Record<string, string> = {
  technical: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
  pricing: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
  scope: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300',
  timeline: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-300',
  compliance: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
  submission: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300',
  evaluation: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-300',
  other: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
}

const fileTypeIcons: Record<string, string> = {
  pdf: '📄',
  docx: '📝',
  doc: '📝',
  xlsx: '📊',
  xls: '📊',
  zip: '📦',
  default: '📎',
}

function formatFileSize(bytes: number | null): string {
  if (!bytes) return 'Unknown size'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function RFPDetail() {
  const { rfpId } = useParams<{ rfpId: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [selectedProfileId, setSelectedProfileId] = useState<string>('')
  const [qaFilter, setQaFilter] = useState<string>('all')
  const [generatedBid, setGeneratedBid] = useState<BidDocument | null>(null)
  const [activeTab, setActiveTab] = useState<string>('overview')
  const [copied, setCopied] = useState(false)
  const [generationMode, setGenerationMode] = useState<GenerationMode>('claude_enhanced')

  // Chat state
  const [chatMessage, setChatMessage] = useState('')
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([])
  const [isChatOpen, setIsChatOpen] = useState(false)
  const chatScrollRef = useRef<HTMLDivElement>(null)

  // Dialog state
  const [showArchiveDialog, setShowArchiveDialog] = useState(false)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)

  // Fetch RFP data
  const { data: rfp, isLoading: rfpLoading, error: rfpError } = useQuery({
    queryKey: ['rfp', rfpId],
    queryFn: () => api.getRFP(rfpId!),
    enabled: !!rfpId,
  })

  // Fetch documents
  const { data: documents, isLoading: docsLoading } = useQuery({
    queryKey: ['rfp-documents', rfpId],
    queryFn: () => api.getRFPDocuments(rfpId!),
    enabled: !!rfpId,
  })

  // Fetch Q&A
  const { data: qaItems, isLoading: qaLoading } = useQuery({
    queryKey: ['rfp-qa', rfpId],
    queryFn: () => api.getRFPQandA(rfpId!),
    enabled: !!rfpId,
  })

  // Fetch company profiles
  const { data: profiles } = useQuery({
    queryKey: ['company-profiles'],
    queryFn: () => api.getCompanyProfiles(),
  })

  // Fetch uploaded documents
  const { data: uploadedDocs, isLoading: uploadedDocsLoading } = useQuery({
    queryKey: ['uploaded-documents', rfpId],
    queryFn: () => api.getUploadedDocuments(rfpId!),
    enabled: !!rfpId,
  })

  // Fetch compliance matrix
  const { data: complianceMatrix, isLoading: complianceLoading } = useQuery({
    queryKey: ['rfp-compliance', rfpId],
    queryFn: () => api.getComplianceMatrix(rfpId!),
    enabled: !!rfpId,
  })

  // Fetch activity log
  const { data: activityLog, isLoading: activityLoading } = useQuery({
    queryKey: ['rfp-activity', rfpId],
    queryFn: () => api.getActivityLog(rfpId!),
    enabled: !!rfpId,
  })

  // File upload ref
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [isDragging, setIsDragging] = useState(false)

  // Auto-select company profile when RFP or profiles load
  useEffect(() => {
    if (!selectedProfileId && profiles && profiles.length > 0) {
      // Priority 1: Use RFP's associated profile
      if (rfp?.company_profile_id) {
        setSelectedProfileId(rfp.company_profile_id.toString())
      }
      // Priority 2: Auto-select first profile if only one exists
      else if (profiles.length === 1) {
        setSelectedProfileId(profiles[0].id.toString())
      }
    }
  }, [rfp, profiles, selectedProfileId])

  // Refresh mutation
  const refreshMutation = useMutation({
    mutationFn: () => api.refreshRFP(rfpId!),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['rfp', rfpId] })
      queryClient.invalidateQueries({ queryKey: ['rfp-documents', rfpId] })
      queryClient.invalidateQueries({ queryKey: ['rfp-qa', rfpId] })
      if (data.has_changes) {
        toast.success('RFP Updated', {
          description: `Found ${data.new_qa_count} new Q&A and ${data.new_document_count} new documents`,
        })
      } else {
        toast.info('No changes detected')
      }
    },
    onError: (error: Error) => {
      toast.error('Refresh failed', { description: error.message })
    },
  })

  // Analyze Q&A mutation
  const analyzeMutation = useMutation({
    mutationFn: () => api.analyzeRFPQandA(rfpId!),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['rfp-qa', rfpId] })
      toast.success('Q&A Analysis Complete', {
        description: `Analyzed ${data.analyzed_count} items`,
      })
    },
    onError: (error: Error) => {
      toast.error('Analysis failed', { description: error.message })
    },
  })

  // Generate proposal mutation
  const generateMutation = useMutation({
    mutationFn: () => api.generateBid(rfpId!, {
      generation_mode: generationMode,
      enable_thinking: generationMode !== 'template' && generationMode !== 'claude_standard',
      thinking_budget: generationMode === 'claude_premium' ? 20000 : 10000
    }),
    onSuccess: (data: BidDocument) => {
      setGeneratedBid(data)
      setActiveTab('proposal')
      const modeLabel = GENERATION_MODES.find(m => m.value === generationMode)?.label || generationMode
      toast.success('Proposal generated successfully', {
        description: `Generated with ${modeLabel} mode • Bid ID: ${data.bid_id}`,
      })
    },
    onError: (error: Error) => {
      toast.error('Generation failed', { description: error.message })
    },
  })

  // Upload document mutation
  const uploadMutation = useMutation({
    mutationFn: (file: File) => api.uploadDocument(rfpId!, file),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['uploaded-documents', rfpId] })
      toast.success('Document uploaded', {
        description: `${data.filename} is being processed`,
      })
    },
    onError: (error: Error) => {
      toast.error('Upload failed', { description: error.message })
    },
  })

  // Delete uploaded document mutation
  const deleteUploadedMutation = useMutation({
    mutationFn: (documentId: string) => api.deleteUploadedDocument(rfpId!, documentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['uploaded-documents', rfpId] })
      toast.success('Document deleted')
    },
    onError: (error: Error) => {
      toast.error('Delete failed', { description: error.message })
    },
  })

  // Archive RFP mutation
  const archiveMutation = useMutation({
    mutationFn: () => api.archiveRFP(rfpId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rfp', rfpId] })
      queryClient.invalidateQueries({ queryKey: ['rfp-activity', rfpId] })
      toast.success('RFP archived successfully')
      setShowArchiveDialog(false)
    },
    onError: (error: Error) => {
      toast.error('Archive failed', { description: error.message })
    },
  })

  // Delete RFP mutation
  const deleteMutation = useMutation({
    mutationFn: () => api.deleteRFP(rfpId!),
    onSuccess: () => {
      toast.success('RFP deleted successfully')
      navigate('/discovery')
    },
    onError: (error: Error) => {
      toast.error('Delete failed', { description: error.message })
    },
  })

  // Advance stage mutation
  const advanceStageMutation = useMutation({
    mutationFn: () => api.advanceStage(rfpId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rfp', rfpId] })
      queryClient.invalidateQueries({ queryKey: ['rfp-activity', rfpId] })
      toast.success('Stage advanced successfully')
    },
    onError: (error: Error) => {
      toast.error('Failed to advance stage', { description: error.message })
    },
  })

  // Chat mutation
  const chatMutation = useMutation({
    mutationFn: (message: string) => api.sendChatMessage(rfpId!, message),
    onSuccess: (data) => {
      setChatMessages(prev => [
        ...prev,
        {
          id: `user-${Date.now()}`,
          role: 'user',
          content: chatMessage,
          timestamp: new Date().toISOString(),
        },
        {
          id: data.message_id || `assistant-${Date.now()}`,
          role: 'assistant',
          content: data.response,
          timestamp: new Date().toISOString(),
        },
      ])
      setChatMessage('')
      // Scroll to bottom
      setTimeout(() => {
        chatScrollRef.current?.scrollTo({ top: chatScrollRef.current.scrollHeight, behavior: 'smooth' })
      }, 100)
    },
    onError: (error: Error) => {
      toast.error('Chat failed', { description: error.message })
    },
  })

  // Handle sending chat message
  const handleSendMessage = () => {
    if (!chatMessage.trim()) return
    chatMutation.mutate(chatMessage)
  }

  // Handle file upload
  const handleFileUpload = useCallback((files: FileList | null) => {
    if (!files) return
    Array.from(files).forEach((file) => {
      uploadMutation.mutate(file)
    })
  }, [uploadMutation])

  // Handle drag and drop
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    handleFileUpload(e.dataTransfer.files)
  }, [handleFileUpload])

  // Download bid document
  const downloadBid = async (format: 'markdown' | 'html' | 'json') => {
    if (!generatedBid) return
    try {
      const blob = await api.downloadBid(generatedBid.bid_id, format)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      const ext = format === 'markdown' ? 'md' : format
      a.download = `proposal_${rfpId}_${generatedBid.bid_id}.${ext}`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
      toast.success(`Downloaded as ${format.toUpperCase()}`)
    } catch {
      toast.error('Download failed')
    }
  }

  // Copy markdown to clipboard
  const copyToClipboard = async () => {
    if (!generatedBid) return
    try {
      await navigator.clipboard.writeText(generatedBid.preview.markdown)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
      toast.success('Copied to clipboard')
    } catch {
      toast.error('Copy failed')
    }
  }

  // Download document
  const handleDownload = async (doc: RFPDocument) => {
    try {
      const blob = await api.downloadRFPDocument(rfpId!, doc.id)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = doc.filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
    } catch {
      toast.error('Download failed')
    }
  }

  // Filter Q&A by category
  const filteredQA = qaItems?.filter((qa: RFPQandA) => {
    if (qaFilter === 'all') return true
    if (qaFilter === 'new') return qa.is_new
    return qa.category === qaFilter
  })

  // Loading state
  if (rfpLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }

  // Error state
  if (rfpError || !rfp) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <AlertCircle className="h-12 w-12 text-red-500 mb-4" />
        <h2 className="text-xl font-semibold mb-2">RFP Not Found</h2>
        <p className="text-muted-foreground mb-4">
          The requested RFP could not be found.
        </p>
        <Button onClick={() => navigate('/discovery')}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Discovery
        </Button>
      </div>
    )
  }

  const deadlineDate = rfp.response_deadline ? new Date(rfp.response_deadline) : null
  const isDeadlinePast = deadlineDate && deadlineDate < new Date()
  const deadlineUrgent = deadlineDate && !isDeadlinePast &&
    (deadlineDate.getTime() - Date.now()) < 7 * 24 * 60 * 60 * 1000 // 7 days

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={() => navigate('/discovery')}>
              <ArrowLeft className="h-4 w-4" />
            </Button>
            <h1 className="text-2xl font-bold">{rfp.title}</h1>
          </div>
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            {rfp.agency && (
              <span className="flex items-center gap-1">
                <Building2 className="h-4 w-4" />
                {rfp.agency}
              </span>
            )}
            {rfp.solicitation_number && (
              <span>#{rfp.solicitation_number}</span>
            )}
            {rfp.source_platform && (
              <Badge variant="outline">{rfp.source_platform}</Badge>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {rfp.source_url && (
            <Button variant="outline" size="sm" asChild>
              <a href={rfp.source_url} target="_blank" rel="noopener noreferrer">
                <ExternalLink className="h-4 w-4 mr-2" />
                View Original
              </a>
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={() => refreshMutation.mutate()}
            disabled={refreshMutation.isPending}
          >
            {refreshMutation.isPending ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4 mr-2" />
            )}
            Refresh
          </Button>
          {/* Generation Mode Selector */}
          <Select
            value={generationMode}
            onValueChange={(value: GenerationMode) => setGenerationMode(value)}
          >
            <SelectTrigger className="w-44">
              <SelectValue>
                <span className="flex items-center gap-2">
                  {GENERATION_MODES.find(m => m.value === generationMode)?.icon}
                  {GENERATION_MODES.find(m => m.value === generationMode)?.label}
                </span>
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              {GENERATION_MODES.map((mode) => (
                <SelectItem key={mode.value} value={mode.value}>
                  <div className="flex flex-col">
                    <span className="flex items-center gap-2">
                      {mode.icon} {mode.label}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {mode.description}
                    </span>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            onClick={() => generateMutation.mutate()}
            disabled={generateMutation.isPending}
            className={generationMode.includes('claude') ? 'bg-purple-600 hover:bg-purple-700' : ''}
          >
            {generateMutation.isPending ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4 mr-2" />
            )}
            Generate Proposal
          </Button>
          <Button
            variant="outline"
            onClick={() => navigate(`/rfps/${rfpId}/copilot`)}
          >
            <Wand2 className="h-4 w-4 mr-2" />
            AI Copilot
          </Button>
          {/* Actions Dropdown Menu */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm">
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => navigate(`/rfps/${rfpId}/copilot`)}>
                <Edit3 className="h-4 w-4 mr-2" />
                Edit Proposal
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => advanceStageMutation.mutate()}
                disabled={advanceStageMutation.isPending}
              >
                <Play className="h-4 w-4 mr-2" />
                Advance to Next Stage
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => navigate('/pipeline')}>
                <ChevronRight className="h-4 w-4 mr-2" />
                View in Pipeline
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => setShowArchiveDialog(true)}>
                <Archive className="h-4 w-4 mr-2" />
                Archive RFP
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => setShowDeleteDialog(true)}
                className="text-red-600"
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Delete RFP
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Archive Confirmation Dialog */}
      <Dialog open={showArchiveDialog} onOpenChange={setShowArchiveDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Archive RFP</DialogTitle>
            <DialogDescription>
              This will archive the RFP "{rfp.title}". Archived RFPs can be restored later.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowArchiveDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => archiveMutation.mutate()}
              disabled={archiveMutation.isPending}
            >
              {archiveMutation.isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Archive
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete RFP</DialogTitle>
            <DialogDescription>
              This action cannot be undone. This will permanently delete the RFP "{rfp.title}" and all associated documents, Q&A, and proposals.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeleteDialog(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => deleteMutation.mutate()}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Deadline Banner */}
      {deadlineDate && (
        <Card className={`border-l-4 ${isDeadlinePast ? 'border-l-red-500 bg-red-50 dark:bg-red-950' : deadlineUrgent ? 'border-l-orange-500 bg-orange-50 dark:bg-orange-950' : 'border-l-blue-500'}`}>
          <CardContent className="py-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Clock className={`h-5 w-5 ${isDeadlinePast ? 'text-red-500' : deadlineUrgent ? 'text-orange-500' : 'text-blue-500'}`} />
              <span className="font-medium">
                {isDeadlinePast ? 'Deadline Passed' : 'Response Deadline'}
              </span>
              <span className="text-muted-foreground">
                {format(deadlineDate, 'PPP p')}
              </span>
            </div>
            {!isDeadlinePast && (
              <Badge variant={deadlineUrgent ? 'destructive' : 'secondary'}>
                {formatDistanceToNow(deadlineDate, { addSuffix: true })}
              </Badge>
            )}
          </CardContent>
        </Card>
      )}

      {/* Main Content Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="flex-wrap h-auto gap-1">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="documents" className="gap-2">
            <FileText className="h-4 w-4" />
            Documents
            {documents?.length > 0 && (
              <Badge variant="secondary" className="ml-1">{documents.length}</Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="qa" className="gap-2">
            <MessageSquare className="h-4 w-4" />
            Q&A
            {qaItems?.length > 0 && (
              <Badge variant="secondary" className="ml-1">{qaItems.length}</Badge>
            )}
            {qaItems?.some((qa: RFPQandA) => qa.is_new) && (
              <span className="h-2 w-2 bg-blue-500 rounded-full" />
            )}
          </TabsTrigger>
          <TabsTrigger value="compliance" className="gap-2">
            <Shield className="h-4 w-4" />
            Compliance
            {complianceMatrix?.compliance_score !== undefined && (
              <Badge
                variant={complianceMatrix.compliance_score >= 80 ? 'default' : complianceMatrix.compliance_score >= 60 ? 'secondary' : 'destructive'}
                className="ml-1"
              >
                {Math.round(complianceMatrix.compliance_score)}%
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="proposal" className="gap-2" disabled={!generatedBid}>
            <FileOutput className="h-4 w-4" />
            Proposal
            {generatedBid && (
              <Badge variant="default" className="ml-1 bg-green-500">Ready</Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="pricing" className="gap-2">
            <DollarSign className="h-4 w-4" />
            Pricing
          </TabsTrigger>
          <TabsTrigger value="activity" className="gap-2">
            <History className="h-4 w-4" />
            Activity
            {activityLog?.length > 0 && (
              <Badge variant="secondary" className="ml-1">{activityLog.length}</Badge>
            )}
          </TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-4">
          {/* Description Section */}
          {rfp.description && (
            <Card>
              <CardHeader>
                <CardTitle>Description</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="whitespace-pre-wrap">{rfp.description}</p>
              </CardContent>
            </Card>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* RFP Details Card */}
            <Card>
              <CardHeader>
                <CardTitle>RFP Details</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  {rfp.naics_code && (
                    <div>
                      <label className="text-sm font-medium text-muted-foreground">NAICS Code</label>
                      <p className="mt-1 font-mono">{rfp.naics_code}</p>
                    </div>
                  )}
                  {rfp.rfp_metadata?.psc_codes?.length > 0 && (
                    <div>
                      <label className="text-sm font-medium text-muted-foreground">PSC Codes</label>
                      <p className="mt-1 font-mono">{rfp.rfp_metadata.psc_codes.join(', ')}</p>
                    </div>
                  )}
                  {rfp.category && (
                    <div>
                      <label className="text-sm font-medium text-muted-foreground">Category</label>
                      <p className="mt-1">{rfp.category}</p>
                    </div>
                  )}
                  {rfp.estimated_value && (
                    <div>
                      <label className="text-sm font-medium text-muted-foreground">Estimated Value</label>
                      <p className="mt-1 font-semibold text-green-600">${rfp.estimated_value.toLocaleString()}</p>
                    </div>
                  )}
                  {rfp.award_amount && (
                    <div>
                      <label className="text-sm font-medium text-muted-foreground">Award Amount</label>
                      <p className="mt-1 font-semibold text-green-600">${rfp.award_amount.toLocaleString()}</p>
                    </div>
                  )}
                </div>

                {/* Set-Asides */}
                {rfp.rfp_metadata?.set_asides?.length > 0 && (
                  <div className="pt-2 border-t">
                    <label className="text-sm font-medium text-muted-foreground">Set-Asides</label>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {rfp.rfp_metadata.set_asides.map((setAside: string, i: number) => (
                        <Badge key={i} variant="outline" className="text-xs">
                          {setAside}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {rfp.last_scraped_at && (
                  <div className="text-xs text-muted-foreground pt-2 border-t">
                    Last updated: {formatDistanceToNow(new Date(rfp.last_scraped_at), { addSuffix: true })}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Timeline Card */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <CalendarDays className="h-5 w-5" />
                  Key Dates
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {rfp.posted_date && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Posted</span>
                    <span className="text-sm font-medium">{format(new Date(rfp.posted_date), 'PPP')}</span>
                  </div>
                )}
                {rfp.rfp_metadata?.qa_deadline && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Q&A Deadline</span>
                    <span className="text-sm font-medium">{format(new Date(rfp.rfp_metadata.qa_deadline), 'PPP')}</span>
                  </div>
                )}
                {rfp.response_deadline && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Response Due</span>
                    <span className={`text-sm font-medium ${isDeadlinePast ? 'text-red-500' : deadlineUrgent ? 'text-orange-500' : ''}`}>
                      {format(new Date(rfp.response_deadline), 'PPP')}
                    </span>
                  </div>
                )}
                {rfp.award_date && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Expected Award</span>
                    <span className="text-sm font-medium">{format(new Date(rfp.award_date), 'PPP')}</span>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Company Profile Card */}
            <Card>
              <CardHeader>
                <CardTitle>Company Profile</CardTitle>
                <CardDescription>
                  Select the company profile to use for proposal generation
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Select
                  value={selectedProfileId || rfp.company_profile_id?.toString() || ''}
                  onValueChange={setSelectedProfileId}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select a company profile" />
                  </SelectTrigger>
                  <SelectContent>
                    {profiles?.map((profile: CompanyProfile) => (
                      <SelectItem key={profile.id} value={profile.id.toString()}>
                        <span className="flex items-center gap-2">
                          <Building2 className="h-4 w-4" />
                          {profile.name}
                          {profile.is_default && (
                            <Badge variant="secondary" className="text-xs">Default</Badge>
                          )}
                        </span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {profiles?.length === 0 && (
                  <p className="text-sm text-muted-foreground mt-2">
                    No company profiles found.{' '}
                    <a href="/profiles" className="text-blue-500 hover:underline">
                      Create one
                    </a>
                  </p>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Pipeline Status Card */}
          <Card>
            <CardHeader>
              <CardTitle>Pipeline Status</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2">
                <Badge variant={rfp.current_stage === 'submitted' ? 'default' : 'secondary'}>
                  {rfp.current_stage?.replace(/_/g, ' ').toUpperCase()}
                </Badge>
                <span className="text-sm text-muted-foreground">
                  RFP ID: {rfp.rfp_id}
                </span>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Documents Tab */}
        <TabsContent value="documents">
          <div className="space-y-4">
            {/* Upload Section */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Upload className="h-5 w-5" />
                  Upload Documents
                </CardTitle>
                <CardDescription>
                  Upload PDF, DOCX, TXT, or Excel files to add to the RFP context
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div
                  className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                    isDragging
                      ? 'border-blue-500 bg-blue-50 dark:bg-blue-950'
                      : 'border-gray-300 dark:border-gray-700 hover:border-gray-400'
                  }`}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    className="hidden"
                    accept=".pdf,.docx,.doc,.txt,.md,.xlsx,.xls"
                    multiple
                    onChange={(e) => handleFileUpload(e.target.files)}
                  />
                  <FileUp className="h-10 w-10 mx-auto mb-4 text-muted-foreground" />
                  <p className="text-sm text-muted-foreground mb-2">
                    Drag and drop files here, or
                  </p>
                  <Button
                    variant="outline"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={uploadMutation.isPending}
                  >
                    {uploadMutation.isPending ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <Upload className="h-4 w-4 mr-2" />
                    )}
                    Browse Files
                  </Button>
                  <p className="text-xs text-muted-foreground mt-2">
                    Supported: PDF, DOCX, DOC, TXT, MD, XLSX, XLS (max 50MB)
                  </p>
                </div>

                {/* Uploaded Documents List */}
                {(uploadedDocs?.documents?.length > 0 || uploadedDocsLoading) && (
                  <div className="mt-4">
                    <h4 className="text-sm font-medium mb-2">Uploaded Documents</h4>
                    {uploadedDocsLoading ? (
                      <Skeleton className="h-12 w-full" />
                    ) : (
                      <div className="divide-y">
                        {uploadedDocs?.documents?.map((doc: UploadedDocument) => (
                          <div
                            key={doc.id}
                            className="flex items-center justify-between py-3 hover:bg-muted/50 rounded px-2 -mx-2"
                          >
                            <div className="flex items-center gap-3">
                              <span className="text-2xl">
                                {fileTypeIcons[doc.file_type] || fileTypeIcons.default}
                              </span>
                              <div>
                                <p className="font-medium">{doc.filename}</p>
                                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                  <Badge
                                    variant={doc.status === 'completed' ? 'default' : doc.status === 'processing' ? 'secondary' : 'destructive'}
                                    className="text-xs"
                                  >
                                    {doc.status === 'completed' && <CheckCircle2 className="h-3 w-3 mr-1" />}
                                    {doc.status === 'processing' && <Loader2 className="h-3 w-3 mr-1 animate-spin" />}
                                    {doc.status}
                                  </Badge>
                                  <span>{formatFileSize(doc.file_size)}</span>
                                  {doc.chunks_count && (
                                    <span>{doc.chunks_count} chunks indexed</span>
                                  )}
                                </div>
                              </div>
                            </div>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => deleteUploadedMutation.mutate(doc.id)}
                              disabled={deleteUploadedMutation.isPending}
                            >
                              <Trash2 className="h-4 w-4 text-red-500" />
                            </Button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Scraped Documents Section */}
            <Card>
              <CardHeader>
                <CardTitle>RFP Documents</CardTitle>
                <CardDescription>
                  Documents downloaded from the RFP posting
                </CardDescription>
              </CardHeader>
              <CardContent>
                {docsLoading ? (
                  <div className="space-y-2">
                    <Skeleton className="h-12 w-full" />
                    <Skeleton className="h-12 w-full" />
                    <Skeleton className="h-12 w-full" />
                  </div>
                ) : documents?.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <FileIcon className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>No documents found</p>
                    <p className="text-sm mt-1">
                      Click Refresh to check for new documents
                    </p>
                  </div>
                ) : (
                  <div className="divide-y">
                    {documents?.map((doc: RFPDocument) => (
                      <div
                        key={doc.id}
                        className="flex items-center justify-between py-3 hover:bg-muted/50 rounded px-2 -mx-2"
                      >
                        <div className="flex items-center gap-3">
                          <span className="text-2xl">
                            {fileTypeIcons[doc.file_type || ''] || fileTypeIcons.default}
                          </span>
                          <div>
                            <p className="font-medium">{doc.filename}</p>
                            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                              {doc.document_type && (
                                <Badge variant="outline" className="text-xs">
                                  {doc.document_type}
                                </Badge>
                              )}
                              {doc.download_status === 'pending' && (
                                <Badge variant="secondary" className="text-xs bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200">
                                  <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                                  Downloading...
                                </Badge>
                              )}
                              {doc.download_status === 'failed' && (
                                <Badge variant="destructive" className="text-xs">
                                  Download Failed
                                </Badge>
                              )}
                              {doc.download_status === 'completed' && (
                                <>
                                  <span>{formatFileSize(doc.file_size)}</span>
                                  {doc.downloaded_at && (
                                    <span>
                                      Downloaded {formatDistanceToNow(new Date(doc.downloaded_at), { addSuffix: true })}
                                    </span>
                                  )}
                                </>
                              )}
                            </div>
                          </div>
                        </div>
                        {doc.download_status === 'completed' ? (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDownload(doc)}
                          >
                            <Download className="h-4 w-4" />
                          </Button>
                        ) : doc.download_status === 'failed' && doc.source_url ? (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => window.open(doc.source_url!, '_blank')}
                            title="Open source URL"
                          >
                            <ExternalLink className="h-4 w-4" />
                          </Button>
                        ) : (
                          <div className="w-8" /> // Spacer for pending items
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Q&A Tab */}
        <TabsContent value="qa">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Questions & Answers</CardTitle>
                  <CardDescription>
                    Q&A from the RFP portal with AI-powered analysis
                  </CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  <Select value={qaFilter} onValueChange={setQaFilter}>
                    <SelectTrigger className="w-40">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Categories</SelectItem>
                      <SelectItem value="new">New Only</SelectItem>
                      <SelectItem value="technical">Technical</SelectItem>
                      <SelectItem value="pricing">Pricing</SelectItem>
                      <SelectItem value="scope">Scope</SelectItem>
                      <SelectItem value="timeline">Timeline</SelectItem>
                      <SelectItem value="compliance">Compliance</SelectItem>
                      <SelectItem value="submission">Submission</SelectItem>
                      <SelectItem value="evaluation">Evaluation</SelectItem>
                    </SelectContent>
                  </Select>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => analyzeMutation.mutate()}
                    disabled={analyzeMutation.isPending || !qaItems?.length}
                  >
                    {analyzeMutation.isPending ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <Sparkles className="h-4 w-4 mr-2" />
                    )}
                    Analyze Q&A
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {qaLoading ? (
                <div className="space-y-4">
                  <Skeleton className="h-24 w-full" />
                  <Skeleton className="h-24 w-full" />
                  <Skeleton className="h-24 w-full" />
                </div>
              ) : filteredQA?.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <MessageSquare className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No Q&A found</p>
                  <p className="text-sm mt-1">
                    Click Refresh to check for new questions and answers
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  {filteredQA?.map((qa: RFPQandA) => (
                    <div
                      key={qa.id}
                      className={`p-4 rounded-lg border ${qa.is_new ? 'border-blue-200 bg-blue-50/50 dark:border-blue-800 dark:bg-blue-950/50' : ''}`}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center gap-2">
                          {qa.question_number && (
                            <Badge variant="outline">{qa.question_number}</Badge>
                          )}
                          {qa.category && (
                            <Badge className={categoryColors[qa.category] || categoryColors.other}>
                              {qa.category}
                            </Badge>
                          )}
                          {qa.is_new && (
                            <Badge variant="default" className="bg-blue-500">New</Badge>
                          )}
                        </div>
                        {qa.answered_date && (
                          <span className="text-xs text-muted-foreground">
                            Answered {formatDistanceToNow(new Date(qa.answered_date), { addSuffix: true })}
                          </span>
                        )}
                      </div>

                      <div className="space-y-3">
                        <div>
                          <p className="font-medium text-sm text-muted-foreground mb-1">Question:</p>
                          <p>{qa.question_text}</p>
                        </div>

                        {qa.answer_text ? (
                          <div>
                            <p className="font-medium text-sm text-muted-foreground mb-1 flex items-center gap-1">
                              <CheckCircle2 className="h-4 w-4 text-green-500" />
                              Answer:
                            </p>
                            <p className="text-muted-foreground">{qa.answer_text}</p>
                          </div>
                        ) : (
                          <div className="flex items-center gap-1 text-sm text-orange-600 dark:text-orange-400">
                            <Clock className="h-4 w-4" />
                            Awaiting answer
                          </div>
                        )}

                        {qa.key_insights && qa.key_insights.length > 0 && (
                          <div className="pt-2 border-t">
                            <p className="font-medium text-sm text-muted-foreground mb-1 flex items-center gap-1">
                              <Sparkles className="h-4 w-4 text-purple-500" />
                              AI Insights:
                            </p>
                            <ul className="list-disc list-inside text-sm text-muted-foreground space-y-1">
                              {qa.key_insights.map((insight: string, i: number) => (
                                <li key={i}>{insight}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Proposal Tab */}
        <TabsContent value="proposal">
          {generatedBid ? (
            <div className="space-y-4">
              {/* Proposal Header */}
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="flex items-center gap-2">
                        <CheckCircle2 className="h-5 w-5 text-green-500" />
                        Proposal Generated
                      </CardTitle>
                      <CardDescription>
                        Bid ID: {generatedBid.bid_id} • Generated {format(new Date(generatedBid.generated_at), 'PPp')}
                      </CardDescription>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={copyToClipboard}
                      >
                        {copied ? (
                          <Check className="h-4 w-4 mr-2" />
                        ) : (
                          <Copy className="h-4 w-4 mr-2" />
                        )}
                        {copied ? 'Copied!' : 'Copy'}
                      </Button>
                      <Select onValueChange={(format: 'markdown' | 'html' | 'json') => downloadBid(format)}>
                        <SelectTrigger className="w-36">
                          <Download className="h-4 w-4 mr-2" />
                          <SelectValue placeholder="Download" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="markdown">Markdown (.md)</SelectItem>
                          <SelectItem value="html">HTML (.html)</SelectItem>
                          <SelectItem value="json">JSON (.json)</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </CardHeader>
              </Card>

              {/* Sections Overview */}
              {generatedBid.preview.sections.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle>Document Sections</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-2">
                      {generatedBid.preview.sections.map((section, i) => (
                        <Badge key={i} variant="secondary">
                          {section.replace(/_/g, ' ')}
                        </Badge>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Proposal Preview */}
              <Card>
                <CardHeader>
                  <CardTitle>Proposal Preview</CardTitle>
                  <CardDescription>
                    {generatedBid.metadata.processing_mode === 'mock'
                      ? 'Preview generated in mock mode (ML components not available)'
                      : generatedBid.metadata.claude_enhanced
                      ? `Generated with Claude ${generatedBid.metadata.generation_mode?.includes('premium') ? 'Opus 4.5' : 'Sonnet 4.5'}${generatedBid.metadata.thinking_enabled ? ' + Extended Thinking' : ''}`
                      : 'Full AI-generated proposal based on RAG retrieval and compliance analysis'}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="bg-muted rounded-lg p-4 max-h-[600px] overflow-y-auto">
                    <pre className="whitespace-pre-wrap font-mono text-sm">
                      {generatedBid.preview.markdown}
                    </pre>
                  </div>
                  {generatedBid.preview.markdown.endsWith('...') && (
                    <p className="text-sm text-muted-foreground mt-2">
                      Showing preview only. Download the full document for complete content.
                    </p>
                  )}
                </CardContent>
              </Card>

              {/* Regenerate Button */}
              <div className="flex justify-center">
                <Button
                  variant="outline"
                  onClick={() => generateMutation.mutate()}
                  disabled={generateMutation.isPending}
                >
                  {generateMutation.isPending ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <RefreshCw className="h-4 w-4 mr-2" />
                  )}
                  Regenerate Proposal
                </Button>
              </div>
            </div>
          ) : (
            <Card>
              <CardContent className="py-12">
                <div className="text-center">
                  <FileOutput className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-50" />
                  <h3 className="font-semibold mb-2">No Proposal Generated Yet</h3>
                  <p className="text-muted-foreground mb-4">
                    Click "Generate Proposal" to create a proposal for this RFP.
                  </p>
                  <Button
                    onClick={() => generateMutation.mutate()}
                    disabled={generateMutation.isPending}
                  >
                    {generateMutation.isPending ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <Sparkles className="h-4 w-4 mr-2" />
                    )}
                    Generate Proposal
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Pricing Tab */}
        <TabsContent value="pricing">
          <PricingTable rfpId={rfpId!} />
        </TabsContent>

        {/* Compliance Matrix Tab */}
        <TabsContent value="compliance">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <Shield className="h-5 w-5" />
                    Compliance Matrix
                  </CardTitle>
                  <CardDescription>
                    Extracted requirements and compliance status tracking
                  </CardDescription>
                </div>
                {complianceMatrix && (
                  <div className="text-right">
                    <div className="text-2xl font-bold">
                      {complianceMatrix.requirements_met}/{complianceMatrix.requirements_extracted}
                    </div>
                    <div className="text-sm text-muted-foreground">Requirements Met</div>
                  </div>
                )}
              </div>
            </CardHeader>
            <CardContent>
              {complianceLoading ? (
                <div className="space-y-4">
                  <Skeleton className="h-12 w-full" />
                  <Skeleton className="h-12 w-full" />
                  <Skeleton className="h-12 w-full" />
                </div>
              ) : complianceMatrix?.requirements?.length > 0 ? (
                <div className="space-y-4">
                  {/* Compliance Score Progress */}
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>Compliance Score</span>
                      <span className="font-medium">{Math.round(complianceMatrix.compliance_score || 0)}%</span>
                    </div>
                    <Progress value={complianceMatrix.compliance_score || 0} className="h-2" />
                  </div>

                  {/* Requirements Table */}
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-12">#</TableHead>
                        <TableHead>Requirement</TableHead>
                        <TableHead className="w-24">Category</TableHead>
                        <TableHead className="w-24">Priority</TableHead>
                        <TableHead className="w-24">Status</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {complianceMatrix.requirements.map((req: ComplianceRequirement, idx: number) => (
                        <TableRow key={req.id || idx}>
                          <TableCell className="font-mono text-xs">{idx + 1}</TableCell>
                          <TableCell>
                            <p className="text-sm">{req.requirement_text}</p>
                            {req.response_notes && (
                              <p className="text-xs text-muted-foreground mt-1">{req.response_notes}</p>
                            )}
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline" className="text-xs">
                              {req.category}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <Badge
                              variant={req.priority === 'high' ? 'destructive' : req.priority === 'medium' ? 'default' : 'secondary'}
                              className="text-xs"
                            >
                              {req.priority}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <Badge
                              className={`text-xs ${
                                req.status === 'met' ? 'bg-green-100 text-green-800' :
                                req.status === 'partial' ? 'bg-yellow-100 text-yellow-800' :
                                req.status === 'not_met' ? 'bg-red-100 text-red-800' :
                                'bg-gray-100 text-gray-800'
                              }`}
                            >
                              {req.status === 'met' && <CheckCircle2 className="h-3 w-3 mr-1" />}
                              {req.status === 'not_met' && <XCircle className="h-3 w-3 mr-1" />}
                              {req.status.replace('_', ' ')}
                            </Badge>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <Shield className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No compliance matrix available</p>
                  <p className="text-sm mt-1">
                    Generate a proposal to create a compliance matrix
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Activity Log Tab */}
        <TabsContent value="activity">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <History className="h-5 w-5" />
                Activity Log
              </CardTitle>
              <CardDescription>
                Track all actions and stage transitions for this RFP
              </CardDescription>
            </CardHeader>
            <CardContent>
              {activityLoading ? (
                <div className="space-y-4">
                  <Skeleton className="h-12 w-full" />
                  <Skeleton className="h-12 w-full" />
                  <Skeleton className="h-12 w-full" />
                </div>
              ) : activityLog?.length > 0 ? (
                <div className="relative">
                  {/* Timeline Line */}
                  <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-gray-200 dark:bg-gray-700" />

                  <div className="space-y-4">
                    {activityLog.map((event: ActivityEvent, idx: number) => (
                      <div key={event.id || idx} className="relative flex gap-4 pl-8">
                        {/* Timeline Dot */}
                        <div className={`absolute left-2.5 w-3 h-3 rounded-full border-2 ${
                          event.automated ? 'bg-blue-500 border-blue-500' : 'bg-green-500 border-green-500'
                        }`} />

                        <div className="flex-1 bg-muted/50 rounded-lg p-4">
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                              {event.from_stage && (
                                <>
                                  <Badge variant="outline" className="text-xs">
                                    {event.from_stage.replace(/_/g, ' ')}
                                  </Badge>
                                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                                </>
                              )}
                              <Badge className="text-xs">
                                {event.to_stage.replace(/_/g, ' ')}
                              </Badge>
                            </div>
                            <span className="text-xs text-muted-foreground">
                              {formatDistanceToNow(new Date(event.timestamp), { addSuffix: true })}
                            </span>
                          </div>

                          <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            {event.automated ? (
                              <span className="flex items-center gap-1">
                                <Bot className="h-4 w-4" />
                                Automated
                              </span>
                            ) : (
                              <span className="flex items-center gap-1">
                                <User className="h-4 w-4" />
                                {event.user || 'Unknown user'}
                              </span>
                            )}
                          </div>

                          {event.notes && (
                            <p className="text-sm mt-2">{event.notes}</p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <History className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No activity recorded yet</p>
                  <p className="text-sm mt-1">
                    Actions on this RFP will appear here
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Floating AI Chat Panel */}
      <div className="fixed bottom-6 right-6 z-50">
        {isChatOpen ? (
          <Card className="w-96 shadow-xl border-2">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg flex items-center gap-2">
                  <Bot className="h-5 w-5 text-purple-500" />
                  RFP Assistant
                </CardTitle>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setIsChatOpen(false)}
                >
                  <XCircle className="h-4 w-4" />
                </Button>
              </div>
              <CardDescription className="text-xs">
                Ask questions about this RFP
              </CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              {/* Chat Messages */}
              <ScrollArea className="h-64 px-4" ref={chatScrollRef}>
                {chatMessages.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground text-sm">
                    <Bot className="h-8 w-8 mx-auto mb-2 opacity-50" />
                    <p>How can I help with this RFP?</p>
                    <div className="mt-3 space-y-1">
                      <button
                        className="block w-full text-xs text-left p-2 rounded hover:bg-muted"
                        onClick={() => {
                          setChatMessage("Summarize the key requirements")
                          handleSendMessage()
                        }}
                      >
                        Summarize key requirements
                      </button>
                      <button
                        className="block w-full text-xs text-left p-2 rounded hover:bg-muted"
                        onClick={() => {
                          setChatMessage("What are the compliance risks?")
                          handleSendMessage()
                        }}
                      >
                        What are the compliance risks?
                      </button>
                      <button
                        className="block w-full text-xs text-left p-2 rounded hover:bg-muted"
                        onClick={() => {
                          setChatMessage("Create a win theme strategy")
                          handleSendMessage()
                        }}
                      >
                        Create a win theme strategy
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-3 py-2">
                    {chatMessages.map((msg) => (
                      <div
                        key={msg.id}
                        className={`flex gap-2 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                      >
                        {msg.role === 'assistant' && (
                          <Bot className="h-6 w-6 text-purple-500 flex-shrink-0" />
                        )}
                        <div
                          className={`max-w-[80%] p-2 rounded-lg text-sm ${
                            msg.role === 'user'
                              ? 'bg-purple-500 text-white'
                              : 'bg-muted'
                          }`}
                        >
                          {msg.content}
                        </div>
                        {msg.role === 'user' && (
                          <User className="h-6 w-6 text-gray-400 flex-shrink-0" />
                        )}
                      </div>
                    ))}
                    {chatMutation.isPending && (
                      <div className="flex gap-2">
                        <Bot className="h-6 w-6 text-purple-500 flex-shrink-0" />
                        <div className="bg-muted p-2 rounded-lg">
                          <Loader2 className="h-4 w-4 animate-spin" />
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </ScrollArea>

              {/* Chat Input */}
              <div className="p-4 border-t flex gap-2">
                <Input
                  placeholder="Ask about this RFP..."
                  value={chatMessage}
                  onChange={(e) => setChatMessage(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      handleSendMessage()
                    }
                  }}
                  disabled={chatMutation.isPending}
                />
                <Button
                  size="sm"
                  onClick={handleSendMessage}
                  disabled={!chatMessage.trim() || chatMutation.isPending}
                >
                  <Send className="h-4 w-4" />
                </Button>
              </div>
            </CardContent>
          </Card>
        ) : (
          <Button
            size="lg"
            className="rounded-full h-14 w-14 shadow-lg bg-purple-500 hover:bg-purple-600"
            onClick={() => setIsChatOpen(true)}
          >
            <Bot className="h-6 w-6" />
          </Button>
        )}
      </div>
    </div>
  )
}
