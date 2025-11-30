import { useState, useCallback, useRef, useEffect } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import {
  Wand2,
  Sparkles,
  FileText,
  Users,
  Shield,
  Clock,
  DollarSign,
  CheckSquare,
  AlertTriangle,
  Loader2,
  Copy,
  Check,
  ChevronDown,
  Expand,
  Shrink,
  RefreshCw,
} from 'lucide-react'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'

interface WriterCommand {
  command: string
  name: string
  description: string
  default_max_words: number
  shortcut: string
}

interface WriterResponse {
  command: string
  section_name: string
  content: string
  word_count: number
  confidence_score: number
  generation_method: string
  rfp_id: string
  suggestions: string[]
}

interface AIWriterMenuProps {
  rfpId: string
  rfpTitle: string
  onContentGenerated?: (content: string, sectionName: string) => void
  className?: string
}

const COMMAND_ICONS: Record<string, typeof FileText> = {
  'executive-summary': FileText,
  'technical-approach': Wand2,
  'past-performance': Clock,
  'management-approach': Users,
  'staffing-plan': Users,
  'quality-control': CheckSquare,
  'risk-mitigation': AlertTriangle,
  'transition-plan': RefreshCw,
  'compliance-matrix': Shield,
  'pricing-narrative': DollarSign,
  'cover-letter': FileText,
  'capability-statement': Sparkles,
}

