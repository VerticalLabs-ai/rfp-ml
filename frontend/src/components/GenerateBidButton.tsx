import { Button } from '@/components/ui/button'
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog'
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select'
import { useMutation } from '@tanstack/react-query'
import { Download, Eye, FileText, Loader2 } from 'lucide-react'
import { useState } from 'react'
import toast from 'react-hot-toast'
import { api } from '../services/api'

type GenerationMode = 'template' | 'claude_standard' | 'claude_enhanced' | 'claude_premium'

interface GenerateBidButtonProps {
    rfpId: string
    rfpTitle: string
    defaultMode?: GenerationMode
}

const GENERATION_MODES: { value: GenerationMode; label: string; description: string }[] = [
    { value: 'template', label: '⚡ Fast Draft', description: 'Template-based' },
    { value: 'claude_standard', label: '🤖 AI Standard', description: 'Claude Sonnet' },
    { value: 'claude_enhanced', label: '✨ AI Enhanced', description: 'Claude + Thinking' },
    { value: 'claude_premium', label: '👑 AI Premium', description: 'Claude Opus' }
]

export default function GenerateBidButton({ rfpId, rfpTitle, defaultMode = 'claude_enhanced' }: GenerateBidButtonProps) {
    const [showPreview, setShowPreview] = useState(false)
    const [bidData, setBidData] = useState<any>(null)
    const [generationMode, setGenerationMode] = useState<GenerationMode>(defaultMode)

    const generateMutation = useMutation({
        mutationFn: () => api.generateBid(rfpId, {
            generation_mode: generationMode,
            enable_thinking: generationMode !== 'template' && generationMode !== 'claude_standard',
            thinking_budget: generationMode === 'claude_premium' ? 20000 : 10000
        }),
        onSuccess: (data) => {
            setBidData(data)
            setShowPreview(true)
            const modeLabel = GENERATION_MODES.find(m => m.value === generationMode)?.label || generationMode
            toast.success(`Bid generated with ${modeLabel}!`)
        },
        onError: (error: any) => {
            toast.error(error.response?.data?.detail || 'Failed to generate bid')
        }
    })

    const handleDownload = async (format: 'markdown' | 'html' | 'json') => {
        try {
            const blob = await api.downloadBid(bidData.bid_id, format)
            const url = window.URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url
            a.download = `bid_${rfpId}_${Date.now()}.${format === 'markdown' ? 'md' : format}`
            document.body.appendChild(a)
            a.click()
            window.URL.revokeObjectURL(url)
            document.body.removeChild(a)
            toast.success(`Downloaded as ${format.toUpperCase()}`)
        } catch (error) {
            toast.error('Download failed')
        }
    }

    return (
        <>
            <div className="flex items-center gap-2">
                <Select
                    value={generationMode}
                    onValueChange={(value: GenerationMode) => setGenerationMode(value)}
                >
                    <SelectTrigger className="w-36 h-9">
                        <SelectValue>
                            {GENERATION_MODES.find(m => m.value === generationMode)?.label}
                        </SelectValue>
                    </SelectTrigger>
                    <SelectContent>
                        {GENERATION_MODES.map((mode) => (
                            <SelectItem key={mode.value} value={mode.value}>
                                <span className="flex flex-col">
                                    <span>{mode.label}</span>
                                    <span className="text-xs text-muted-foreground">{mode.description}</span>
                                </span>
                            </SelectItem>
                        ))}
                    </SelectContent>
                </Select>
                <Button
                    onClick={() => generateMutation.mutate()}
                    disabled={generateMutation.isPending}
                    size="sm"
                    variant={generationMode.includes('claude') ? 'default' : 'outline'}
                    className={generationMode.includes('claude') ? 'bg-purple-600 hover:bg-purple-700' : ''}
                >
                    {generateMutation.isPending ? (
                        <>
                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                            Generating...
                        </>
                    ) : (
                        <>
                            <FileText className="w-4 h-4 mr-2" />
                            Generate
                        </>
                    )}
                </Button>
            </div>

            <Dialog open={showPreview} onOpenChange={setShowPreview}>
                <DialogContent className="max-w-4xl max-h-[90vh]">
                    <DialogHeader>
                        <DialogTitle>Bid Document Preview</DialogTitle>
                        <DialogDescription>
                            Generated proposal for: {rfpTitle}
                        </DialogDescription>
                    </DialogHeader>

                    {bidData && (
                        <div className="space-y-4">
                            {/* Document Info */}
                            <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-lg">
                                <h3 className="font-semibold mb-2">Document Information</h3>
                                <div className="grid grid-cols-2 gap-2 text-sm">
                                    <div>
                                        <span className="text-gray-500">Bid ID:</span> {bidData.bid_id}
                                    </div>
                                    <div>
                                        <span className="text-gray-500">Generated:</span>{' '}
                                        {new Date(bidData.generated_at).toLocaleString()}
                                    </div>
                                    <div>
                                        <span className="text-gray-500">Sections:</span>{' '}
                                        {bidData.preview?.sections?.length || 0}
                                    </div>
                                    <div>
                                        <span className="text-gray-500">Mode:</span>{' '}
                                        {bidData.metadata?.processing_mode || 'Full ML Pipeline'}
                                    </div>
                                </div>
                            </div>

                            {/* Preview */}
                            <div className="border rounded-lg p-4 max-h-[400px] overflow-y-auto">
                                <h3 className="font-semibold mb-2 flex items-center gap-2">
                                    <Eye className="w-4 h-4" />
                                    Document Preview
                                </h3>
                                <pre className="text-sm whitespace-pre-wrap font-mono bg-gray-50 dark:bg-gray-900 p-4 rounded">
                                    {bidData.preview?.markdown || 'No preview available'}
                                </pre>
                            </div>

                            {/* Download Options */}
                            <div className="flex gap-3 justify-end border-t pt-4">
                                <Button
                                    onClick={() => handleDownload('markdown')}
                                    variant="outline"
                                    size="sm"
                                >
                                    <Download className="w-4 h-4 mr-2" />
                                    Markdown
                                </Button>
                                <Button
                                    onClick={() => handleDownload('html')}
                                    variant="outline"
                                    size="sm"
                                >
                                    <Download className="w-4 h-4 mr-2" />
                                    HTML
                                </Button>
                                <Button
                                    onClick={() => handleDownload('json')}
                                    variant="outline"
                                    size="sm"
                                >
                                    <Download className="w-4 h-4 mr-2" />
                                    JSON
                                </Button>
                            </div>
                        </div>
                    )}
                </DialogContent>
            </Dialog>
        </>
    )
}
