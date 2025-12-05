import { useState, useCallback } from 'react'
import { Editor } from '@tiptap/react'
import {
  Sparkles,
  Maximize2,
  Minimize2,
  Briefcase,
  SpellCheck,
  Eye,
  AlertTriangle,
  BookOpen,
  Loader2,
  X,
  Check,
  RefreshCw,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'
import { AIActionId, AI_ACTIONS, ReadabilityScore } from '@/types/aiToolbar'

const iconMap = {
  Sparkles,
  Maximize2,
  Minimize2,
  Briefcase,
  SpellCheck,
  Eye,
  AlertTriangle,
  BookOpen,
}

interface AIToolbarProps {
  editor: Editor | null
  rfpId: string
  sectionId: string
  onExecuteAction: (
    actionId: AIActionId,
    selectedText: string,
    fullContent: string
  ) => Promise<string>
  className?: string
}

export function AIToolbar({
  editor,
  rfpId,
  sectionId,
  onExecuteAction,
  className,
}: AIToolbarProps) {
  const [activeAction, setActiveAction] = useState<AIActionId | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const [result, setResult] = useState<string | null>(null)
  const [readabilityScore, setReadabilityScore] =
    useState<ReadabilityScore | null>(null)

  const getSelectedText = useCallback(() => {
    if (!editor) return ''
    const { from, to } = editor.state.selection
    return editor.state.doc.textBetween(from, to, ' ')
  }, [editor])

  const getFullContent = useCallback(() => {
    if (!editor) return ''
    return editor.getText()
  }, [editor])

  const handleAction = async (actionId: AIActionId) => {
    if (!editor || isProcessing) return

    const action = AI_ACTIONS.find((a) => a.id === actionId)
    if (!action) return

    const selectedText = getSelectedText()
    if (action.requiresSelection && !selectedText) {
      // Show toast or feedback that selection is required
      return
    }

    setActiveAction(actionId)
    setIsProcessing(true)
    setResult(null)

    try {
      const response = await onExecuteAction(
        actionId,
        selectedText,
        getFullContent()
      )
      setResult(response)

      if (actionId === 'readability') {
        // Parse readability response
        try {
          setReadabilityScore(JSON.parse(response))
        } catch {
          setReadabilityScore(null)
        }
      }
    } catch (error) {
      console.error('AI action failed:', error)
      setResult('Error processing request. Please try again.')
    } finally {
      setIsProcessing(false)
    }
  }

  const applyResult = () => {
    if (!editor || !result || !activeAction) return

    const action = AI_ACTIONS.find((a) => a.id === activeAction)
    if (!action || action.category === 'analyze') return

    const { from, to } = editor.state.selection
    editor
      .chain()
      .focus()
      .deleteRange({ from, to })
      .insertContent(result)
      .run()

    setResult(null)
    setActiveAction(null)
  }

  const cancelResult = () => {
    setResult(null)
    setActiveAction(null)
  }

  const hasSelection = getSelectedText().length > 0

  return (
    <div
      className={cn(
        'flex items-center gap-1 rounded-lg border bg-background/95 p-1 shadow-lg backdrop-blur',
        className
      )}
    >
      <TooltipProvider delayDuration={300}>
        {/* Transform Actions */}
        <div className="flex items-center gap-0.5">
          {AI_ACTIONS.filter((a) => a.category === 'transform').map(
            (action) => {
              const Icon = iconMap[action.icon as keyof typeof iconMap]
              const isActive = activeAction === action.id
              const isDisabled =
                isProcessing || (action.requiresSelection && !hasSelection)

              return (
                <Tooltip key={action.id}>
                  <TooltipTrigger asChild>
                    <Button
                      variant={isActive ? 'secondary' : 'ghost'}
                      size="sm"
                      className="h-8 w-8 p-0"
                      disabled={isDisabled}
                      onClick={() => handleAction(action.id)}
                    >
                      {isActive && isProcessing ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Icon className="h-4 w-4" />
                      )}
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p className="font-medium">{action.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {action.description}
                    </p>
                    {action.requiresSelection && !hasSelection && (
                      <p className="text-xs text-yellow-500">
                        Select text first
                      </p>
                    )}
                  </TooltipContent>
                </Tooltip>
              )
            }
          )}
        </div>

        <div className="mx-1 h-6 w-px bg-border" />

        {/* Analyze Actions */}
        <div className="flex items-center gap-0.5">
          {AI_ACTIONS.filter((a) => a.category === 'analyze').map((action) => {
            const Icon = iconMap[action.icon as keyof typeof iconMap]
            const isActive = activeAction === action.id
            const isDisabled =
              isProcessing || (action.requiresSelection && !hasSelection)

            return (
              <Popover key={action.id}>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <PopoverTrigger asChild>
                      <Button
                        variant={isActive ? 'secondary' : 'ghost'}
                        size="sm"
                        className="h-8 w-8 p-0"
                        disabled={isDisabled}
                        onClick={() => handleAction(action.id)}
                      >
                        {isActive && isProcessing ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Icon className="h-4 w-4" />
                        )}
                      </Button>
                    </PopoverTrigger>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p className="font-medium">{action.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {action.description}
                    </p>
                  </TooltipContent>
                </Tooltip>

                {action.id === 'readability' && readabilityScore && (
                  <PopoverContent className="w-72">
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="font-medium">Readability Score</span>
                        <Badge
                          variant={
                            readabilityScore.score >= 60
                              ? 'default'
                              : 'destructive'
                          }
                        >
                          {readabilityScore.score}/100
                        </Badge>
                      </div>
                      <div className="text-sm text-muted-foreground">
                        <p>Grade Level: {readabilityScore.grade}</p>
                        <p>
                          Avg Sentence: {readabilityScore.avgSentenceLength}{' '}
                          words
                        </p>
                        <p>Avg Word: {readabilityScore.avgWordLength} chars</p>
                      </div>
                      {readabilityScore.suggestions.length > 0 && (
                        <div>
                          <p className="mb-1 text-sm font-medium">
                            Suggestions:
                          </p>
                          <ul className="list-inside list-disc text-sm text-muted-foreground">
                            {readabilityScore.suggestions.map((s, i) => (
                              <li key={i}>{s}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  </PopoverContent>
                )}
              </Popover>
            )
          })}
        </div>
      </TooltipProvider>

      {/* Result Preview */}
      {result &&
        activeAction &&
        AI_ACTIONS.find((a) => a.id === activeAction)?.category ===
          'transform' && (
          <Popover open={!!result} onOpenChange={() => cancelResult()}>
            <PopoverContent className="w-96" align="end">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="font-medium">AI Suggestion</span>
                  <div className="flex gap-1">
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-7 w-7 p-0"
                      onClick={() => handleAction(activeAction)}
                    >
                      <RefreshCw className="h-3 w-3" />
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-7 w-7 p-0"
                      onClick={cancelResult}
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
                <ScrollArea className="h-32">
                  <p className="text-sm">{result}</p>
                </ScrollArea>
                <div className="flex justify-end gap-2">
                  <Button size="sm" variant="outline" onClick={cancelResult}>
                    Cancel
                  </Button>
                  <Button size="sm" onClick={applyResult}>
                    <Check className="mr-1 h-3 w-3" />
                    Apply
                  </Button>
                </div>
              </div>
            </PopoverContent>
          </Popover>
        )}
    </div>
  )
}
