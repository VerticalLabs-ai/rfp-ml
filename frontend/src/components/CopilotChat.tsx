import { useState, useRef, useEffect, useCallback } from 'react'
import {
  Send,
  Sparkles,
  Plus,
  Replace,
  Copy,
  Check,
  Loader2,
  StopCircle,
  Trash2,
  Lightbulb,
  FileText,
  ArrowRight,
} from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { StreamingText } from '@/components/ui/streaming-text'
import { useStreamingChat, ChatMessage } from '@/hooks/useStreamingChat'
import { cn } from '@/lib/utils'

interface CopilotChatProps {
  rfpId: string
  currentSection: string
  currentContent: string
  onInsertText: (text: string) => void
  onReplaceSection: (text: string) => void
}

const QUICK_PROMPTS = [
  { label: 'Improve', prompt: 'Improve the current section to be more compelling and professional' },
  { label: 'Expand', prompt: 'Expand on the current content with more detail and examples' },
  { label: 'Summarize', prompt: 'Create a concise summary of the key points' },
  { label: 'Requirements', prompt: 'What are the key requirements I should address in this section?' },
]

const SECTION_PROMPTS: Record<string, string[]> = {
  executive_summary: [
    'Write a compelling executive summary that highlights our key strengths',
    'What should be the main value proposition for this RFP?',
    'Summarize the key win themes for this opportunity',
  ],
  technical_approach: [
    'What technical capabilities should I emphasize?',
    'Suggest a methodology framework for this project',
    'What innovative solutions would differentiate our approach?',
  ],
  management_approach: [
    'Outline an effective project management structure',
    'What governance model would work best for this contract?',
    'How should I present our quality control processes?',
  ],
  past_performance: [
    'What past performance examples would be most relevant?',
    'How should I structure the past performance narratives?',
    'What metrics should I highlight from past projects?',
  ],
  compliance_matrix: [
    'Review the requirements and identify any compliance gaps',
    'What mandatory certifications should we highlight?',
    'Are there any requirements we might be missing?',
  ],
}

