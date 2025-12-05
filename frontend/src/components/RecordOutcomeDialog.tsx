/**
 * Record Outcome Dialog Component
 *
 * Modal dialog for recording bid outcomes (win/loss/pending/no_bid/withdrawn).
 * Includes conditional fields that appear based on outcome status.
 */
import { useState, useEffect } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
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
import { Textarea } from '@/components/ui/textarea'
import { api } from '@/services/api'
import type { BidOutcomeCreate, BidStatus } from '@/types/analytics'

interface RecordOutcomeDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export default function RecordOutcomeDialog({
  open,
  onOpenChange,
}: RecordOutcomeDialogProps) {
  const queryClient = useQueryClient()
  const [formData, setFormData] = useState<BidOutcomeCreate>({
    rfp_id: 0,
    status: 'pending',
  })

  // Reset form when dialog closes
  useEffect(() => {
    if (!open) {
      setFormData({
        rfp_id: 0,
        status: 'pending',
      })
    }
  }, [open])

  const createMutation = useMutation({
    mutationFn: (data: BidOutcomeCreate) => api.createBidOutcome(data),
    onSuccess: () => {
      toast.success('Bid outcome recorded successfully')
      queryClient.invalidateQueries({ queryKey: ['analytics-overview'] })
      onOpenChange(false)
      // Reset form
      setFormData({
        rfp_id: 0,
        status: 'pending',
      })
    },
    onError: (error: any) => {
      toast.error(
        error.response?.data?.detail || 'Failed to record bid outcome'
      )
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    // Validation
    if (!formData.rfp_id || formData.rfp_id <= 0) {
      toast.error('Please enter a valid RFP ID')
      return
    }

    // Prepare data - only include optional fields if they have values
    const submitData: BidOutcomeCreate = {
      rfp_id: formData.rfp_id,
      status: formData.status,
    }

    if (formData.award_amount !== undefined && formData.award_amount > 0) {
      submitData.award_amount = formData.award_amount
    }

    if (formData.our_bid_amount !== undefined && formData.our_bid_amount > 0) {
      submitData.our_bid_amount = formData.our_bid_amount
    }

    if (formData.winning_bidder?.trim()) {
      submitData.winning_bidder = formData.winning_bidder.trim()
    }

    if (
      formData.winning_bid_amount !== undefined &&
      formData.winning_bid_amount > 0
    ) {
      submitData.winning_bid_amount = formData.winning_bid_amount
    }

    if (formData.loss_reason?.trim()) {
      submitData.loss_reason = formData.loss_reason.trim()
    }

    if (formData.debrief_notes?.trim()) {
      submitData.debrief_notes = formData.debrief_notes.trim()
    }

    if (formData.award_date) {
      submitData.award_date = formData.award_date
    }

    createMutation.mutate(submitData)
  }

  const handleStatusChange = (status: BidStatus) => {
    setFormData((prev) => ({
      ...prev,
      status,
      // Clear loss-specific fields if not lost
      ...(status !== 'lost' && {
        winning_bidder: undefined,
        winning_bid_amount: undefined,
        loss_reason: undefined,
      }),
    }))
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Record Bid Outcome</DialogTitle>
          <DialogDescription>
            Record the outcome of a bid to track win/loss analytics and improve
            future bid strategies.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            {/* RFP ID */}
            <div className="col-span-2">
              <Label htmlFor="rfp_id">
                RFP ID <span className="text-red-500">*</span>
              </Label>
              <Input
                id="rfp_id"
                type="number"
                min="1"
                value={formData.rfp_id || ''}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    rfp_id: parseInt(e.target.value) || 0,
                  })
                }
                required
                placeholder="Enter RFP ID"
                disabled={createMutation.isPending}
              />
            </div>

            {/* Status */}
            <div className="col-span-2">
              <Label htmlFor="status">
                Status <span className="text-red-500">*</span>
              </Label>
              <Select
                value={formData.status}
                onValueChange={handleStatusChange}
                disabled={createMutation.isPending}
              >
                <SelectTrigger id="status">
                  <SelectValue placeholder="Select outcome status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="won">Won</SelectItem>
                  <SelectItem value="lost">Lost</SelectItem>
                  <SelectItem value="pending">Pending</SelectItem>
                  <SelectItem value="no_bid">No Bid</SelectItem>
                  <SelectItem value="withdrawn">Withdrawn</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Award Amount */}
            <div>
              <Label htmlFor="award_amount">Award Amount ($)</Label>
              <Input
                id="award_amount"
                type="number"
                min="0"
                step="0.01"
                value={formData.award_amount || ''}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    award_amount: parseFloat(e.target.value) || undefined,
                  })
                }
                placeholder="0.00"
                disabled={createMutation.isPending}
              />
            </div>

            {/* Our Bid Amount */}
            <div>
              <Label htmlFor="our_bid_amount">Our Bid Amount ($)</Label>
              <Input
                id="our_bid_amount"
                type="number"
                min="0"
                step="0.01"
                value={formData.our_bid_amount || ''}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    our_bid_amount: parseFloat(e.target.value) || undefined,
                  })
                }
                placeholder="0.00"
                disabled={createMutation.isPending}
              />
            </div>

            {/* Conditional Fields for Lost Status */}
            {formData.status === 'lost' && (
              <>
                {/* Winning Bidder */}
                <div>
                  <Label htmlFor="winning_bidder">Winning Bidder</Label>
                  <Input
                    id="winning_bidder"
                    value={formData.winning_bidder || ''}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        winning_bidder: e.target.value,
                      })
                    }
                    placeholder="Competitor name"
                    disabled={createMutation.isPending}
                  />
                </div>

                {/* Winning Bid Amount */}
                <div>
                  <Label htmlFor="winning_bid_amount">
                    Winning Bid Amount ($)
                  </Label>
                  <Input
                    id="winning_bid_amount"
                    type="number"
                    min="0"
                    step="0.01"
                    value={formData.winning_bid_amount || ''}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        winning_bid_amount:
                          parseFloat(e.target.value) || undefined,
                      })
                    }
                    placeholder="0.00"
                    disabled={createMutation.isPending}
                  />
                </div>

                {/* Loss Reason */}
                <div className="col-span-2">
                  <Label htmlFor="loss_reason">Loss Reason</Label>
                  <Textarea
                    id="loss_reason"
                    value={formData.loss_reason || ''}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        loss_reason: e.target.value,
                      })
                    }
                    placeholder="Why did we lose this bid?"
                    rows={3}
                    disabled={createMutation.isPending}
                  />
                </div>
              </>
            )}

            {/* Award Date */}
            <div>
              <Label htmlFor="award_date">Award Date</Label>
              <Input
                id="award_date"
                type="date"
                value={formData.award_date || ''}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    award_date: e.target.value,
                  })
                }
                disabled={createMutation.isPending}
              />
            </div>

            {/* Debrief Notes */}
            <div className="col-span-2">
              <Label htmlFor="debrief_notes">Debrief Notes</Label>
              <Textarea
                id="debrief_notes"
                value={formData.debrief_notes || ''}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    debrief_notes: e.target.value,
                  })
                }
                placeholder="Additional notes from debrief or post-mortem..."
                rows={3}
                disabled={createMutation.isPending}
              />
            </div>
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={createMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={createMutation.isPending || !formData.rfp_id}
            >
              {createMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Recording...
                </>
              ) : (
                'Record Outcome'
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
