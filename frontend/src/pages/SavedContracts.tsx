import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { formatDistance } from 'date-fns'
import { Bookmark, BookmarkX, ExternalLink, FileText, Filter, Search, Tag, Trash2, X } from 'lucide-react'
import { api, SavedRfpWithRfp } from '@/services/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
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
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Textarea } from '@/components/ui/textarea'
import { toast } from 'sonner'
import GenerateBidButton from '@/components/GenerateBidButton'

export default function SavedContracts() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  // Filters state
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedTag, setSelectedTag] = useState<string>('')
  const [selectedFolder, setSelectedFolder] = useState<string>('')
  const [sortBy, setSortBy] = useState('saved_at')
  const [sortOrder, setSortOrder] = useState('desc')

  // Edit dialog state
  const [editingRfp, setEditingRfp] = useState<SavedRfpWithRfp | null>(null)
  const [editNotes, setEditNotes] = useState('')
  const [editTags, setEditTags] = useState('')
  const [editFolder, setEditFolder] = useState('')

  // Selected items for bulk operations
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())

  // Fetch saved RFPs
  const { data, isLoading, error } = useQuery({
    queryKey: ['saved-rfps', searchTerm, selectedTag, selectedFolder, sortBy, sortOrder],
    queryFn: () => api.savedRfps.list({
      search: searchTerm || undefined,
      tag: selectedTag || undefined,
      folder: selectedFolder || undefined,
      sort_by: sortBy,
      sort_order: sortOrder,
    }),
  })

  // Fetch tags for filter dropdown
  const { data: tagsData } = useQuery({
    queryKey: ['saved-rfps-tags'],
    queryFn: () => api.savedRfps.getTags(),
  })

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => api.savedRfps.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['saved-rfps'] })
      setEditingRfp(null)
      toast.success('Saved RFP updated')
    },
    onError: () => toast.error('Failed to update'),
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.savedRfps.unsave(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['saved-rfps'] })
      toast.success('RFP removed from saved list')
    },
    onError: () => toast.error('Failed to remove'),
  })

  // Bulk delete mutation
  const bulkDeleteMutation = useMutation({
    mutationFn: (ids: number[]) => api.savedRfps.bulkUnsave(ids),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['saved-rfps'] })
      setSelectedIds(new Set())
      toast.success(`Removed ${result.deleted_count} RFPs from saved list`)
    },
    onError: () => toast.error('Failed to remove selected RFPs'),
  })

  const handleEdit = (rfp: SavedRfpWithRfp) => {
    setEditingRfp(rfp)
    setEditNotes(rfp.notes || '')
    setEditTags((rfp.tags || []).join(', '))
    setEditFolder(rfp.folder || '')
  }

  const handleSaveEdit = () => {
    if (!editingRfp) return

    const tags = editTags.split(',').map(t => t.trim()).filter(Boolean)
    updateMutation.mutate({
      id: editingRfp.id,
      data: {
        notes: editNotes || null,
        tags,
        folder: editFolder || null,
      },
    })
  }

  const handleBulkDelete = () => {
    if (selectedIds.size === 0) return
    if (confirm(`Remove ${selectedIds.size} RFPs from saved list?`)) {
      bulkDeleteMutation.mutate(Array.from(selectedIds))
    }
  }

  const toggleSelect = (id: number) => {
    const newSelected = new Set(selectedIds)
    if (newSelected.has(id)) {
      newSelected.delete(id)
    } else {
      newSelected.add(id)
    }
    setSelectedIds(newSelected)
  }

  const toggleSelectAll = () => {
    if (selectedIds.size === data?.saved_rfps.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(data?.saved_rfps.map(r => r.id) || []))
    }
  }

  // Get unique folders from data
  const folders = data ? Object.keys(data.folders_summary) : []

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-red-500">Failed to load saved RFPs</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Bookmark className="w-6 h-6" />
            Saved Contracts
          </h1>
          <p className="text-gray-500 mt-1">
            {data?.total ?? 0} saved RFPs
          </p>
        </div>

        {selectedIds.size > 0 && (
          <Button
            variant="destructive"
            onClick={handleBulkDelete}
            disabled={bulkDeleteMutation.isPending}
          >
            <Trash2 className="w-4 h-4 mr-2" />
            Remove Selected ({selectedIds.size})
          </Button>
        )}
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-wrap gap-4">
            <div className="flex-1 min-w-[200px]">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <Input
                  placeholder="Search notes..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>

            <Select value={selectedTag} onValueChange={setSelectedTag}>
              <SelectTrigger className="w-[180px]">
                <Tag className="w-4 h-4 mr-2" />
                <SelectValue placeholder="Filter by tag" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All tags</SelectItem>
                {tagsData?.tags.map(tag => (
                  <SelectItem key={tag} value={tag}>
                    {tag} ({tagsData.counts[tag]})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={selectedFolder} onValueChange={setSelectedFolder}>
              <SelectTrigger className="w-[180px]">
                <Filter className="w-4 h-4 mr-2" />
                <SelectValue placeholder="Filter by folder" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All folders</SelectItem>
                {folders.map(folder => (
                  <SelectItem key={folder} value={folder}>
                    {folder} ({data?.folders_summary[folder]})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={sortBy} onValueChange={setSortBy}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Sort by" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="saved_at">Date Saved</SelectItem>
                <SelectItem value="deadline">Deadline</SelectItem>
                <SelectItem value="title">Title</SelectItem>
              </SelectContent>
            </Select>

            <Select value={sortOrder} onValueChange={setSortOrder}>
              <SelectTrigger className="w-[100px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="desc">Newest</SelectItem>
                <SelectItem value="asc">Oldest</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Tags summary */}
      {data && Object.keys(data.tags_summary).length > 0 && (
        <div className="flex flex-wrap gap-2">
          {Object.entries(data.tags_summary).map(([tag, count]) => (
            <Badge
              key={tag}
              variant={selectedTag === tag ? 'default' : 'secondary'}
              className="cursor-pointer"
              onClick={() => setSelectedTag(selectedTag === tag ? '' : tag)}
            >
              {tag} ({count})
              {selectedTag === tag && <X className="w-3 h-3 ml-1" />}
            </Badge>
          ))}
        </div>
      )}

      {/* Saved RFPs List */}
      {isLoading ? (
        <div className="text-center py-12">
          <p className="text-gray-500">Loading saved RFPs...</p>
        </div>
      ) : data?.saved_rfps.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <BookmarkX className="w-12 h-12 mx-auto text-gray-300 mb-4" />
            <h3 className="text-lg font-medium text-gray-900">No saved RFPs</h3>
            <p className="text-gray-500 mt-1">
              Save RFPs from the Discovery page to see them here
            </p>
            <Button
              className="mt-4"
              onClick={() => navigate('/discovery')}
            >
              Go to Discovery
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {/* Select all checkbox */}
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={selectedIds.size === data?.saved_rfps.length && data?.saved_rfps.length > 0}
              onChange={toggleSelectAll}
              className="rounded border-gray-300"
            />
            <span className="text-sm text-gray-500">Select all</span>
          </div>

          {data?.saved_rfps.map((saved) => (
            <Card key={saved.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-6">
                <div className="flex items-start gap-4">
                  {/* Checkbox */}
                  <input
                    type="checkbox"
                    checked={selectedIds.has(saved.id)}
                    onChange={() => toggleSelect(saved.id)}
                    className="mt-1 rounded border-gray-300"
                  />

                  {/* Main content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between">
                      <div>
                        <h3
                          className="text-lg font-medium text-gray-900 hover:text-blue-600 cursor-pointer"
                          onClick={() => navigate(`/rfps/${saved.rfp_id}`)}
                        >
                          {saved.rfp_title}
                        </h3>
                        <p className="text-sm text-gray-500">
                          {saved.rfp_agency || 'Unknown Agency'}
                          {saved.rfp_stage && (
                            <Badge variant="outline" className="ml-2">
                              {saved.rfp_stage}
                            </Badge>
                          )}
                        </p>
                      </div>

                      <div className="text-right">
                        {saved.rfp_triage_score && (
                          <span className="text-xl font-bold text-blue-600">
                            {saved.rfp_triage_score.toFixed(1)}
                          </span>
                        )}
                        {saved.rfp_deadline && (
                          <p className="text-xs text-gray-500">
                            Due {formatDistance(new Date(saved.rfp_deadline), new Date(), { addSuffix: true })}
                          </p>
                        )}
                      </div>
                    </div>

                    {/* Notes */}
                    {saved.notes && (
                      <p className="mt-2 text-sm text-gray-600 bg-gray-50 p-2 rounded">
                        {saved.notes}
                      </p>
                    )}

                    {/* Tags */}
                    {saved.tags && saved.tags.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {saved.tags.map(tag => (
                          <Badge key={tag} variant="secondary" className="text-xs">
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    )}

                    {/* Folder */}
                    {saved.folder && (
                      <p className="mt-1 text-xs text-gray-400">
                        Folder: {saved.folder}
                      </p>
                    )}

                    {/* Meta info */}
                    <p className="mt-2 text-xs text-gray-400">
                      Saved {formatDistance(new Date(saved.saved_at), new Date(), { addSuffix: true })}
                    </p>
                  </div>

                  {/* Actions */}
                  <div className="flex flex-col gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => navigate(`/rfps/${saved.rfp_id}`)}
                    >
                      <ExternalLink className="w-4 h-4 mr-1" />
                      View
                    </Button>
                    <GenerateBidButton
                      rfpId={String(saved.rfp_id)}
                      rfpTitle={saved.rfp_title}
                    />
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleEdit(saved)}
                    >
                      <FileText className="w-4 h-4 mr-1" />
                      Edit
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="text-red-500 hover:text-red-600"
                      onClick={() => {
                        if (confirm('Remove this RFP from saved list?')) {
                          deleteMutation.mutate(saved.id)
                        }
                      }}
                    >
                      <Trash2 className="w-4 h-4 mr-1" />
                      Remove
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Edit Dialog */}
      <Dialog open={!!editingRfp} onOpenChange={() => setEditingRfp(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Saved RFP</DialogTitle>
            <DialogDescription>
              Update notes, tags, or folder for this saved RFP.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div>
              <label className="text-sm font-medium">Notes</label>
              <Textarea
                value={editNotes}
                onChange={(e) => setEditNotes(e.target.value)}
                placeholder="Add notes about this RFP..."
                rows={3}
              />
            </div>

            <div>
              <label className="text-sm font-medium">Tags (comma-separated)</label>
              <Input
                value={editTags}
                onChange={(e) => setEditTags(e.target.value)}
                placeholder="priority, healthcare, review-needed"
              />
            </div>

            <div>
              <label className="text-sm font-medium">Folder</label>
              <Input
                value={editFolder}
                onChange={(e) => setEditFolder(e.target.value)}
                placeholder="e.g., Q1 2025, Healthcare Bids"
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setEditingRfp(null)}>
              Cancel
            </Button>
            <Button onClick={handleSaveEdit} disabled={updateMutation.isPending}>
              Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