export function CopilotChat({
  rfpId,
  currentSection,
  currentContent,
  onInsertText,
  onReplaceSection,
}: CopilotChatProps) {
  const [input, setInput] = useState('')
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const {
    messages,
    sendMessage,
    stopStreaming,
    clearMessages,
    isStreaming,
    currentResponse,
    error,
  } = useStreamingChat({
    rfpId,
    onError: (err) => console.error('Chat error:', err),
  })

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (scrollRef.current) {
      // ScrollArea forwards ref to Root, not Viewport - query the viewport directly
      const viewport = scrollRef.current.querySelector('[data-radix-scroll-area-viewport]')
      if (viewport) {
        viewport.scrollTop = viewport.scrollHeight
      }
    }
  }, [messages, currentResponse])

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  // Handle send message
  const handleSend = useCallback(async () => {
    if (!input.trim() || isStreaming) return

    // Include current section context in the message
    const contextMessage = currentContent
      ? `[Context: Working on "${currentSection}" section]\n\nCurrent content preview:\n${currentContent.slice(0, 500)}${currentContent.length > 500 ? '...' : ''}\n\nUser question: ${input}`
      : `[Context: Working on "${currentSection}" section]\n\nUser question: ${input}`

    await sendMessage(contextMessage)
    setInput('')
  }, [input, isStreaming, sendMessage, currentSection, currentContent])

  // Handle keyboard shortcut
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // Copy message content
  const copyContent = async (messageId: string, content: string) => {
    try {
      await navigator.clipboard.writeText(content)
      setCopiedId(messageId)
      setTimeout(() => setCopiedId(null), 2000)
    } catch (err) {
      console.error('Failed to copy to clipboard:', err)
    }
  }

  // Get section-specific prompts
  const sectionPrompts = SECTION_PROMPTS[currentSection] || []

  return (
    <div className="h-full flex flex-col bg-background border-l">
      {/* Header */}
      <div className="p-4 border-b">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-purple-500" />
            <h3 className="font-semibold">AI Copilot</h3>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={clearMessages}
            disabled={messages.length === 0 || isStreaming}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          Ask questions about the RFP or get help writing your proposal
        </p>
      </div>

      {/* Messages */}
      <ScrollArea className="flex-1 p-4" ref={scrollRef}>
        {messages.length === 0 ? (
          <div className="space-y-4">
            {/* Welcome message */}
            <div className="text-center py-6">
              <Lightbulb className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
              <p className="text-sm text-muted-foreground">
                I can help you write and improve your proposal.
                <br />
                Ask me anything about the RFP or your current section.
              </p>
            </div>

            {/* Quick prompts */}
            <div className="space-y-2">
              <p className="text-xs font-medium text-muted-foreground">Quick actions:</p>
              <div className="flex flex-wrap gap-2">
                {QUICK_PROMPTS.map((prompt) => (
                  <Button
                    key={prompt.label}
                    variant="outline"
                    size="sm"
                    onClick={() => sendMessage(prompt.prompt)}
                    className="text-xs"
                  >
                    {prompt.label}
                  </Button>
                ))}
              </div>
            </div>

            {/* Section-specific suggestions */}
            {sectionPrompts.length > 0 && (
              <div className="space-y-2 mt-4">
                <p className="text-xs font-medium text-muted-foreground flex items-center gap-1">
                  <FileText className="h-3 w-3" />
                  For {currentSection.replace(/_/g, ' ')}:
                </p>
                <div className="space-y-1">
                  {sectionPrompts.map((prompt, idx) => (
                    <button
                      type="button"
                      key={idx}
                      onClick={() => sendMessage(prompt)}
                      className="w-full text-left text-xs p-2 rounded-md hover:bg-muted transition-colors flex items-center gap-2"
                    >
                      <ArrowRight className="h-3 w-3 text-muted-foreground flex-shrink-0" />
                      <span>{prompt}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((message) => (
              <MessageBubble
                key={message.id}
                message={message}
                currentResponse={message.isStreaming ? currentResponse : undefined}
                copiedId={copiedId}
                onCopy={copyContent}
                onInsert={onInsertText}
                onReplace={onReplaceSection}
              />
            ))}
            {error && (
              <div className="text-sm text-red-500 p-2 bg-red-50 dark:bg-red-950 rounded-md">
                Error: {error}
              </div>
            )}
          </div>
        )}
      </ScrollArea>

      <Separator />

      {/* Input */}
      <div className="p-4">
        <div className="flex items-center gap-2">
          <Input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about the RFP or request help..."
            disabled={isStreaming}
            className="flex-1"
          />
          {isStreaming ? (
            <Button
              variant="destructive"
              size="icon"
              onClick={stopStreaming}
            >
              <StopCircle className="h-4 w-4" />
            </Button>
          ) : (
            <Button
              size="icon"
              onClick={handleSend}
              disabled={!input.trim()}
            >
              <Send className="h-4 w-4" />
            </Button>
          )}
        </div>
        <p className="text-xs text-muted-foreground mt-2">
          Press Enter to send • Context from current section is included
        </p>
      </div>
    </div>
  )
}

interface MessageBubbleProps {
  message: ChatMessage
  currentResponse?: string
  copiedId: string | null
  onCopy: (id: string, content: string) => void
  onInsert: (text: string) => void
  onReplace: (text: string) => void
}

function MessageBubble({
  message,
  currentResponse,
  copiedId,
  onCopy,
  onInsert,
  onReplace,
}: MessageBubbleProps) {
  const isUser = message.role === 'user'
  const content = message.isStreaming ? currentResponse || '' : message.content

  // Clean user message (remove context prefix)
  const displayContent = isUser
    ? message.content.replace(/^\[Context:.*?\]\n\n.*?User question:\s*/s, '')
    : content

  return (
    <div className={cn('flex flex-col', isUser ? 'items-end' : 'items-start')}>
      <div
        className={cn(
          'max-w-[90%] rounded-lg px-3 py-2 text-sm',
          isUser
            ? 'bg-primary text-primary-foreground'
            : 'bg-muted'
        )}
      >
        {message.isStreaming ? (
          <StreamingText content={content} isStreaming={true} />
        ) : (
          <div className="whitespace-pre-wrap">{displayContent}</div>
        )}
      </div>

      {/* Actions for assistant messages */}
      {!isUser && !message.isStreaming && content && (
        <div className="flex items-center gap-1 mt-1">
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6"
                  onClick={() => onCopy(message.id, content)}
                >
                  {copiedId === message.id ? (
                    <Check className="h-3 w-3" />
                  ) : (
                    <Copy className="h-3 w-3" />
                  )}
                </Button>
              </TooltipTrigger>
              <TooltipContent>Copy</TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6"
                  onClick={() => onInsert(content)}
                >
                  <Plus className="h-3 w-3" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Insert at end</TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6"
                  onClick={() => onReplace(content)}
                >
                  <Replace className="h-3 w-3" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Replace section</TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      )}

      {/* Citations */}
      {message.citations && message.citations.length > 0 && (
        <div className="mt-2 space-y-1">
          {message.citations.map((citation, idx) => (
            <div
              key={idx}
              className="text-xs p-2 bg-blue-50 dark:bg-blue-950 rounded text-blue-700 dark:text-blue-300"
            >
              <span className="font-medium">[{citation.index}]</span>{' '}
              {citation.content.slice(0, 100)}...
            </div>
          ))}
        </div>
      )}

      {/* Streaming indicator */}
      {message.isStreaming && (
        <div className="flex items-center gap-1 mt-1 text-xs text-muted-foreground">
          <Loader2 className="h-3 w-3 animate-spin" />
          Generating...
        </div>
      )}
    </div>
  )
}