export function AIWriterMenu({
  rfpId,
  rfpTitle,
  onContentGenerated,
  className
}: AIWriterMenuProps) {
  const [open, setOpen] = useState(false)
  const [selectedCommand, setSelectedCommand] = useState<WriterCommand | null>(null)
  const [context, setContext] = useState('')
  const [tone, setTone] = useState('professional')
  const [generatedContent, setGeneratedContent] = useState('')
  const [copied, setCopied] = useState(false)
  const [isExpanded, setIsExpanded] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Fetch available commands
  const { data: commands } = useQuery({
    queryKey: ['writer', 'commands'],
    queryFn: () => api.get<{ commands: WriterCommand[]; total: number }>('/generation/writer/commands'),
  })

  // Execute writer command
  const executeCommand = useMutation({
    mutationFn: async (command: WriterCommand) => {
      return api.post<WriterResponse>(`/generation/${rfpId}/writer`, {
        command: command.command,
        context: context,
        tone: tone,
        include_citations: false,
      })
    },
    onSuccess: (response) => {
      setGeneratedContent(response.content)
      onContentGenerated?.(response.content, response.section_name)
    },
  })

  // Improve content
  const improveContent = useMutation({
    mutationFn: async (instruction: string) => {
      return api.post<{ improved_text: string }>(`/generation/${rfpId}/writer/improve`, {
        text: generatedContent,
        instruction: instruction,
        context: context,
      })
    },
    onSuccess: (response) => {
      setGeneratedContent(response.improved_text)
    },
  })

  const handleCommandSelect = useCallback((command: WriterCommand) => {
    setSelectedCommand(command)
    setOpen(false)
  }, [])

  const handleGenerate = useCallback(() => {
    if (selectedCommand) {
      executeCommand.mutate(selectedCommand)
    }
  }, [selectedCommand, executeCommand])

  const handleCopy = useCallback(async () => {
    await navigator.clipboard.writeText(generatedContent)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }, [generatedContent])

  const handleImprove = useCallback((instruction: string) => {
    improveContent.mutate(instruction)
  }, [improveContent])

  // Focus textarea when command is selected
  useEffect(() => {
    if (selectedCommand && textareaRef.current) {
      textareaRef.current.focus()
    }
  }, [selectedCommand])

  const getIcon = (commandName: string) => {
    const Icon = COMMAND_ICONS[commandName] || Wand2
    return <Icon className="h-4 w-4" />
  }

  return (
    <Card className={cn("w-full", className)}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Wand2 className="h-5 w-5 text-primary" />
            <CardTitle className="text-lg">AI Writer</CardTitle>
          </div>
          <Badge variant="outline" className="text-xs">
            GovGPT Style
          </Badge>
        </div>
        <CardDescription>
          Use slash commands to generate proposal sections for {rfpTitle}
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Command Selector */}
        <div className="space-y-2">
          <Label>Select Command</Label>
          <Popover open={open} onOpenChange={setOpen}>
            <PopoverTrigger asChild>
              <Button
                variant="outline"
                role="combobox"
                aria-expanded={open}
                className="w-full justify-between"
              >
                {selectedCommand ? (
                  <div className="flex items-center gap-2">
                    {getIcon(selectedCommand.command)}
                    <span>{selectedCommand.shortcut}</span>
                    <span className="text-muted-foreground">- {selectedCommand.name}</span>
                  </div>
                ) : (
                  <span className="text-muted-foreground">Type / to search commands...</span>
                )}
                <ChevronDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-[400px] p-0" align="start">
              <Command>
                <CommandInput placeholder="Search commands..." />
                <CommandList>
                  <CommandEmpty>No command found.</CommandEmpty>
                  <CommandGroup heading="Proposal Sections">
                    {commands?.commands.map((cmd) => (
                      <CommandItem
                        key={cmd.command}
                        value={cmd.command}
                        onSelect={() => handleCommandSelect(cmd)}
                        className="cursor-pointer"
                      >
                        <div className="flex items-center gap-2 flex-1">
                          {getIcon(cmd.command)}
                          <div className="flex flex-col">
                            <span className="font-medium">{cmd.shortcut}</span>
                            <span className="text-xs text-muted-foreground">
                              {cmd.description}
                            </span>
                          </div>
                        </div>
                        <Badge variant="secondary" className="text-xs">
                          ~{cmd.default_max_words} words
                        </Badge>
                      </CommandItem>
                    ))}
                  </CommandGroup>
                </CommandList>
              </Command>
            </PopoverContent>
          </Popover>
        </div>

        {/* Context and Options */}
        {selectedCommand && (
          <>
            <div className="space-y-2">
              <Label htmlFor="context">Additional Context (optional)</Label>
              <Textarea
                ref={textareaRef}
                id="context"
                placeholder="Add specific requirements, focus areas, or guidance for this section..."
                value={context}
                onChange={(e) => setContext(e.target.value)}
                className="min-h-[80px] resize-none"
              />
            </div>

            <div className="flex gap-4">
              <div className="flex-1 space-y-2">
                <Label htmlFor="tone">Writing Tone</Label>
                <Select value={tone} onValueChange={setTone}>
                  <SelectTrigger id="tone">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="professional">Professional</SelectItem>
                    <SelectItem value="formal">Formal</SelectItem>
                    <SelectItem value="conversational">Conversational</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <Button
              onClick={handleGenerate}
              disabled={executeCommand.isPending}
              className="w-full"
            >
              {executeCommand.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Generating {selectedCommand.name}...
                </>
              ) : (
                <>
                  <Sparkles className="mr-2 h-4 w-4" />
                  Generate {selectedCommand.name}
                </>
              )}
            </Button>
          </>
        )}

        {/* Generated Content */}
        {generatedContent && (
          <div className="space-y-3 mt-4 pt-4 border-t">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Label>Generated Content</Label>
                {executeCommand.data && (
                  <Badge variant="outline" className="text-xs">
                    {executeCommand.data.word_count} words
                  </Badge>
                )}
                {executeCommand.data && (
                  <Badge
                    variant={executeCommand.data.confidence_score >= 0.8 ? "default" : "secondary"}
                    className="text-xs"
                  >
                    {Math.round(executeCommand.data.confidence_score * 100)}% confident
                  </Badge>
                )}
              </div>
              <div className="flex items-center gap-1">
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  onClick={() => setIsExpanded(!isExpanded)}
                >
                  {isExpanded ? (
                    <Shrink className="h-4 w-4" />
                  ) : (
                    <Expand className="h-4 w-4" />
                  )}
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  onClick={handleCopy}
                >
                  {copied ? (
                    <Check className="h-4 w-4 text-green-500" />
                  ) : (
                    <Copy className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </div>

            <div
              className={cn(
                "rounded-md border bg-muted/50 p-3 text-sm whitespace-pre-wrap overflow-auto",
                isExpanded ? "max-h-[500px]" : "max-h-[200px]"
              )}
            >
              {generatedContent}
            </div>

            {/* Quick Improve Actions */}
            <div className="flex flex-wrap gap-2">
              <span className="text-xs text-muted-foreground self-center">Quick improve:</span>
              <Button
                variant="outline"
                size="sm"
                className="text-xs h-7"
                onClick={() => handleImprove("Make it more persuasive")}
                disabled={improveContent.isPending}
              >
                More Persuasive
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="text-xs h-7"
                onClick={() => handleImprove("Add specific metrics and numbers")}
                disabled={improveContent.isPending}
              >
                Add Metrics
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="text-xs h-7"
                onClick={() => handleImprove("Strengthen compliance language")}
                disabled={improveContent.isPending}
              >
                Add Compliance
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="text-xs h-7"
                onClick={() => handleImprove("Make it more concise")}
                disabled={improveContent.isPending}
              >
                More Concise
              </Button>
              {improveContent.isPending && (
                <Loader2 className="h-4 w-4 animate-spin self-center" />
              )}
            </div>

            {/* Suggestions */}
            {executeCommand.data?.suggestions && executeCommand.data.suggestions.length > 0 && (
              <div className="pt-2">
                <p className="text-xs text-muted-foreground mb-2">Suggestions:</p>
                <div className="flex flex-wrap gap-1">
                  {executeCommand.data.suggestions.map((suggestion, idx) => (
                    <Badge key={idx} variant="secondary" className="text-xs">
                      {suggestion}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default AIWriterMenu
