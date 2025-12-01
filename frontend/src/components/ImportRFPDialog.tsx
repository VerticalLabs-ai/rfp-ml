import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link2, Loader2, Building2, CheckCircle2, FileText, MessageSquare } from 'lucide-react'
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
import { api } from '@/lib/api'

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
  const [url, setUrl] = useState('')
  const [selectedProfileId, setSelectedProfileId] = useState<string>('')
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  // Fetch company profiles
  const { data: profiles } = useQuery({
    queryKey: ['company-profiles'],
    queryFn: () => api.get<CompanyProfile[]>('/profiles'),
    enabled: isOpen,
  })

  // Set default profile when profiles load
  useState(() => {
    if (profiles) {
      const defaultProfile = profiles.find(p => p.is_default)
      if (defaultProfile && !selectedProfileId) {
        setSelectedProfileId(defaultProfile.id.toString())
      }
    }
  })

  // Scrape mutation
  const scrapeMutation = useMutation({
    mutationFn: async (data: { url: string; company_profile_id?: number }) =>
      api.post<ScrapeResponse>('/scraper/scrape', data),
    onSuccess: (data) => {
      toast.success(`RFP imported: ${data.title}`, {
        description: `${data.documents_count} documents, ${data.qa_count} Q&A items`,
      })
      queryClient.invalidateQueries({ queryKey: ['rfps'] })
      setIsOpen(false)
      setUrl('')
      onSuccess?.(data.rfp_id)
      // Navigate to the RFP detail page
      navigate(`/rfps/${data.rfp_id}`)
    },
    onError: (error: Error) => {
      toast.error('Failed to import RFP', {
        description: error.message,
      })
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (!url.trim()) {
      toast.error('Please enter a URL')
      return
    }

    scrapeMutation.mutate({
      url: url.trim(),
      company_profile_id: selectedProfileId && selectedProfileId !== 'none' ? parseInt(selectedProfileId) : undefined,
    })
  }

  const isValidUrl = (urlString: string) => {
    try {
      const parsed = new URL(urlString)
      return parsed.hostname.includes('beaconbid.com')
    } catch {
      return false
    }
  }

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
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Link2 className="h-5 w-5" />
            Import RFP from URL
          </DialogTitle>
          <DialogDescription>
            Paste a BeaconBid URL to automatically import the RFP, download documents, and extract Q&A.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="url">BeaconBid URL</Label>
            <Input
              id="url"
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://www.beaconbid.com/solicitations/..."
              disabled={scrapeMutation.isPending}
            />
            {url && !isValidUrl(url) && (
              <p className="text-sm text-amber-600">
                URL should be from beaconbid.com
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="profile">Company Profile (for proposals)</Label>
            <Select
              value={selectedProfileId}
              onValueChange={setSelectedProfileId}
              disabled={scrapeMutation.isPending}
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
                        <span className="text-xs text-muted-foreground">(default)</span>
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

          {/* Scraping Status */}
          {scrapeMutation.isPending && (
            <div className="rounded-lg bg-blue-50 dark:bg-blue-900/20 p-4 space-y-3">
              <div className="flex items-center gap-2 text-blue-700 dark:text-blue-300">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span className="font-medium">Scraping RFP...</span>
              </div>
              <div className="text-sm text-blue-600 dark:text-blue-400 space-y-1">
                <p>This may take a moment. We're:</p>
                <ul className="list-disc list-inside space-y-1 ml-2">
                  <li>Opening the page in a cloud browser</li>
                  <li>Extracting RFP metadata</li>
                  <li>Finding document attachments</li>
                  <li>Capturing Q&A entries</li>
                </ul>
              </div>
            </div>
          )}

          {/* Success Preview */}
          {scrapeMutation.isSuccess && (
            <div className="rounded-lg bg-green-50 dark:bg-green-900/20 p-4 space-y-2">
              <div className="flex items-center gap-2 text-green-700 dark:text-green-300">
                <CheckCircle2 className="h-4 w-4" />
                <span className="font-medium">RFP Imported Successfully!</span>
              </div>
              <div className="flex items-center gap-4 text-sm text-green-600 dark:text-green-400">
                <span className="flex items-center gap-1">
                  <FileText className="h-4 w-4" />
                  {scrapeMutation.data.documents_count} documents
                </span>
                <span className="flex items-center gap-1">
                  <MessageSquare className="h-4 w-4" />
                  {scrapeMutation.data.qa_count} Q&A items
                </span>
              </div>
            </div>
          )}

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setIsOpen(false)}
              disabled={scrapeMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={!url || scrapeMutation.isPending}
            >
              {scrapeMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Importing...
                </>
              ) : (
                'Import RFP'
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
