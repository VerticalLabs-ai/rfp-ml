import { useMemo } from 'react'
import { FileText, Clock, Target, AlertCircle } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { Progress } from '@/components/ui/progress'
import { cn } from '@/lib/utils'

interface WritingStatsProps {
  content: string
  sectionType: string
  targetWordCount?: number
  className?: string
}

// Approximate word counts per section type
const SECTION_TARGETS: Record<string, { min: number; target: number; max: number }> = {
  executive_summary: { min: 300, target: 500, max: 750 },
  technical_approach: { min: 800, target: 1500, max: 2500 },
  company_qualifications: { min: 400, target: 700, max: 1000 },
  management_approach: { min: 500, target: 800, max: 1200 },
  pricing_narrative: { min: 300, target: 500, max: 800 },
  past_performance: { min: 600, target: 1000, max: 1500 },
  staffing_plan: { min: 400, target: 600, max: 900 },
  quality_assurance: { min: 300, target: 500, max: 800 },
  risk_mitigation: { min: 300, target: 500, max: 800 },
  compliance_matrix: { min: 200, target: 400, max: 600 },
}

// Average reading speed (words per minute)
const READING_SPEED = 200
// Average words per page (single-spaced, standard margins)
const WORDS_PER_PAGE = 500

export function WritingStats({
  content,
  sectionType,
  targetWordCount,
  className,
}: WritingStatsProps) {
  const stats = useMemo(() => {
    const text = content.replace(/<[^>]*>/g, ' ').trim()
    const words = text.split(/\s+/).filter((w) => w.length > 0)
    const wordCount = words.length
    const charCount = text.length
    const sentences = text.split(/[.!?]+/).filter((s) => s.trim().length > 0)
    const paragraphs = text.split(/\n\n+/).filter((p) => p.trim().length > 0)

    const avgWordLength = charCount / Math.max(wordCount, 1)
    const avgSentenceLength = wordCount / Math.max(sentences.length, 1)
    const readingTime = Math.ceil(wordCount / READING_SPEED)
    const pageEstimate = (wordCount / WORDS_PER_PAGE).toFixed(1)

    // Get target for section type
    const targets = SECTION_TARGETS[sectionType] || { min: 200, target: 500, max: 1000 }
    const effectiveTarget = targetWordCount || targets.target

    // Calculate progress
    const progress = Math.min((wordCount / effectiveTarget) * 100, 100)

    // Determine status
    let status: 'under' | 'good' | 'over' = 'under'
    if (wordCount >= targets.min && wordCount <= targets.max) {
      status = 'good'
    } else if (wordCount > targets.max) {
      status = 'over'
    }

    return {
      wordCount,
      charCount,
      sentences: sentences.length,
      paragraphs: paragraphs.length,
      avgWordLength: avgWordLength.toFixed(1),
      avgSentenceLength: avgSentenceLength.toFixed(1),
      readingTime,
      pageEstimate,
      progress,
      status,
      targets,
      effectiveTarget,
    }
  }, [content, sectionType, targetWordCount])

  const statusColors = {
    under: 'text-yellow-500',
    good: 'text-green-500',
    over: 'text-red-500',
  }

  const statusLabels = {
    under: 'Below target',
    good: 'On target',
    over: 'Over limit',
  }

  return (
    <TooltipProvider>
      <div
        className={cn(
          'flex flex-wrap items-center gap-4 text-sm text-muted-foreground',
          className
        )}
      >
        {/* Word Count */}
        <Tooltip>
          <TooltipTrigger asChild>
            <div className="flex items-center gap-1.5">
              <FileText className="h-4 w-4" />
              <span className={cn('font-medium', statusColors[stats.status])}>
                {stats.wordCount.toLocaleString()}
              </span>
              <span>/ {stats.effectiveTarget.toLocaleString()} words</span>
            </div>
          </TooltipTrigger>
          <TooltipContent>
            <div className="space-y-1">
              <p className="font-medium">{statusLabels[stats.status]}</p>
              <p>
                Target: {stats.targets.min} - {stats.targets.max} words
              </p>
              <p>{stats.charCount.toLocaleString()} characters</p>
              <p>{stats.sentences} sentences</p>
              <p>{stats.paragraphs} paragraphs</p>
            </div>
          </TooltipContent>
        </Tooltip>

        {/* Progress Bar */}
        <div className="w-24">
          <Progress
            value={stats.progress}
            className={cn(
              'h-2',
              stats.status === 'under' && '[&>div]:bg-yellow-500',
              stats.status === 'good' && '[&>div]:bg-green-500',
              stats.status === 'over' && '[&>div]:bg-red-500'
            )}
          />
        </div>

        {/* Reading Time */}
        <Tooltip>
          <TooltipTrigger asChild>
            <div className="flex items-center gap-1.5">
              <Clock className="h-4 w-4" />
              <span>{stats.readingTime} min read</span>
            </div>
          </TooltipTrigger>
          <TooltipContent>
            <p>Estimated reading time at {READING_SPEED} words/min</p>
          </TooltipContent>
        </Tooltip>

        {/* Page Estimate */}
        <Tooltip>
          <TooltipTrigger asChild>
            <div className="flex items-center gap-1.5">
              <Target className="h-4 w-4" />
              <span>~{stats.pageEstimate} pages</span>
            </div>
          </TooltipTrigger>
          <TooltipContent>
            <p>
              Estimated at {WORDS_PER_PAGE} words/page (single-spaced)
            </p>
          </TooltipContent>
        </Tooltip>

        {/* Status Badge */}
        <Badge
          variant={stats.status === 'good' ? 'default' : 'secondary'}
          className={cn(
            stats.status === 'under' && 'bg-yellow-100 text-yellow-800',
            stats.status === 'over' && 'bg-red-100 text-red-800'
          )}
        >
          {stats.status === 'under' && (
            <AlertCircle className="mr-1 h-3 w-3" />
          )}
          {Math.round(stats.progress)}% complete
        </Badge>
      </div>
    </TooltipProvider>
  )
}
