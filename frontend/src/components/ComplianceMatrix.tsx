'use client'

import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Checkbox } from '@/components/ui/checkbox'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Check,
  X,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Search,
  Download,
  Plus,
  Sparkles,
  RefreshCw,
  Trash2,
} from 'lucide-react'
import { toast } from 'sonner'
import { api, ComplianceRequirementList } from '@/services/api'

interface ComplianceMatrixProps {
  rfpId: number
}

const statusOptions = [
  { value: 'not_started', label: 'Not Started', color: 'secondary' },
  { value: 'in_progress', label: 'In Progress', color: 'warning' },
  { value: 'complete', label: 'Complete', color: 'success' },
  { value: 'not_applicable', label: 'N/A', color: 'outline' },
] as const

const typeOptions = [
  { value: 'mandatory', label: 'Mandatory', color: 'destructive' },
  { value: 'evaluation', label: 'Evaluation', color: 'default' },
  { value: 'performance', label: 'Performance', color: 'secondary' },
  { value: 'technical', label: 'Technical', color: 'outline' },
  { value: 'administrative', label: 'Administrative', color: 'outline' },
] as const

const ComplianceIndicator = ({ indicator }: { indicator: string | null }) => {
  if (!indicator) return <span className="text-muted-foreground">-</span>

  const icons = {
    compliant: <Check className="h-4 w-4 text-green-500" />,
    partial: <AlertTriangle className="h-4 w-4 text-yellow-500" />,
    non_compliant: <X className="h-4 w-4 text-red-500" />,
  }

  return icons[indicator as keyof typeof icons] || <span>-</span>
}

const TypeBadge = ({ type }: { type: string }) => {
  const option = typeOptions.find(t => t.value === type)
  return (
    <Badge variant={option?.color as 'destructive' | 'default' | 'secondary' | 'outline' || 'secondary'}>
      {option?.label || type}
    </Badge>
  )
}

