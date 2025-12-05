import { useState, useCallback, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft,
  Save,
  Sparkles,
  MessageSquare,
  FileText,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  RotateCcw,
  Copy,
  Check,
  Wand2,
  ListChecks,
  Target,
  Clock,
} from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Textarea } from '@/components/ui/textarea'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from '@/components/ui/resizable'
import { Progress } from '@/components/ui/progress'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

// Model options for AI generation
const MODEL_OPTIONS = [
  { id: 'haiku', name: 'Claude Haiku', description: 'Fast & economical' },
  { id: 'sonnet', name: 'Claude Sonnet', description: 'Balanced quality' },
  { id: 'opus', name: 'Claude Opus', description: 'Highest quality' },
] as const

type ModelId = typeof MODEL_OPTIONS[number]['id']
import { api } from '@/services/api'
import { CopilotChat } from '@/components/CopilotChat'
import { StreamingText } from '@/components/ui/streaming-text'
import { useStreaming } from '@/hooks/useStreaming'
import { useCommandStreaming } from '@/hooks/useCommandStreaming'
import { useSlashCommands } from '@/hooks/useSlashCommands'
import { SlashCommandPalette } from '@/components/SlashCommandPalette'
import type { SlashCommandDef, CommandExecutionResult } from '@/types/copilot'

// Proposal section definitions
const PROPOSAL_SECTIONS = [
  { id: 'executive_summary', name: 'Executive Summary', required: true },
  { id: 'technical_approach', name: 'Technical Approach', required: true },
  { id: 'company_qualifications', name: 'Company Qualifications', required: true },
  { id: 'management_approach', name: 'Management Approach', required: true },
  { id: 'pricing_narrative', name: 'Pricing Narrative', required: true },
  { id: 'past_performance', name: 'Past Performance', required: true },
  { id: 'staffing_plan', name: 'Staffing Plan', required: false },
  { id: 'quality_assurance', name: 'Quality Assurance', required: false },
  { id: 'risk_mitigation', name: 'Risk Mitigation', required: false },
  { id: 'compliance_matrix', name: 'Compliance Matrix', required: true },
] as const

type SectionId = typeof PROPOSAL_SECTIONS[number]['id']

interface SectionContent {
  id: SectionId
  content: string
  lastSaved?: Date
  aiGenerated?: boolean
  complianceScore?: number
  wordCount: number
}

interface ComplianceIssue {
  severity: 'error' | 'warning' | 'info'
  message: string
  section?: SectionId
  requirement?: string
}

