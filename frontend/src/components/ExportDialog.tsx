import { useState } from 'react'
import {
  FileText,
  FileJson,
  FileCode,
  Download,
  Settings,
  Loader2,
} from 'lucide-react'
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
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Separator } from '@/components/ui/separator'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { toast } from 'sonner'
import {
  exportToWord,
  exportToMarkdown,
  exportToJSON,
} from '@/services/exportService'

interface ExportSection {
  id: string
  title: string
  content: string
}

interface ExportDialogProps {
  sections: ExportSection[]
  rfpTitle?: string
  companyName?: string
  trigger?: React.ReactNode
}

type ExportFormat = 'docx' | 'md' | 'json'

export function ExportDialog({
  sections,
  rfpTitle,
  companyName,
  trigger,
}: ExportDialogProps) {
  const [open, setOpen] = useState(false)
  const [isExporting, setIsExporting] = useState(false)
  const [format, setFormat] = useState<ExportFormat>('docx')
  const [filename, setFilename] = useState(
    rfpTitle?.toLowerCase().replace(/\s+/g, '-') || 'proposal'
  )
  const [options, setOptions] = useState({
    includeTableOfContents: true,
    includeHeader: true,
    includeFooter: true,
    includePageNumbers: true,
    customCompanyName: companyName || '',
  })
  const [showAdvanced, setShowAdvanced] = useState(false)

  const handleExport = async () => {
    if (sections.length === 0) {
      toast.error('No content to export')
      return
    }

    setIsExporting(true)

    try {
      const exportOptions = {
        filename,
        rfpTitle,
        companyName: options.customCompanyName,
        includeTableOfContents: options.includeTableOfContents,
        includeHeader: options.includeHeader,
        includeFooter: options.includeFooter,
        includePageNumbers: options.includePageNumbers,
      }

      switch (format) {
        case 'docx':
          await exportToWord(sections, exportOptions)
          break
        case 'md':
          exportToMarkdown(sections, exportOptions)
          break
        case 'json':
          exportToJSON(sections, exportOptions)
          break
      }

      toast.success(`Exported successfully as ${format.toUpperCase()}`)
      setOpen(false)
    } catch (error) {
      console.error('Export failed:', error)
      toast.error('Export failed. Please try again.')
    } finally {
      setIsExporting(false)
    }
  }

  const formatOptions = [
    {
      value: 'docx',
      label: 'Word Document',
      description: 'Microsoft Word format with formatting',
      icon: FileText,
    },
    {
      value: 'md',
      label: 'Markdown',
      description: 'Plain text with markdown formatting',
      icon: FileCode,
    },
    {
      value: 'json',
      label: 'JSON',
      description: 'Structured data format',
      icon: FileJson,
    },
  ]

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || (
          <Button variant="outline">
            <Download className="mr-2 h-4 w-4" />
            Export
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Export Proposal</DialogTitle>
          <DialogDescription>
            Export your proposal in various formats. Word format includes full
            formatting and is recommended for submission.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-6 py-4">
          {/* Format Selection */}
          <div className="grid gap-3">
            <Label>Export Format</Label>
            <RadioGroup
              value={format}
              onValueChange={(v) => setFormat(v as ExportFormat)}
              className="grid gap-2"
            >
              {formatOptions.map((opt) => (
                <div
                  key={opt.value}
                  className={`flex items-center space-x-3 rounded-lg border p-3 cursor-pointer transition-colors ${
                    format === opt.value
                      ? 'border-primary bg-primary/5'
                      : 'hover:bg-muted'
                  }`}
                  onClick={() => setFormat(opt.value as ExportFormat)}
                >
                  <RadioGroupItem value={opt.value} id={opt.value} />
                  <opt.icon className="h-5 w-5 text-muted-foreground" />
                  <div className="flex-1">
                    <Label htmlFor={opt.value} className="cursor-pointer">
                      {opt.label}
                    </Label>
                    <p className="text-xs text-muted-foreground">
                      {opt.description}
                    </p>
                  </div>
                </div>
              ))}
            </RadioGroup>
          </div>

          {/* Filename */}
          <div className="grid gap-2">
            <Label htmlFor="filename">Filename</Label>
            <div className="flex">
              <Input
                id="filename"
                value={filename}
                onChange={(e) => setFilename(e.target.value)}
                placeholder="proposal"
                className="rounded-r-none"
              />
              <div className="flex items-center rounded-r-md border border-l-0 bg-muted px-3 text-sm text-muted-foreground">
                .{format}
              </div>
            </div>
          </div>

          {/* Advanced Options */}
          {format === 'docx' && (
            <Collapsible open={showAdvanced} onOpenChange={setShowAdvanced}>
              <CollapsibleTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  className="w-full justify-between"
                >
                  <span className="flex items-center">
                    <Settings className="mr-2 h-4 w-4" />
                    Advanced Options
                  </span>
                </Button>
              </CollapsibleTrigger>
              <CollapsibleContent className="mt-3 space-y-4">
                <Separator />

                <div className="grid gap-2">
                  <Label htmlFor="companyName">Company Name</Label>
                  <Input
                    id="companyName"
                    value={options.customCompanyName}
                    onChange={(e) =>
                      setOptions((prev) => ({
                        ...prev,
                        customCompanyName: e.target.value,
                      }))
                    }
                    placeholder="Your Company Name"
                  />
                </div>

                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="toc">Include Table of Contents</Label>
                    <Switch
                      id="toc"
                      checked={options.includeTableOfContents}
                      onCheckedChange={(v) =>
                        setOptions((prev) => ({
                          ...prev,
                          includeTableOfContents: v,
                        }))
                      }
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <Label htmlFor="header">Include Header</Label>
                    <Switch
                      id="header"
                      checked={options.includeHeader}
                      onCheckedChange={(v) =>
                        setOptions((prev) => ({ ...prev, includeHeader: v }))
                      }
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <Label htmlFor="footer">Include Footer</Label>
                    <Switch
                      id="footer"
                      checked={options.includeFooter}
                      onCheckedChange={(v) =>
                        setOptions((prev) => ({ ...prev, includeFooter: v }))
                      }
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <Label htmlFor="pageNumbers">Include Page Numbers</Label>
                    <Switch
                      id="pageNumbers"
                      checked={options.includePageNumbers}
                      onCheckedChange={(v) =>
                        setOptions((prev) => ({
                          ...prev,
                          includePageNumbers: v,
                        }))
                      }
                    />
                  </div>
                </div>
              </CollapsibleContent>
            </Collapsible>
          )}

          {/* Section Summary */}
          <div className="rounded-lg bg-muted p-3">
            <p className="text-sm text-muted-foreground">
              <strong>{sections.length}</strong> sections will be exported
              {sections.length > 0 && (
                <span className="ml-1">
                  ({sections.map((s) => s.title).join(', ')})
                </span>
              )}
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button onClick={handleExport} disabled={isExporting}>
            {isExporting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Exporting...
              </>
            ) : (
              <>
                <Download className="mr-2 h-4 w-4" />
                Export
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