export function ComplianceMatrix({ rfpId }: ComplianceMatrixProps) {
  const queryClient = useQueryClient()
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<string | null>(null)
  const [typeFilter, setTypeFilter] = useState<string | null>(null)
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set())
  const [editingResponse, setEditingResponse] = useState<number | null>(null)
  const [responseText, setResponseText] = useState('')
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false)
  const [newRequirement, setNewRequirement] = useState({
    requirement_id: '',
    requirement_text: '',
    requirement_type: 'mandatory' as const,
    source_document: '',
    source_section: '',
  })

  // Fetch requirements
  const { data, isLoading } = useQuery<ComplianceRequirementList>({
    queryKey: ['compliance-requirements', rfpId, statusFilter, typeFilter, searchQuery],
    queryFn: async () => {
      const params: Record<string, string> = {}
      if (statusFilter) params.status = statusFilter
      if (typeFilter) params.type = typeFilter
      if (searchQuery) params.search = searchQuery
      return api.compliance.listRequirements(rfpId, params)
    },
  })

  // Mutations
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Record<string, unknown> }) =>
      api.compliance.updateRequirement(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['compliance-requirements', rfpId] })
      toast.success('Requirement updated')
    },
    onError: () => toast.error('Failed to update requirement'),
  })

  const createMutation = useMutation({
    mutationFn: (data: typeof newRequirement) => api.compliance.createRequirement(rfpId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['compliance-requirements', rfpId] })
      toast.success('Requirement added')
      setIsAddDialogOpen(false)
      setNewRequirement({
        requirement_id: '',
        requirement_text: '',
        requirement_type: 'mandatory',
        source_document: '',
        source_section: '',
      })
    },
    onError: () => toast.error('Failed to add requirement'),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.compliance.deleteRequirement(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['compliance-requirements', rfpId] })
      toast.success('Requirement deleted')
    },
    onError: () => toast.error('Failed to delete requirement'),
  })

  const bulkUpdateMutation = useMutation({
    mutationFn: ({ ids, status }: { ids: number[]; status: string }) =>
      api.compliance.bulkUpdateStatus(rfpId, ids, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['compliance-requirements', rfpId] })
      setSelectedIds(new Set())
      toast.success('Requirements updated')
    },
    onError: () => toast.error('Failed to update requirements'),
  })

  const extractMutation = useMutation({
    mutationFn: () => api.compliance.extractRequirements(rfpId),
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: ['compliance-requirements', rfpId] })
      toast.success(`Extracted ${response.extracted_count} requirements`)
    },
    onError: () => toast.error('Failed to extract requirements'),
  })

  const aiResponseMutation = useMutation({
    mutationFn: (requirementId: number) => api.compliance.generateAIResponse(requirementId),
    onSuccess: (response) => {
      setResponseText(response.response_text)
      toast.success('AI response generated')
    },
    onError: () => toast.error('Failed to generate AI response'),
  })

  // Toggle selection
  const toggleSelect = (id: number) => {
    const newSelected = new Set(selectedIds)
    if (newSelected.has(id)) {
      newSelected.delete(id)
    } else {
      newSelected.add(id)
    }
    setSelectedIds(newSelected)
  }

  // Toggle expand
  const toggleExpand = (id: number) => {
    const newExpanded = new Set(expandedIds)
    if (newExpanded.has(id)) {
      newExpanded.delete(id)
    } else {
      newExpanded.add(id)
    }
    setExpandedIds(newExpanded)
  }

  // Handle status change
  const handleStatusChange = (id: number, status: string) => {
    updateMutation.mutate({ id, data: { status } })
  }

  // Handle response save
  const handleResponseSave = (id: number) => {
    updateMutation.mutate({
      id,
      data: {
        response_text: responseText,
        compliance_indicator: responseText ? 'compliant' : null,
      },
    })
    setEditingResponse(null)
  }

  // Export to CSV
  const exportToCSV = () => {
    if (!data?.requirements) return

    const headers = ['Req ID', 'Requirement', 'Type', 'Status', 'Response', 'Source']
    const rows = data.requirements.map(r => [
      r.requirement_id,
      r.requirement_text.replace(/"/g, '""'),
      r.requirement_type,
      r.status,
      (r.response_text || '').replace(/"/g, '""'),
      r.source_document || '',
    ])

    const csv = [headers, ...rows].map(row => row.map(cell => `"${cell}"`).join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `compliance-matrix-${rfpId}.csv`
    a.click()
    URL.revokeObjectURL(url)
    toast.success('Exported to CSV')
  }

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {[1, 2, 3].map(i => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  const requirements = data?.requirements || []
  const summary = data ? {
    total: data.total,
    completed: data.completed,
    inProgress: data.in_progress,
    notStarted: data.not_started,
    complianceRate: data.compliance_rate,
  } : { total: 0, completed: 0, inProgress: 0, notStarted: 0, complianceRate: 0 }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Compliance Matrix</CardTitle>
            <CardDescription>
              {summary.total} requirements | {summary.completed} complete | {summary.complianceRate.toFixed(0)}% compliance
            </CardDescription>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => extractMutation.mutate()}
              disabled={extractMutation.isPending}
            >
              <RefreshCw className={`mr-2 h-4 w-4 ${extractMutation.isPending ? 'animate-spin' : ''}`} />
              Extract
            </Button>
            <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
              <DialogTrigger asChild>
                <Button variant="outline" size="sm">
                  <Plus className="mr-2 h-4 w-4" />
                  Add
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Add Requirement</DialogTitle>
                  <DialogDescription>Manually add a compliance requirement</DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                  <Input
                    placeholder="Requirement ID (e.g., L.1.2)"
                    value={newRequirement.requirement_id}
                    onChange={e => setNewRequirement({ ...newRequirement, requirement_id: e.target.value })}
                  />
                  <Textarea
                    placeholder="Requirement text"
                    value={newRequirement.requirement_text}
                    onChange={e => setNewRequirement({ ...newRequirement, requirement_text: e.target.value })}
                  />
                  <Select
                    value={newRequirement.requirement_type}
                    onValueChange={(v) => setNewRequirement({ ...newRequirement, requirement_type: v as typeof newRequirement.requirement_type })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {typeOptions.map(t => (
                        <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Input
                    placeholder="Source document"
                    value={newRequirement.source_document}
                    onChange={e => setNewRequirement({ ...newRequirement, source_document: e.target.value })}
                  />
                  <Button
                    className="w-full"
                    onClick={() => createMutation.mutate(newRequirement)}
                    disabled={createMutation.isPending || !newRequirement.requirement_id || !newRequirement.requirement_text}
                  >
                    Add Requirement
                  </Button>
                </div>
              </DialogContent>
            </Dialog>
            <Button variant="outline" size="sm" onClick={exportToCSV}>
              <Download className="mr-2 h-4 w-4" />
              Export
            </Button>
          </div>
        </div>

        {/* Progress bar */}
        <Progress value={summary.complianceRate} className="mt-4" />

        {/* Filters */}
        <div className="mt-4 flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search requirements..."
              className="pl-8"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
            />
          </div>
          <Select value={statusFilter || 'all'} onValueChange={v => setStatusFilter(v === 'all' ? null : v)}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              {statusOptions.map(s => (
                <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={typeFilter || 'all'} onValueChange={v => setTypeFilter(v === 'all' ? null : v)}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              {typeOptions.map(t => (
                <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Bulk actions */}
        {selectedIds.size > 0 && (
          <div className="mt-4 flex items-center gap-2 rounded-md bg-muted p-2">
            <span className="text-sm">{selectedIds.size} selected</span>
            <Select onValueChange={status => bulkUpdateMutation.mutate({ ids: Array.from(selectedIds), status })}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Set status..." />
              </SelectTrigger>
              <SelectContent>
                {statusOptions.map(s => (
                  <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button variant="ghost" size="sm" onClick={() => setSelectedIds(new Set())}>
              Clear
            </Button>
          </div>
        )}
      </CardHeader>

      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-10">
                <Checkbox
                  checked={selectedIds.size === requirements.length && requirements.length > 0}
                  onCheckedChange={checked => {
                    if (checked) {
                      setSelectedIds(new Set(requirements.map(r => r.id)))
                    } else {
                      setSelectedIds(new Set())
                    }
                  }}
                />
              </TableHead>
              <TableHead className="w-10"></TableHead>
              <TableHead className="w-24">Req ID</TableHead>
              <TableHead>Requirement</TableHead>
              <TableHead className="w-32">Source</TableHead>
              <TableHead className="w-28">Type</TableHead>
              <TableHead className="w-36">Status</TableHead>
              <TableHead className="w-16 text-center">Comply</TableHead>
              <TableHead className="w-24">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {requirements.length === 0 ? (
              <TableRow>
                <TableCell colSpan={9} className="text-center text-muted-foreground py-8">
                  No requirements found. Click &quot;Extract&quot; to extract from documents or &quot;Add&quot; to add manually.
                </TableCell>
              </TableRow>
            ) : (
              requirements.map(req => (
                <React.Fragment key={req.id}>
                  <TableRow className="group">
                    <TableCell>
                      <Checkbox
                        checked={selectedIds.has(req.id)}
                        onCheckedChange={() => toggleSelect(req.id)}
                      />
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-6 w-6 p-0"
                        onClick={() => toggleExpand(req.id)}
                      >
                        {expandedIds.has(req.id) ? (
                          <ChevronDown className="h-4 w-4" />
                        ) : (
                          <ChevronRight className="h-4 w-4" />
                        )}
                      </Button>
                    </TableCell>
                    <TableCell className="font-mono text-sm">{req.requirement_id}</TableCell>
                    <TableCell className="max-w-md">
                      <p className="line-clamp-2">{req.requirement_text}</p>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {req.source_document && (
                        <div>
                          <div className="truncate">{req.source_document}</div>
                          {req.source_section && <div>{req.source_section}</div>}
                        </div>
                      )}
                    </TableCell>
                    <TableCell>
                      <TypeBadge type={req.requirement_type} />
                    </TableCell>
                    <TableCell>
                      <Select
                        value={req.status}
                        onValueChange={v => handleStatusChange(req.id, v)}
                      >
                        <SelectTrigger className="h-8">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {statusOptions.map(s => (
                            <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </TableCell>
                    <TableCell className="text-center">
                      <ComplianceIndicator indicator={req.compliance_indicator} />
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 w-7 p-0"
                          onClick={() => {
                            setEditingResponse(req.id)
                            setResponseText(req.response_text || '')
                            if (!expandedIds.has(req.id)) toggleExpand(req.id)
                          }}
                        >
                          <Sparkles className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 w-7 p-0 text-destructive"
                          onClick={() => {
                            if (confirm('Delete this requirement?')) {
                              deleteMutation.mutate(req.id)
                            }
                          }}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>

                  {/* Expanded row for response */}
                  {expandedIds.has(req.id) && (
                    <TableRow>
                      <TableCell colSpan={9} className="bg-muted/50">
                        <div className="p-4 space-y-3">
                          <div className="flex items-center justify-between">
                            <span className="font-medium">Response</span>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => {
                                setEditingResponse(req.id)
                                aiResponseMutation.mutate(req.id)
                              }}
                              disabled={aiResponseMutation.isPending}
                            >
                              <Sparkles className={`mr-2 h-4 w-4 ${aiResponseMutation.isPending ? 'animate-pulse' : ''}`} />
                              Generate with AI
                            </Button>
                          </div>

                          {editingResponse === req.id ? (
                            <div className="space-y-2">
                              <Textarea
                                value={responseText}
                                onChange={e => setResponseText(e.target.value)}
                                placeholder="Enter compliance response..."
                                rows={4}
                              />
                              <div className="flex gap-2">
                                <Button size="sm" onClick={() => handleResponseSave(req.id)}>
                                  Save
                                </Button>
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => {
                                    setEditingResponse(null)
                                    setResponseText('')
                                  }}
                                >
                                  Cancel
                                </Button>
                              </div>
                            </div>
                          ) : (
                            <div
                              className="text-sm cursor-pointer hover:bg-muted p-2 rounded"
                              onClick={() => {
                                setEditingResponse(req.id)
                                setResponseText(req.response_text || '')
                              }}
                            >
                              {req.response_text || (
                                <span className="text-muted-foreground italic">
                                  Click to add response or use AI to generate
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                </React.Fragment>
              ))
            )}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
