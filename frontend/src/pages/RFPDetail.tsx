import { useState } from 'react'
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
  Check
} from 'lucide-react'
import { toast } from 'sonner'
import { format, formatDistanceToNow } from 'date-fns'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { api } from '@/services/api'

interface RFPDocument {
  id: number
  filename: string
  file_type: string | null
  file_size: number | null
  document_type: string | null
  downloaded_at: string | null
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
  }
}

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
    mutationFn: () => api.generateBid(rfpId!),
    onSuccess: (data: BidDocument) => {
      setGeneratedBid(data)
      setActiveTab('proposal')
      toast.success('Proposal generated successfully', {
        description: `Bid ID: ${data.bid_id}`,
      })
    },
    onError: (error: Error) => {
      toast.error('Generation failed', { description: error.message })
    },
  })

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
        <div className="flex gap-2">
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
      </div>

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
        <TabsList>
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
          <TabsTrigger value="proposal" className="gap-2" disabled={!generatedBid}>
            <FileOutput className="h-4 w-4" />
            Proposal
            {generatedBid && (
              <Badge variant="default" className="ml-1 bg-green-500">Ready</Badge>
            )}
          </TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* RFP Details Card */}
            <Card>
              <CardHeader>
                <CardTitle>RFP Details</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {rfp.description && (
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">Description</label>
                    <p className="mt-1">{rfp.description}</p>
                  </div>
                )}
                <div className="grid grid-cols-2 gap-4">
                  {rfp.naics_code && (
                    <div>
                      <label className="text-sm font-medium text-muted-foreground">NAICS Code</label>
                      <p className="mt-1 font-mono">{rfp.naics_code}</p>
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
                      <p className="mt-1 font-semibold">${rfp.estimated_value.toLocaleString()}</p>
                    </div>
                  )}
                  {rfp.posted_date && (
                    <div>
                      <label className="text-sm font-medium text-muted-foreground">Posted Date</label>
                      <p className="mt-1">{format(new Date(rfp.posted_date), 'PPP')}</p>
                    </div>
                  )}
                </div>
                {rfp.last_scraped_at && (
                  <div className="text-xs text-muted-foreground pt-2 border-t">
                    Last updated: {formatDistanceToNow(new Date(rfp.last_scraped_at), { addSuffix: true })}
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
          <Card>
            <CardHeader>
              <CardTitle>Documents</CardTitle>
              <CardDescription>
                Downloaded documents from the RFP posting
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
                            <span>{formatFileSize(doc.file_size)}</span>
                            {doc.downloaded_at && (
                              <span>
                                Downloaded {formatDistanceToNow(new Date(doc.downloaded_at), { addSuffix: true })}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDownload(doc)}
                      >
                        <Download className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
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
      </Tabs>
    </div>
  )
}
