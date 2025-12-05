import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Link2,
  Loader2,
  Building2,
  CheckCircle2,
  FileText,
  MessageSquare,
  AlertTriangle,
  ArrowLeft,
  Globe,
  Edit3,
} from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Separator } from '@/components/ui/separator'
import { api } from '@/lib/api'
import type {
  PreviewResponse,
  EditableFields,
  ImportStep,
  ConfirmImportRequest,
} from '@/types/import'

interface CompanyProfile {
  id: number
  name: string
  is_default: boolean
}

interface ScrapeResponse {
  rfp_id: string
  status: string
  title: string
  documents_count: number
  qa_count: number
  message: string
}

interface ImportRFPDialogProps {
  trigger?: React.ReactNode
  onSuccess?: (rfpId: string) => void
}

export function ImportRFPDialog({ trigger, onSuccess }: ImportRFPDialogProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [step, setStep] = useState<ImportStep>('url')
  const [url, setUrl] = useState('')
  const [selectedProfileId, setSelectedProfileId] = useState<string>('')
  const [previewData, setPreviewData] = useState<PreviewResponse | null>(null)
  const [editedFields, setEditedFields] = useState<EditableFields | null>(null)
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  // Fetch company profiles
  const { data: profiles } = useQuery({
    queryKey: ['company-profiles'],
    queryFn: () => api.get<CompanyProfile[]>('/profiles'),
    enabled: isOpen,
  })

  // Set default profile when profiles load
  useEffect(() => {
    if (profiles && !selectedProfileId) {
      const defaultProfile = profiles.find((p) => p.is_default)
      if (defaultProfile) {
        setSelectedProfileId(defaultProfile.id.toString())
      }
    }
  }, [profiles, selectedProfileId])

  // Reset state when dialog closes
  useEffect(() => {
    if (!isOpen) {
      setStep('url')
      setUrl('')
      setPreviewData(null)
      setEditedFields(null)
    }
  }, [isOpen])

  // Preview mutation - extracts data without saving
  const previewMutation = useMutation({
    mutationFn: (url: string) =>
      api.post<PreviewResponse>('/scraper/preview', { url }),
    onSuccess: (data) => {
      setPreviewData(data)
      setEditedFields({
        title: data.detected_fields.title || '',
        solicitation_number: data.detected_fields.solicitation_number || '',
        agency: data.detected_fields.agency || '',
        office: data.detected_fields.office || '',
        description: data.detected_fields.description || '',
        naics_code: data.detected_fields.naics_code || '',
        category: data.detected_fields.category || '',
      })
      setStep('preview')
    },
    onError: (error: Error) => {
      toast.error('Failed to preview RFP', {
        description: error.message,
      })
    },
  })

  // Confirm mutation - saves with edits
  const confirmMutation = useMutation({
    mutationFn: (data: ConfirmImportRequest) =>
      api.post<ScrapeResponse>('/scraper/confirm', data),
    onSuccess: (data) => {
      toast.success(`RFP imported: ${data.title}`, {
        description: `${data.documents_count} documents, ${data.qa_count} Q&A items`,
      })
      queryClient.invalidateQueries({ queryKey: ['rfps'] })
      setIsOpen(false)
      onSuccess?.(data.rfp_id)
      navigate(`/rfps/${data.rfp_id}`)
    },
    onError: (error: Error) => {
      toast.error('Failed to import RFP', {
        description: error.message,
      })
    },
  })

  // Legacy scrape mutation - for direct import without preview
  const scrapeMutation = useMutation({
    mutationFn: async (data: { url: string; company_profile_id?: number }) =>
      api.post<ScrapeResponse>('/scraper/scrape', data),
    onSuccess: (data) => {
      toast.success(`RFP imported: ${data.title}`, {
        description: `${data.documents_count} documents, ${data.qa_count} Q&A items`,
      })
      queryClient.invalidateQueries({ queryKey: ['rfps'] })
      setIsOpen(false)
      onSuccess?.(data.rfp_id)
      navigate(`/rfps/${data.rfp_id}`)
    },
    onError: (error: Error) => {
      toast.error('Failed to import RFP', {
        description: error.message,
      })
    },
  })

  const handlePreview = (e: React.FormEvent) => {
    e.preventDefault()
    if (!url.trim()) {
      toast.error('Please enter a URL')
      return
    }
    previewMutation.mutate(url.trim())
  }

  const handleConfirm = () => {
    if (!previewData) return

    const overrides: Partial<EditableFields> = {}

    // Only include fields that were actually changed
    if (editedFields) {
      if (editedFields.title !== (previewData.detected_fields.title || '')) {
        overrides.title = editedFields.title
      }
      if (
        editedFields.solicitation_number !==
        (previewData.detected_fields.solicitation_number || '')
      ) {
        overrides.solicitation_number = editedFields.solicitation_number
      }
      if (editedFields.agency !== (previewData.detected_fields.agency || '')) {
        overrides.agency = editedFields.agency
      }
      if (editedFields.office !== (previewData.detected_fields.office || '')) {
        overrides.office = editedFields.office
      }
      if (
        editedFields.description !==
        (previewData.detected_fields.description || '')
      ) {
        overrides.description = editedFields.description
      }
      if (
        editedFields.naics_code !==
        (previewData.detected_fields.naics_code || '')
      ) {
        overrides.naics_code = editedFields.naics_code
      }
      if (
        editedFields.category !== (previewData.detected_fields.category || '')
      ) {
        overrides.category = editedFields.category
      }
    }

    confirmMutation.mutate({
      source_url: url,
      company_profile_id:
        selectedProfileId && selectedProfileId !== 'none'
          ? parseInt(selectedProfileId)
          : undefined,
      overrides: Object.keys(overrides).length > 0 ? overrides : undefined,
    })
  }

  const handleDirectImport = (e: React.FormEvent) => {
    e.preventDefault()
    if (!url.trim()) {
      toast.error('Please enter a URL')
      return
    }
    scrapeMutation.mutate({
      url: url.trim(),
      company_profile_id:
        selectedProfileId && selectedProfileId !== 'none'
          ? parseInt(selectedProfileId)
          : undefined,
    })
  }

  // Accept any valid HTTP(S) URL
  const isValidUrl = (urlString: string) => {
    try {
      const parsed = new URL(urlString)
      return ['http:', 'https:'].includes(parsed.protocol)
    } catch {
      return false
    }
  }

  const isLoading =
    previewMutation.isPending ||
    confirmMutation.isPending ||
    scrapeMutation.isPending

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        {trigger || (
          <Button className="gap-2">
            <Link2 className="h-4 w-4" />
            Import RFP
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* Step 1: URL Input */}
        {step === 'url' && (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Link2 className="h-5 w-5" />
                Import RFP from URL
              </DialogTitle>
              <DialogDescription>
                Paste any government contracting URL to automatically import the
                RFP, download documents, and extract Q&A.
              </DialogDescription>
            </DialogHeader>

            <form onSubmit={handlePreview} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="url">RFP URL</Label>
                <Input
                  id="url"
                  type="url"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://sam.gov/opp/... or any government contracting site"
                  disabled={isLoading}
                />
                {url && !isValidUrl(url) && (
                  <p className="text-sm text-amber-600">
                    Please enter a valid HTTP or HTTPS URL
                  </p>
                )}
                <p className="text-xs text-muted-foreground">
                  Supports: SAM.gov, BeaconBid, state portals, and most
                  government contracting websites
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="profile">Company Profile (for proposals)</Label>
                <Select
                  value={selectedProfileId}
                  onValueChange={setSelectedProfileId}
                  disabled={isLoading}
                >
                  <SelectTrigger id="profile">
                    <SelectValue placeholder="Select a profile" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">None</SelectItem>
                    {profiles?.map((profile) => (
                      <SelectItem key={profile.id} value={profile.id.toString()}>
                        <span className="flex items-center gap-2">
                          <Building2 className="h-4 w-4" />
                          {profile.name}
                          {profile.is_default && (
                            <span className="text-xs text-muted-foreground">
                              (default)
                            </span>
                          )}
                        </span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {profiles?.length === 0 && (
                  <p className="text-sm text-muted-foreground">
                    No profiles yet.{' '}
                    <a href="/profiles" className="text-blue-500 hover:underline">
                      Create one
                    </a>
                  </p>
                )}
              </div>

              {/* Loading Status */}
              {previewMutation.isPending && (
                <div className="rounded-lg bg-blue-50 dark:bg-blue-900/20 p-4 space-y-3">
                  <div className="flex items-center gap-2 text-blue-700 dark:text-blue-300">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span className="font-medium">Extracting RFP data...</span>
                  </div>
                  <div className="text-sm text-blue-600 dark:text-blue-400 space-y-1">
                    <p>This may take a moment. We're:</p>
                    <ul className="list-disc list-inside space-y-1 ml-2">
                      <li>Opening the page in a cloud browser</li>
                      <li>Using AI to extract RFP details</li>
                      <li>Finding document attachments</li>
                      <li>Capturing Q&A entries</li>
                    </ul>
                  </div>
                </div>
              )}

              <DialogFooter className="gap-2 sm:gap-0">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setIsOpen(false)}
                  disabled={isLoading}
                >
                  Cancel
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  onClick={handleDirectImport}
                  disabled={!url || !isValidUrl(url) || isLoading}
                >
                  Import Directly
                </Button>
                <Button
                  type="submit"
                  disabled={!url || !isValidUrl(url) || isLoading}
                >
                  {previewMutation.isPending ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Extracting...
                    </>
                  ) : (
                    <>
                      <Edit3 className="h-4 w-4 mr-2" />
                      Preview & Edit
                    </>
                  )}
                </Button>
              </DialogFooter>
            </form>
          </>
        )}

        {/* Step 2: Preview & Edit */}
        {step === 'preview' && previewData && (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Edit3 className="h-5 w-5" />
                Review & Edit Extracted Data
              </DialogTitle>
              <DialogDescription>
                Review the extracted information and make any corrections before
                importing.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4">
              {/* Duplicate Warning */}
              {previewData.duplicate_check && (
                <Alert variant="destructive">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertTitle>Duplicate Detected</AlertTitle>
                  <AlertDescription>
                    This URL was already imported as{' '}
                    <strong>{previewData.duplicate_check.rfp_id}</strong>
                    {previewData.duplicate_check.imported_at && (
                      <>
                        {' '}
                        on{' '}
                        {new Date(
                          previewData.duplicate_check.imported_at
                        ).toLocaleDateString()}
                      </>
                    )}
                    . Use the refresh feature to update existing RFPs.
                  </AlertDescription>
                </Alert>
              )}

              {/* Platform Badge */}
              <div className="flex items-center gap-2">
                <Globe className="h-4 w-4 text-muted-foreground" />
                <Badge variant="secondary">
                  {previewData.source_platform}
                </Badge>
                <span className="text-xs text-muted-foreground truncate flex-1">
                  {previewData.source_url}
                </span>
              </div>

              <Separator />

              {/* Editable Fields */}
              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2 space-y-2">
                  <Label htmlFor="edit-title">Title</Label>
                  <Input
                    id="edit-title"
                    value={editedFields?.title || ''}
                    onChange={(e) =>
                      setEditedFields((prev) =>
                        prev ? { ...prev, title: e.target.value } : null
                      )
                    }
                    disabled={isLoading}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="edit-solicitation">Solicitation Number</Label>
                  <Input
                    id="edit-solicitation"
                    value={editedFields?.solicitation_number || ''}
                    onChange={(e) =>
                      setEditedFields((prev) =>
                        prev
                          ? { ...prev, solicitation_number: e.target.value }
                          : null
                      )
                    }
                    disabled={isLoading}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="edit-naics">NAICS Code</Label>
                  <Input
                    id="edit-naics"
                    value={editedFields?.naics_code || ''}
                    onChange={(e) =>
                      setEditedFields((prev) =>
                        prev ? { ...prev, naics_code: e.target.value } : null
                      )
                    }
                    disabled={isLoading}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="edit-agency">Agency</Label>
                  <Input
                    id="edit-agency"
                    value={editedFields?.agency || ''}
                    onChange={(e) =>
                      setEditedFields((prev) =>
                        prev ? { ...prev, agency: e.target.value } : null
                      )
                    }
                    disabled={isLoading}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="edit-office">Office</Label>
                  <Input
                    id="edit-office"
                    value={editedFields?.office || ''}
                    onChange={(e) =>
                      setEditedFields((prev) =>
                        prev ? { ...prev, office: e.target.value } : null
                      )
                    }
                    disabled={isLoading}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="edit-category">Category</Label>
                  <Input
                    id="edit-category"
                    value={editedFields?.category || ''}
                    onChange={(e) =>
                      setEditedFields((prev) =>
                        prev ? { ...prev, category: e.target.value } : null
                      )
                    }
                    disabled={isLoading}
                  />
                </div>

                <div className="space-y-2">
                  <Label>Response Deadline</Label>
                  <Input
                    value={
                      previewData.detected_fields.response_deadline
                        ? new Date(
                            previewData.detected_fields.response_deadline
                          ).toLocaleString()
                        : 'Not detected'
                    }
                    disabled
                    className="bg-muted"
                  />
                </div>

                <div className="col-span-2 space-y-2">
                  <Label htmlFor="edit-description">Description</Label>
                  <Textarea
                    id="edit-description"
                    value={editedFields?.description || ''}
                    onChange={(e) =>
                      setEditedFields((prev) =>
                        prev ? { ...prev, description: e.target.value } : null
                      )
                    }
                    rows={3}
                    disabled={isLoading}
                  />
                </div>
              </div>

              <Separator />

              {/* Documents Preview */}
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4 text-muted-foreground" />
                  <span className="font-medium">
                    Documents ({previewData.documents.length})
                  </span>
                </div>
                {previewData.documents.length > 0 ? (
                  <div className="rounded-lg border p-2 max-h-32 overflow-y-auto">
                    <ul className="space-y-1 text-sm">
                      {previewData.documents.map((doc, i) => (
                        <li key={i} className="flex items-center gap-2">
                          <Badge variant="outline" className="text-xs">
                            {doc.file_type || 'file'}
                          </Badge>
                          <span className="truncate">{doc.filename}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    No documents detected
                  </p>
                )}
              </div>

              {/* Q&A Preview */}
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <MessageSquare className="h-4 w-4 text-muted-foreground" />
                  <span className="font-medium">
                    Q&A ({previewData.qa_items.length})
                  </span>
                </div>
                {previewData.qa_items.length > 0 ? (
                  <div className="rounded-lg border p-2 max-h-32 overflow-y-auto">
                    <ul className="space-y-2 text-sm">
                      {previewData.qa_items.slice(0, 3).map((qa, i) => (
                        <li key={i} className="border-b last:border-0 pb-2 last:pb-0">
                          <p className="font-medium truncate">
                            {qa.number && `${qa.number}: `}
                            {qa.question}
                          </p>
                          {qa.answer && (
                            <p className="text-muted-foreground truncate">
                              A: {qa.answer}
                            </p>
                          )}
                        </li>
                      ))}
                      {previewData.qa_items.length > 3 && (
                        <li className="text-muted-foreground">
                          +{previewData.qa_items.length - 3} more...
                        </li>
                      )}
                    </ul>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    No Q&A detected
                  </p>
                )}
              </div>

              {/* Import Progress */}
              {confirmMutation.isPending && (
                <div className="rounded-lg bg-blue-50 dark:bg-blue-900/20 p-4">
                  <div className="flex items-center gap-2 text-blue-700 dark:text-blue-300">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span className="font-medium">Importing RFP...</span>
                  </div>
                </div>
              )}

              {/* Success State */}
              {confirmMutation.isSuccess && (
                <div className="rounded-lg bg-green-50 dark:bg-green-900/20 p-4">
                  <div className="flex items-center gap-2 text-green-700 dark:text-green-300">
                    <CheckCircle2 className="h-4 w-4" />
                    <span className="font-medium">RFP Imported Successfully!</span>
                  </div>
                </div>
              )}
            </div>

            <DialogFooter className="gap-2 sm:gap-0">
              <Button
                type="button"
                variant="outline"
                onClick={() => setStep('url')}
                disabled={isLoading}
              >
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back
              </Button>
              <Button
                type="button"
                onClick={handleConfirm}
                disabled={!!previewData.duplicate_check || isLoading}
              >
                {confirmMutation.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Importing...
                  </>
                ) : (
                  'Import RFP'
                )}
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}
