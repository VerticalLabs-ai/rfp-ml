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
import { Progress } from '@/components/ui/progress'
import { useQueryClient } from '@tanstack/react-query'
import { CheckCircle, Globe, Search, XCircle } from 'lucide-react'
import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { api } from '../services/api'

export default function DiscoveryButton() {
    const [isOpen, setIsOpen] = useState(false)
    const [isDiscovering, setIsDiscovering] = useState(false)
    const [jobId, setJobId] = useState<string | null>(null)
    const [status, setStatus] = useState<string | null>(null)
    const [progress, setProgress] = useState(0)
    const [discoveredCount, setDiscoveredCount] = useState(0)
    const [processedCount, setProcessedCount] = useState(0)

    // Configuration state
    const [limit, setLimit] = useState(50)
    const [daysBack, setDaysBack] = useState(30)

    const queryClient = useQueryClient()

    const handleDiscover = async () => {
        setIsDiscovering(true)
        setProgress(0)
        setDiscoveredCount(0)
        setProcessedCount(0)
        setJobId(null)
        setStatus("starting")

        try {
            // Start discovery job with parameters
            const response = await api.discoverRFPs({ limit, days_back: daysBack })
            setJobId(response.data.job_id)
            setStatus("searching")
            setProgress(10)
            toast.success('RFP discovery started!')
        } catch (error: any) {
            console.error("Failed to start discovery:", error)
            setStatus("failed")
            setIsDiscovering(false)
            toast.error(error.response?.data?.detail || 'Failed to start discovery')
        }
    }

    // Poll for status updates
    useEffect(() => {
        if (!jobId || !isDiscovering) return

        const interval = setInterval(async () => {
            try {
                const response = await api.getDiscoveryStatus(jobId)
                const statusData = response.data

                setStatus(statusData.status)
                setDiscoveredCount(statusData.discovered_count || 0)
                setProcessedCount(statusData.processed_count || 0)

                if (statusData.status === 'searching') {
                    setProgress(10 + (statusData.progress || 0) * 0.4) // 10% to 50%
                } else if (statusData.status === 'processing') {
                    setProgress(50 + (statusData.progress || 0) * 0.5) // 50% to 100%
                } else if (statusData.status === 'completed') {
                    clearInterval(interval)
                    setProgress(100)
                    queryClient.invalidateQueries({ queryKey: ['discovered-rfps'] })
                    queryClient.invalidateQueries({ queryKey: ['rfp-stats'] })
                    toast.success(`Discovery complete! Found ${statusData.discovered_count} RFPs`)
                } else if (statusData.status === 'failed') {
                    clearInterval(interval)
                    setProgress(0)
                    toast.error('Discovery failed - check the modal for details')
                }
            } catch (error: any) {
                console.error('Failed to fetch status:', error)
                setStatus('failed')
                toast.error(error.response?.data?.detail || error.message || 'Failed to fetch status')
                clearInterval(interval)
            }
        }, 2000)

        return () => clearInterval(interval)
    }, [jobId, isDiscovering, queryClient])

    const handleCloseModal = () => {
        // Only allow closing if not actively running (or if user really wants to background it)
        // For now, we'll allow closing and it keeps running in background, but we reset UI state if it was done
        setIsOpen(false)

        if (status === 'completed' || status === 'failed') {
            setIsDiscovering(false)
            setJobId(null)
            setStatus(null)
            setProgress(0)
            setDiscoveredCount(0)
            setProcessedCount(0)
        }
    }

    const handleCancel = () => {
        // Just close the modal for now, backend job continues
        setIsOpen(false)
    }

    return (
        <>
            <Button
                onClick={() => setIsOpen(true)}
                className="bg-indigo-600 hover:bg-indigo-700 text-white gap-2"
            >
                <Search className="h-4 w-4" />
                Discover New RFPs
            </Button>

            <Dialog open={isOpen} onOpenChange={handleCloseModal}>
                <DialogContent className="sm:max-w-md">
                    <DialogHeader>
                        <DialogTitle>Discover New RFPs</DialogTitle>
                        <DialogDescription>
                            Search SAM.gov for new opportunities and process them through the ML pipeline.
                        </DialogDescription>
                    </DialogHeader>

                    {!isDiscovering ? (
                        <div className="grid gap-4 py-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <label className="text-sm font-medium">Max Results</label>
                                    <Input
                                        type="number"
                                        value={limit}
                                        onChange={(e) => {
                                            const val = parseInt(e.target.value, 10)
                                            if (!isNaN(val)) setLimit(Math.max(10, Math.min(500, val)))
                                        }}
                                        min={10}
                                        max={500}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <label className="text-sm font-medium">Days Back</label>
                                    <Input
                                        type="number"
                                        value={daysBack}
                                        onChange={(e) => {
                                            const val = parseInt(e.target.value, 10)
                                            if (!isNaN(val)) setDaysBack(Math.max(1, Math.min(90, val)))
                                        }}
                                        min={1}
                                        max={90}
                                    />
                                </div>
                            </div>
                            <div className="bg-blue-50 text-blue-700 p-3 rounded-md text-sm flex gap-2">
                                <Globe className="h-4 w-4 mt-0.5 shrink-0" />
                                <div>
                                    Searching <strong>SAM.gov</strong> via API.
                                    <br />
                                    <span className="text-xs opacity-80">Falls back to local archive if API fails.</span>
                                </div>
                            </div>
                        </div>
                    ) : (
                        <div className="py-6 space-y-6">
                            <div className="space-y-2">
                                <div className="flex justify-between text-sm">
                                    <span className="text-muted-foreground capitalize">
                                        {status === 'starting' && 'Starting discovery...'}
                                        {status === 'searching' && 'Searching SAM.gov...'}
                                        {status === 'processing' && 'Analyzing RFPs...'}
                                        {status === 'completed' && 'Discovery complete!'}
                                        {status === 'failed' && 'Discovery failed!'}
                                    </span>
                                    <span className="font-medium">{Math.round(progress)}%</span>
                                </div>
                                <Progress value={progress} className="h-2" />
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div className="bg-slate-50 p-3 rounded-lg border text-center">
                                    <div className="text-2xl font-bold text-slate-900">{discoveredCount}</div>
                                    <div className="text-xs text-muted-foreground uppercase tracking-wider mt-1">Found</div>
                                </div>
                                <div className="bg-slate-50 p-3 rounded-lg border text-center">
                                    <div className="text-2xl font-bold text-indigo-600">{processedCount}</div>
                                    <div className="text-xs text-muted-foreground uppercase tracking-wider mt-1">Processed</div>
                                </div>
                            </div>

                            {status === 'completed' && (
                                <div className="flex items-center gap-2 text-green-600 bg-green-50 p-3 rounded-md">
                                    <CheckCircle className="h-5 w-5" />
                                    <div className="text-sm font-medium">
                                        Discovery complete!
                                        <div className="text-xs opacity-90">
                                            Discovered {discoveredCount} RFPs, processed {processedCount}
                                        </div>
                                    </div>
                                </div>
                            )}

                            {status === 'failed' && (
                                <div className="flex items-center gap-3 text-red-600 bg-red-50 p-3 rounded-md">
                                    <XCircle className="h-5 w-5" />
                                    <div>
                                        <p className="font-medium">Discovery failed</p>
                                        <p className="text-sm">An error occurred during discovery.</p>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    <DialogFooter className={!isDiscovering ? "sm:justify-between" : "sm:justify-end"}>
                        {!isDiscovering ? (
                            <>
                                <Button variant="ghost" onClick={handleCloseModal}>Cancel</Button>
                                <Button onClick={handleDiscover} disabled={isDiscovering}>
                                    Start Discovery
                                </Button>
                            </>
                        ) : (
                            <Button
                                onClick={handleCancel}
                                variant="outline"
                                className="w-full sm:w-auto"
                            >
                                {status === 'completed' ? 'Done' : 'Run in Background'}
                            </Button>
                        )}
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>
    )
}
