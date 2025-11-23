import { Button } from '@/components/ui/button'
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Loader2, Plus } from 'lucide-react'
import { useState } from 'react'
import toast from 'react-hot-toast'
import { api } from '../services/api'

export default function AddRFPDialog() {
    const [open, setOpen] = useState(false)
    const queryClient = useQueryClient()

    const [formData, setFormData] = useState({
        title: '',
        agency: '',
        solicitation_number: '',
        description: '',
        url: '',
        award_amount: '',
        response_deadline: '',
        category: 'general'
    })

    const processMutation = useMutation({
        mutationFn: (data: any) => api.processManualRFP(data),
        onSuccess: (data) => {
            queryClient.invalidateQueries({ queryKey: ['discovered-rfps'] })
            queryClient.invalidateQueries({ queryKey: ['rfp-stats'] })
            toast.success(
                `RFP processed successfully! Triage Score: ${data.triage_score?.toFixed(1)} - ${data.decision_recommendation?.toUpperCase()}`
            )
            setOpen(false)
            // Reset form
            setFormData({
                title: '',
                agency: '',
                solicitation_number: '',
                description: '',
                url: '',
                award_amount: '',
                response_deadline: '',
                category: 'general'
            })
        },
        onError: (error: any) => {
            toast.error(error.response?.data?.detail || 'Failed to process RFP')
        }
    })

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault()

        const submitData = {
            ...formData,
            award_amount: formData.award_amount ? parseFloat(formData.award_amount) : undefined,
            response_deadline: formData.response_deadline || undefined
        }

        processMutation.mutate(submitData)
    }

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
                <Button>
                    <Plus className="w-4 h-4 mr-2" />
                    Add RFP
                </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>Add RFP Manually</DialogTitle>
                    <DialogDescription>
                        Enter RFP details to process through the ML pipeline for triage scoring and decision analysis.
                    </DialogDescription>
                </DialogHeader>

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                        <div className="col-span-2">
                            <Label htmlFor="title">Title *</Label>
                            <Input
                                id="title"
                                value={formData.title}
                                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                                required
                                placeholder="Enter RFP title"
                            />
                        </div>

                        <div>
                            <Label htmlFor="agency">Agency</Label>
                            <Input
                                id="agency"
                                value={formData.agency}
                                onChange={(e) => setFormData({ ...formData, agency: e.target.value })}
                                placeholder="e.g., GSA, DOD"
                            />
                        </div>

                        <div>
                            <Label htmlFor="solicitation_number">Solicitation Number</Label>
                            <Input
                                id="solicitation_number"
                                value={formData.solicitation_number}
                                onChange={(e) => setFormData({ ...formData, solicitation_number: e.target.value })}
                                placeholder="e.g., 12345-SOL-2025"
                            />
                        </div>

                        <div>
                            <Label htmlFor="url">SAM.gov URL</Label>
                            <Input
                                id="url"
                                type="url"
                                value={formData.url}
                                onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                                placeholder="https://sam.gov/..."
                            />
                        </div>

                        <div>
                            <Label htmlFor="award_amount">Award Amount ($)</Label>
                            <Input
                                id="award_amount"
                                type="number"
                                value={formData.award_amount}
                                onChange={(e) => setFormData({ ...formData, award_amount: e.target.value })}
                                placeholder="100000"
                            />
                        </div>

                        <div>
                            <Label htmlFor="response_deadline">Response Deadline</Label>
                            <Input
                                id="response_deadline"
                                type="date"
                                value={formData.response_deadline}
                                onChange={(e) => setFormData({ ...formData, response_deadline: e.target.value })}
                            />
                        </div>

                        <div>
                            <Label htmlFor="category">Category</Label>
                            <Input
                                id="category"
                                value={formData.category}
                                onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                                placeholder="general"
                            />
                        </div>

                        <div className="col-span-2">
                            <Label htmlFor="description">Description</Label>
                            <Textarea
                                id="description"
                                value={formData.description}
                                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                placeholder="Enter RFP description and requirements..."
                                rows={4}
                            />
                        </div>
                    </div>

                    <div className="flex gap-3 justify-end">
                        <Button
                            type="button"
                            variant="outline"
                            onClick={() => setOpen(false)}
                            disabled={processMutation.isPending}
                        >
                            Cancel
                        </Button>
                        <Button
                            type="submit"
                            disabled={processMutation.isPending || !formData.title}
                        >
                            {processMutation.isPending ? (
                                <>
                                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                    Processing...
                                </>
                            ) : (
                                'Process RFP'
                            )}
                        </Button>
                    </div>
                </form>
            </DialogContent>
        </Dialog>
    )
}