export default function ProposalCopilot() {
  const { rfpId } = useParams<{ rfpId: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  // State
  const [activeSection, setActiveSection] = useState<SectionId>('executive_summary')
  const [sections, setSections] = useState<Record<SectionId, SectionContent>>(() =>
    PROPOSAL_SECTIONS.reduce((acc, section) => ({
      ...acc,
      [section.id]: {
        id: section.id,
        content: '',
        wordCount: 0,
      },
    }), {} as Record<SectionId, SectionContent>)
  )
  const [chatOpen, setChatOpen] = useState(true)
  const [copied, setCopied] = useState(false)
  const [complianceIssues, setComplianceIssues] = useState<ComplianceIssue[]>([])
  const [overallScore, setOverallScore] = useState(0)
  const [isDirty, setIsDirty] = useState(false)
  const [selectedModel, setSelectedModel] = useState<ModelId>('sonnet')

  // Fetch RFP data
  const { data: rfp, isLoading: rfpLoading, isFetching: rfpFetching, error: rfpError } = useQuery({
    queryKey: ['rfp', rfpId],
    queryFn: () => api.getRFP(rfpId!),
    enabled: !!rfpId,
  })

  // Show loading if rfpId is missing or query is loading/fetching
  const isInitializing = !rfpId || rfpLoading || (rfpFetching && !rfp)

  // Fetch existing bid document if any
  const { data: existingBid } = useQuery({
    queryKey: ['bid-document', rfpId],
    queryFn: () => api.getBidDocument(rfpId!),
    enabled: !!rfpId,
    retry: false,
  })

  // Load existing bid content into sections
  useEffect(() => {
    if (existingBid?.content_json?.sections) {
      // Initialize from PROPOSAL_SECTIONS to avoid stale closure on sections
      const loadedSections = PROPOSAL_SECTIONS.reduce((acc, section) => ({
        ...acc,
        [section.id]: {
          id: section.id,
          content: '',
          wordCount: 0,
        },
      }), {} as Record<SectionId, SectionContent>)

      Object.entries(existingBid.content_json.sections).forEach(([key, value]) => {
        if (key in loadedSections) {
          const sectionId = key as SectionId
          const content = typeof value === 'string' ? value : ''
          loadedSections[sectionId] = {
            ...loadedSections[sectionId],
            content,
            wordCount: content.split(/\s+/).filter(Boolean).length,
            lastSaved: existingBid.updated_at ? new Date(existingBid.updated_at) : undefined,
          }
        }
      })
      setSections(loadedSections)
    }
  }, [existingBid])

  // Streaming for section generation
  const sectionStreaming = useStreaming({
    url: `/api/v1/streaming/${rfpId}/generate/${activeSection}?model=${selectedModel}`,
    onComplete: (content) => {
      setSections((prev) => ({
        ...prev,
        [activeSection]: {
          ...prev[activeSection],
          content,
          aiGenerated: true,
          wordCount: content.split(/\s+/).filter(Boolean).length,
        },
      }))
      setIsDirty(true)
      toast.success(`${PROPOSAL_SECTIONS.find(s => s.id === activeSection)?.name} generated`)
    },
    onError: (error) => {
      toast.error('Generation failed', { description: error })
    },
  })

  // Slash commands state for command result tracking
  const [pendingCommandResult, setPendingCommandResult] = useState<CommandExecutionResult | null>(null)

  // Streaming for slash command generation (uses POST with JSON body)
  const commandStreaming = useCommandStreaming({
    url: rfpId ? api.getCommandStreamUrl(rfpId) : '',
    onComplete: (result) => {
      // Insert result at appropriate position
      if (pendingCommandResult) {
        const { slashStartIndex, selectedText } = pendingCommandResult
        const sectionContent = sections[activeSection].content

        if (selectedText) {
          // Replace selected text - find it in the content
          const selectionIndex = sectionContent.indexOf(selectedText)
          if (selectionIndex !== -1) {
            const before = sectionContent.slice(0, selectionIndex)
            const after = sectionContent.slice(selectionIndex + selectedText.length)
            handleContentChange(before + result + after)
          } else {
            // Fallback: append result
            handleContentChange(sectionContent + '\n\n' + result)
          }
        } else if (slashStartIndex !== null) {
          // Remove the slash command text and insert result
          const before = sectionContent.slice(0, slashStartIndex)
          handleContentChange(before + result)
        } else {
          // Append result
          handleContentChange(sectionContent + '\n\n' + result)
        }
        setPendingCommandResult(null)
      }
      toast.success('Command completed')
    },
    onError: (error) => {
      toast.error('Command failed', { description: error })
      setPendingCommandResult(null)
    },
  })

  // Save mutation
  const saveMutation = useMutation({
    mutationFn: async () => {
      const sectionData = Object.entries(sections).reduce((acc, [key, val]) => ({
        ...acc,
        [key]: val.content,
      }), {})
      return api.saveBidDraft(rfpId!, { sections: sectionData })
    },
    onSuccess: () => {
      setIsDirty(false)
      toast.success('Draft saved')
      queryClient.invalidateQueries({ queryKey: ['bid-document', rfpId] })
    },
    onError: (error: Error) => {
      toast.error('Save failed', { description: error.message })
    },
  })

  // Check compliance mutation
  const complianceMutation = useMutation({
    mutationFn: () => api.checkCompliance(rfpId!, sections),
    onSuccess: (data) => {
      setComplianceIssues(data.issues || [])
      setOverallScore(data.score || 0)
      // Update section scores
      if (data.section_scores) {
        setSections((prev) => {
          const updated = { ...prev }
          Object.entries(data.section_scores).forEach(([key, score]) => {
            if (key in updated) {
              updated[key as SectionId] = {
                ...updated[key as SectionId],
                complianceScore: score as number,
              }
            }
          })
          return updated
        })
      }
    },
    onError: (error: Error) => {
      toast.error('Compliance check failed', { description: error.message })
    },
  })

  // Handle section content change
  const handleContentChange = useCallback((content: string) => {
    setSections((prev) => ({
      ...prev,
      [activeSection]: {
        ...prev[activeSection],
        content,
        wordCount: content.split(/\s+/).filter(Boolean).length,
      },
    }))
    setIsDirty(true)
  }, [activeSection])

  // Slash commands hook
  const slashCommands = useSlashCommands({
    rfpId: rfpId || '',
    sectionId: activeSection,
    content: sections[activeSection]?.content || '',
    onContentChange: handleContentChange,
  })

  // Handle command selection
  const handleCommandSelect = useCallback(async (command: SlashCommandDef) => {
    const result = await slashCommands.executeCommand(command)

    if (result && command.isStreaming) {
      // Store the result for when streaming completes
      setPendingCommandResult(result)

      // Execute streaming command via POST
      commandStreaming.reset()
      await commandStreaming.startStreaming({
        command: command.id,
        selected_text: result.selectedText,
        context: result.context,
        section_id: activeSection,
      })
    }
  }, [slashCommands, activeSection, commandStreaming])

  // Generate section with AI
  const generateSection = useCallback(async () => {
    sectionStreaming.reset()
    await sectionStreaming.startStreaming({ use_thinking: true })
  }, [sectionStreaming])

  // Copy all content
  const copyAllContent = async () => {
    const fullContent = PROPOSAL_SECTIONS.map((section) => {
      const content = sections[section.id].content
      return content ? `## ${section.name}\n\n${content}` : ''
    })
      .filter(Boolean)
      .join('\n\n---\n\n')

    try {
      await navigator.clipboard.writeText(fullContent)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
      toast.success('Copied to clipboard')
    } catch (err) {
      console.error('Failed to copy to clipboard:', err)
      toast.error('Failed to copy to clipboard')
    }
  }

  // Calculate total word count
  const totalWordCount = Object.values(sections).reduce((sum, s) => sum + s.wordCount, 0)

  // Calculate completion percentage
  const completedSections = PROPOSAL_SECTIONS.filter(
    (s) => sections[s.id].content.length > 100
  ).length
  const completionPercentage = Math.round((completedSections / PROPOSAL_SECTIONS.length) * 100)

  // Loading state - show skeleton while initializing or loading data
  if (isInitializing) {
    return (
      <div className="h-screen flex flex-col">
        <div className="border-b p-4">
          <Skeleton className="h-8 w-64" />
        </div>
        <div className="flex-1 flex">
          <Skeleton className="w-64 h-full" />
          <Skeleton className="flex-1 h-full" />
        </div>
      </div>
    )
  }

  // Error state
  if (rfpError || !rfp) {
    return (
      <div className="flex flex-col items-center justify-center h-screen">
        <AlertTriangle className="h-12 w-12 text-red-500 mb-4" />
        <h2 className="text-xl font-semibold mb-2">RFP Not Found</h2>
        <Button onClick={() => navigate('/discovery')}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Discovery
        </Button>
      </div>
    )
  }

  const currentSection = PROPOSAL_SECTIONS.find((s) => s.id === activeSection)!
  const currentContent = sections[activeSection]

  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <header className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="sm" onClick={() => navigate(`/rfps/${rfpId}`)}>
              <ArrowLeft className="h-4 w-4" />
            </Button>
            <div>
              <h1 className="text-lg font-semibold line-clamp-1">{rfp.title}</h1>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <span>Proposal Copilot</span>
                {isDirty && (
                  <Badge variant="outline" className="text-orange-500 border-orange-500">
                    Unsaved
                  </Badge>
                )}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Progress indicator */}
            <div className="flex items-center gap-2 mr-4 px-3 py-1 rounded-md bg-muted">
              <Progress value={completionPercentage} className="w-24 h-2" />
              <span className="text-sm text-muted-foreground">
                {completedSections}/{PROPOSAL_SECTIONS.length} sections • {totalWordCount.toLocaleString()} words
              </span>
            </div>

            {/* Compliance Score */}
            {overallScore > 0 && (
              <Badge
                variant={overallScore >= 80 ? 'default' : overallScore >= 60 ? 'secondary' : 'destructive'}
                className="gap-1"
              >
                <Target className="h-3 w-3" />
                {overallScore}% Compliant
              </Badge>
            )}

            <Button
              variant="outline"
              size="sm"
              onClick={() => complianceMutation.mutate()}
              disabled={complianceMutation.isPending}
            >
              {complianceMutation.isPending ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <ListChecks className="h-4 w-4 mr-2" />
              )}
              Check Compliance
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={copyAllContent}
            >
              {copied ? <Check className="h-4 w-4 mr-2" /> : <Copy className="h-4 w-4 mr-2" />}
              {copied ? 'Copied!' : 'Copy All'}
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={() => saveMutation.mutate()}
              disabled={saveMutation.isPending || !isDirty}
            >
              {saveMutation.isPending ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Save className="h-4 w-4 mr-2" />
              )}
              Save Draft
            </Button>

            <Button
              size="sm"
              onClick={() => setChatOpen(!chatOpen)}
              variant={chatOpen ? 'default' : 'outline'}
            >
              <MessageSquare className="h-4 w-4 mr-2" />
              AI Chat
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 overflow-hidden">
        <ResizablePanelGroup direction="horizontal">
          {/* Section Navigation Sidebar */}
          <ResizablePanel defaultSize={15} minSize={12} maxSize={20}>
            <ScrollArea className="h-full border-r">
              <div className="p-4 space-y-1">
                <h3 className="text-sm font-medium mb-3 text-muted-foreground">Sections</h3>
                {PROPOSAL_SECTIONS.map((section) => {
                  const sectionContent = sections[section.id]
                  const isComplete = sectionContent.content.length > 100
                  const score = sectionContent.complianceScore

                  return (
                    <button
                      type="button"
                      key={section.id}
                      onClick={() => setActiveSection(section.id)}
                      className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors ${
                        activeSection === section.id
                          ? 'bg-primary text-primary-foreground'
                          : 'hover:bg-muted'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="line-clamp-1">{section.name}</span>
                        <div className="flex items-center gap-1">
                          {section.required && !isComplete && (
                            <span className="h-2 w-2 rounded-full bg-orange-500" title="Required" />
                          )}
                          {isComplete && (
                            <CheckCircle2 className="h-3 w-3 text-green-500" />
                          )}
                        </div>
                      </div>
                      {score !== undefined && (
                        <div className="mt-1">
                          <Progress
                            value={score}
                            className={`h-1 ${
                              score >= 80
                                ? '[&>div]:bg-green-500'
                                : score >= 60
                                ? '[&>div]:bg-yellow-500'
                                : '[&>div]:bg-red-500'
                            }`}
                          />
                        </div>
                      )}
                    </button>
                  )
                })}
              </div>
            </ScrollArea>
          </ResizablePanel>

          <ResizableHandle withHandle />

          {/* Editor Panel */}
          <ResizablePanel defaultSize={chatOpen ? 50 : 85}>
            <div className="h-full flex flex-col">
              {/* Editor Header */}
              <div className="border-b px-4 py-3 flex items-center justify-between bg-muted/30">
                <div className="flex items-center gap-3">
                  <FileText className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <h2 className="font-medium">{currentSection.name}</h2>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <span>{currentContent.wordCount} words</span>
                      {currentContent.lastSaved && (
                        <>
                          <span>•</span>
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            Saved {currentContent.lastSaved.toLocaleTimeString()}
                          </span>
                        </>
                      )}
                      {currentContent.aiGenerated && (
                        <>
                          <span>•</span>
                          <Badge variant="secondary" className="text-xs py-0">
                            <Sparkles className="h-3 w-3 mr-1" />
                            AI Generated
                          </Badge>
                        </>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setSections((prev) => ({
                        ...prev,
                        [activeSection]: { ...prev[activeSection], content: '', wordCount: 0 },
                      }))
                      setIsDirty(true)
                    }}
                    disabled={!currentContent.content}
                  >
                    <RotateCcw className="h-4 w-4 mr-2" />
                    Clear
                  </Button>
                  {/* Model Selector */}
                  <Select value={selectedModel} onValueChange={(value) => setSelectedModel(value as ModelId)}>
                    <SelectTrigger className="w-[160px] h-9">
                      <SelectValue placeholder="Select model" />
                    </SelectTrigger>
                    <SelectContent>
                      {MODEL_OPTIONS.map((model) => (
                        <SelectItem key={model.id} value={model.id}>
                          <div className="flex flex-col">
                            <span>{model.name}</span>
                            <span className="text-xs text-muted-foreground">{model.description}</span>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Button
                    size="sm"
                    onClick={generateSection}
                    disabled={sectionStreaming.isStreaming}
                    className="bg-purple-600 hover:bg-purple-700"
                  >
                    {sectionStreaming.isStreaming ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <Wand2 className="h-4 w-4 mr-2" />
                    )}
                    Generate with AI
                  </Button>
                </div>
              </div>

              {/* Editor Area */}
              <div className="flex-1 p-4 overflow-hidden relative">
                {sectionStreaming.isStreaming || commandStreaming.isStreaming ? (
                  <div className="h-full bg-muted/30 rounded-lg p-4 overflow-auto">
                    <StreamingText
                      content={sectionStreaming.isStreaming ? sectionStreaming.content : commandStreaming.content}
                      isStreaming={true}
                      className="prose dark:prose-invert max-w-none"
                    />
                  </div>
                ) : (
                  <>
                    <Textarea
                      ref={slashCommands.textareaRef}
                      value={currentContent.content}
                      onChange={(e) => {
                        handleContentChange(e.target.value)
                        slashCommands.handleInput(e)
                      }}
                      onKeyDown={slashCommands.handleKeyDown}
                      placeholder={`Write your ${currentSection.name.toLowerCase()} here...\n\nTip: Type "/" for AI commands, or click "Generate with AI" to auto-generate content.`}
                      className="h-full resize-none font-mono text-sm"
                    />

                    <SlashCommandPalette
                      isOpen={slashCommands.isOpen}
                      position={slashCommands.position}
                      searchQuery={slashCommands.searchQuery}
                      onSearchChange={slashCommands.setSearchQuery}
                      groupedCommands={slashCommands.groupedCommands}
                      onSelect={handleCommandSelect}
                      isExecuting={slashCommands.isExecuting || commandStreaming.isStreaming}
                      hasSelection={!!slashCommands.selection?.text}
                    />
                  </>
                )}
              </div>

              {/* Compliance Issues for this section */}
              {complianceIssues.filter((i) => i.section === activeSection).length > 0 && (
                <div className="border-t p-4 bg-muted/30">
                  <h4 className="text-sm font-medium mb-2">Compliance Issues</h4>
                  <div className="space-y-2">
                    {complianceIssues
                      .filter((i) => i.section === activeSection)
                      .map((issue, idx) => (
                        <div
                          key={idx}
                          className={`flex items-start gap-2 text-sm p-2 rounded ${
                            issue.severity === 'error'
                              ? 'bg-red-100 dark:bg-red-950 text-red-700 dark:text-red-300'
                              : issue.severity === 'warning'
                              ? 'bg-orange-100 dark:bg-orange-950 text-orange-700 dark:text-orange-300'
                              : 'bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-300'
                          }`}
                        >
                          <AlertTriangle className="h-4 w-4 mt-0.5 flex-shrink-0" />
                          <span>{issue.message}</span>
                        </div>
                      ))}
                  </div>
                </div>
              )}
            </div>
          </ResizablePanel>

          {/* Chat Panel */}
          {chatOpen && (
            <>
              <ResizableHandle withHandle />
              <ResizablePanel defaultSize={35} minSize={25} maxSize={50}>
                <CopilotChat
                  rfpId={rfpId!}
                  currentSection={activeSection}
                  currentContent={currentContent.content}
                  onInsertText={(text) => {
                    handleContentChange(currentContent.content + '\n\n' + text)
                    toast.success('Text inserted')
                  }}
                  onReplaceSection={(text) => {
                    handleContentChange(text)
                    toast.success('Section replaced')
                  }}
                />
              </ResizablePanel>
            </>
          )}
        </ResizablePanelGroup>
      </div>
    </div>
  )
}
