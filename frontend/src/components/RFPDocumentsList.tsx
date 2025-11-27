import { useQuery } from '@tanstack/react-query'
import { FileText, Download, FileArchive, FileSpreadsheet, File, Loader2 } from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { api } from '@/lib/api'

interface RFPDocument {
  id: number
  filename: string
  file_type: string | null
  file_size: number | null
  document_type: string | null
  downloaded_at: string | null
}

interface RFPDocumentsListProps {
  rfpId: string
}

const getFileIcon = (fileType: string | null) => {
  switch (fileType?.toLowerCase()) {
    case 'pdf':
      return <FileText className="h-5 w-5 text-red-500" />
    case 'docx':
    case 'doc':
      return <FileText className="h-5 w-5 text-blue-500" />
    case 'xlsx':
    case 'xls':
      return <FileSpreadsheet className="h-5 w-5 text-green-500" />
    case 'zip':
    case 'rar':
      return <FileArchive className="h-5 w-5 text-amber-500" />
    default:
      return <File className="h-5 w-5 text-slate-400" />
  }
}

const formatFileSize = (bytes: number | null): string => {
  if (!bytes) return 'Unknown size'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const getDocumentTypeBadge = (docType: string | null) => {
  const typeColors: Record<string, string> = {
    solicitation: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
    amendment: 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200',
    attachment: 'bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-200',
    qa_response: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  }

  const color = typeColors[docType || ''] || typeColors.attachment
  return <Badge className={color}>{docType || 'attachment'}</Badge>
}

export function RFPDocumentsList({ rfpId }: RFPDocumentsListProps) {
  const { data: documents, isLoading, error } = useQuery({
    queryKey: ['rfp-documents', rfpId],
    queryFn: () => api.get<RFPDocument[]>(`/scraper/${rfpId}/documents`),
  })

  const handleDownload = async (docId: number, filename: string) => {
    try {
      await api.download(`/scraper/${rfpId}/documents/${docId}/download`, filename)
      toast.success(`Downloaded ${filename}`)
    } catch {
      toast.error(`Failed to download ${filename}`)
    }
  }

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Documents
          </CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Documents
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-red-500">Failed to load documents</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileText className="h-5 w-5" />
          Documents
        </CardTitle>
        <CardDescription>
          {documents?.length || 0} documents attached to this RFP
        </CardDescription>
      </CardHeader>
      <CardContent>
        {!documents || documents.length === 0 ? (
          <p className="text-slate-500 dark:text-slate-400 text-center py-4">
            No documents available
          </p>
        ) : (
          <div className="space-y-2">
            {documents.map((doc) => (
              <div
                key={doc.id}
                className="flex items-center justify-between p-3 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800/50"
              >
                <div className="flex items-center gap-3">
                  {getFileIcon(doc.file_type)}
                  <div>
                    <p className="font-medium text-sm">{doc.filename}</p>
                    <div className="flex items-center gap-2 text-xs text-slate-500">
                      {getDocumentTypeBadge(doc.document_type)}
                      <span>{formatFileSize(doc.file_size)}</span>
                    </div>
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleDownload(doc.id, doc.filename)}
                >
                  <Download className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
