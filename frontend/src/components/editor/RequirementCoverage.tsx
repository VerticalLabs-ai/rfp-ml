import { useMemo } from 'react'
import { CheckCircle2, Circle, AlertCircle } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Button } from '@/components/ui/button'
import { ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Requirement {
  id: string
  text: string
  keywords: string[]
  priority: 'must' | 'should' | 'may'
}

interface RequirementCoverageProps {
  content: string
  requirements: Requirement[]
  className?: string
}

export function RequirementCoverage({
  content,
  requirements,
  className,
}: RequirementCoverageProps) {
  const coverage = useMemo(() => {
    const normalizedContent = content.toLowerCase()

    return requirements.map((req) => {
      const matches = req.keywords.filter((kw) =>
        normalizedContent.includes(kw.toLowerCase())
      )
      const covered = matches.length >= Math.ceil(req.keywords.length * 0.5)
      const partialCoverage = matches.length / req.keywords.length

      return {
        ...req,
        covered,
        partialCoverage,
        matchedKeywords: matches,
        missingKeywords: req.keywords.filter((kw) => !matches.includes(kw)),
      }
    })
  }, [content, requirements])

  const stats = useMemo(() => {
    const covered = coverage.filter((r) => r.covered).length
    const mustRequirements = coverage.filter((r) => r.priority === 'must')
    const mustCovered = mustRequirements.filter((r) => r.covered).length

    return {
      total: coverage.length,
      covered,
      percentage: Math.round((covered / Math.max(coverage.length, 1)) * 100),
      mustTotal: mustRequirements.length,
      mustCovered,
      mustPercentage: Math.round(
        (mustCovered / Math.max(mustRequirements.length, 1)) * 100
      ),
    }
  }, [coverage])

  const priorityIcons = {
    must: <AlertCircle className="h-3 w-3 text-red-500" />,
    should: <Circle className="h-3 w-3 text-yellow-500" />,
    may: <Circle className="h-3 w-3 text-blue-500" />,
  }

  return (
    <TooltipProvider>
      <div className={cn('space-y-3', className)}>
        {/* Summary */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">Requirement Coverage</span>
            <Badge variant={stats.percentage >= 80 ? 'default' : 'secondary'}>
              {stats.covered}/{stats.total}
            </Badge>
          </div>
          <Tooltip>
            <TooltipTrigger>
              <Badge
                variant={stats.mustPercentage >= 100 ? 'default' : 'destructive'}
              >
                {stats.mustCovered}/{stats.mustTotal} Must-Have
              </Badge>
            </TooltipTrigger>
            <TooltipContent>
              <p>
                {stats.mustPercentage}% of mandatory requirements addressed
              </p>
            </TooltipContent>
          </Tooltip>
        </div>

        {/* Progress */}
        <Progress
          value={stats.percentage}
          className={cn(
            'h-2',
            stats.percentage < 50 && '[&>div]:bg-red-500',
            stats.percentage >= 50 &&
              stats.percentage < 80 &&
              '[&>div]:bg-yellow-500',
            stats.percentage >= 80 && '[&>div]:bg-green-500'
          )}
        />

        {/* Detailed List */}
        <Collapsible>
          <CollapsibleTrigger asChild>
            <Button variant="ghost" size="sm" className="w-full justify-between">
              View Requirements
              <ChevronDown className="h-4 w-4" />
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <div className="mt-2 space-y-2">
              {coverage.map((req) => (
                <div
                  key={req.id}
                  className={cn(
                    'flex items-start gap-2 rounded-md p-2 text-sm',
                    req.covered ? 'bg-green-50' : 'bg-muted'
                  )}
                >
                  {req.covered ? (
                    <CheckCircle2 className="mt-0.5 h-4 w-4 text-green-500" />
                  ) : (
                    priorityIcons[req.priority]
                  )}
                  <div className="flex-1">
                    <p
                      className={cn(
                        'font-medium',
                        req.covered
                          ? 'text-green-700'
                          : 'text-muted-foreground'
                      )}
                    >
                      {req.text}
                    </p>
                    {!req.covered && req.missingKeywords.length > 0 && (
                      <p className="mt-1 text-xs text-muted-foreground">
                        Missing: {req.missingKeywords.join(', ')}
                      </p>
                    )}
                  </div>
                  <Badge
                    variant="outline"
                    className={cn(
                      'text-xs',
                      req.priority === 'must' && 'border-red-300 text-red-700',
                      req.priority === 'should' &&
                        'border-yellow-300 text-yellow-700',
                      req.priority === 'may' && 'border-blue-300 text-blue-700'
                    )}
                  >
                    {req.priority}
                  </Badge>
                </div>
              ))}
            </div>
          </CollapsibleContent>
        </Collapsible>
      </div>
    </TooltipProvider>
  )
}
