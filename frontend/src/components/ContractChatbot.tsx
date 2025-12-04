import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { format } from 'date-fns'
import {
  Bot,
  Check,
  Copy,
  Download,
  History,
  Loader2,
  MessageSquare,
  Plus,
  Send,
  Sparkles,
  Trash2,
  X,
} from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { api, apiClient } from '@/services/api'

interface Citation {
  document_id: string
  content_snippet: string
  source: string
  similarity_score: number
}

interface ChatMessageType {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  citations?: Citation[]
  confidence?: number
}

interface ChatSession {
  session_id: string
  rfp_id: string
  title: string | null
  message_count: number
  created_at: string
  last_message_at: string | null
}

interface ContractChatbotProps {
  rfpId: string
  rfpTitle: string
  isOpen: boolean
  onClose: () => void
}

export function ContractChatbot({ rfpId, rfpTitle, isOpen, onClose }: ContractChatbotProps) {
  const queryClient = useQueryClient()

  // State
  const [message, setMessage] = useState('')
  const [messages, setMessages] = useState<ChatMessageType[]>([])
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamingContent, setStreamingContent] = useState('')
  const [streamingStatus, setStreamingStatus] = useState<string | null>(null)
  const [copied, setCopied] = useState<string | null>(null)
  const [showSessions, setShowSessions] = useState(false)

  // Refs
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  // Fetch chat sessions
  const { data: sessionsData } = useQuery({
    queryKey: ['chat-sessions', rfpId],
    queryFn: () => api.listChatSessions(rfpId),
    enabled: isOpen,
  })

  // Fetch suggestions
  const { data: suggestionsData } = useQuery({
    queryKey: ['chat-suggestions', rfpId],
    queryFn: () => api.getChatSuggestions(rfpId),
    enabled: isOpen && messages.length === 0,
  })

  // Fetch chat status
  const { data: chatStatus } = useQuery({
    queryKey: ['chat-status', rfpId],
    queryFn: () => api.getChatStatus(rfpId),
    enabled: isOpen,
  })

  // Create session mutation
  const createSessionMutation = useMutation({
    mutationFn: () => api.createChatSession(rfpId),
    onSuccess: (data) => {
      setCurrentSessionId(data.session_id)
      setMessages([])
      queryClient.invalidateQueries({ queryKey: ['chat-sessions', rfpId] })
      toast.success('New conversation started')
    },
  })

  // Delete session mutation
  const deleteSessionMutation = useMutation({
    mutationFn: (sessionId: string) => api.deleteChatSession(rfpId, sessionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chat-sessions', rfpId] })
      if (currentSessionId) {
        setCurrentSessionId(null)
        setMessages([])
      }
      toast.success('Conversation deleted')
    },
  })

  // Load session
  const loadSession = useCallback(async (sessionId: string) => {
    try {
      const session = await api.getChatSession(rfpId, sessionId)
      setCurrentSessionId(sessionId)
      setMessages(
        session.messages.map((m: any) => ({
          id: m.id.toString(),
          role: m.role,
          content: m.content,
          timestamp: m.created_at,
          citations: m.citations,
          confidence: m.confidence,
        }))
      )
      setShowSessions(false)
    } catch (error) {
      toast.error('Failed to load conversation')
    }
  }, [rfpId])

  // Send message with streaming
  const sendMessage = useCallback(async () => {
    if (!message.trim() || isStreaming) return

    const userMessage: ChatMessageType = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: message.trim(),
      timestamp: new Date().toISOString(),
    }

    setMessages((prev) => [...prev, userMessage])
    setMessage('')
    setIsStreaming(true)
    setStreamingContent('')
    setStreamingStatus(null)

    // Abort any existing stream
    abortControllerRef.current?.abort()
    abortControllerRef.current = new AbortController()

    try {
      const response = await fetch(
        `${apiClient.defaults.baseURL}/rfps/${rfpId}/chat/stream`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            message: userMessage.content,
            session_id: currentSessionId,
          }),
          signal: abortControllerRef.current.signal,
        }
      )

      if (!response.ok) {
        throw new Error('Stream request failed')
      }

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      let fullContent = ''
      let citations: Citation[] = []
      let confidence = 0

      if (reader) {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          const chunk = decoder.decode(value)
          const lines = chunk.split('\n')

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6))

                if (data.type === 'status') {
                  setStreamingStatus(data.content)
                } else if (data.type === 'content') {
                  fullContent += data.content
                  setStreamingContent(fullContent)
                  setStreamingStatus(null)
                } else if (data.type === 'done') {
                  citations = data.citations || []
                  confidence = data.confidence || 0
                } else if (data.type === 'error') {
                  throw new Error(data.content)
                }
              } catch (e) {
                if (!(e instanceof SyntaxError)) {
                  console.error('Unexpected error processing SSE:', e)
                }
                // Ignore JSON parse errors for incomplete chunks
              }
            }
          }
        }
      }

      // Add assistant message
      const assistantMessage: ChatMessageType = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: fullContent,
        timestamp: new Date().toISOString(),
        citations,
        confidence,
      }

      setMessages((prev) => [...prev, assistantMessage])
      setStreamingContent('')

    } catch (error: any) {
      if (error.name !== 'AbortError') {
        toast.error('Failed to get response')
        // Remove user message on error
        setMessages((prev) => prev.slice(0, -1))
      }
    } finally {
      setIsStreaming(false)
      setStreamingStatus(null)
    }
  }, [message, isStreaming, rfpId, currentSessionId])

  // Handle keyboard submit
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  // Copy message to clipboard
  const copyToClipboard = async (content: string, messageId: string) => {
    try {
      await navigator.clipboard.writeText(content)
      setCopied(messageId)
      setTimeout(() => setCopied(null), 2000)
    } catch {
      toast.error('Failed to copy')
    }
  }

  // Export conversation to markdown
  const exportConversation = () => {
    if (messages.length === 0) return

    const content = messages
      .map(msg => `**${msg.role === 'user' ? 'You' : 'AI'}:** ${msg.content}`)
      .join('\n\n---\n\n')

    const header = `# Chat Export: ${rfpTitle}\n\nExported: ${new Date().toLocaleString()}\n\n---\n\n`

    const blob = new Blob([header + content], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `chat-${rfpId}-${Date.now()}.md`
    a.click()
    URL.revokeObjectURL(url)
    toast.success('Conversation exported')
  }

  // Handle suggestion click
  const handleSuggestionClick = (suggestion: string) => {
    setMessage(suggestion)
    inputRef.current?.focus()
  }

  // Scroll to bottom when messages change
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
    }
  }, [messages, streamingContent])

  // Focus input when opened
  useEffect(() => {
    if (isOpen) {
      inputRef.current?.focus()
    }
  }, [isOpen])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort()
    }
  }, [])

  if (!isOpen) return null

  return (
    <Card className="fixed bottom-6 right-6 w-[420px] h-[600px] shadow-2xl border-2 z-50 flex flex-col">
      <CardHeader className="pb-2 border-b shrink-0">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Bot className="h-5 w-5 text-purple-500" />
            Contract Assistant
          </CardTitle>
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="sm"
              onClick={exportConversation}
              disabled={messages.length === 0}
              title="Export conversation"
            >
              <Download className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setShowSessions(!showSessions)}>
              <History className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="sm" onClick={onClose}>
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>
        <CardDescription className="text-xs truncate">
          Ask questions about: {rfpTitle}
        </CardDescription>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col p-0 overflow-hidden">
        {/* Session List Drawer */}
        {showSessions && (
          <div className="absolute inset-0 bg-background z-10 flex flex-col">
            <div className="p-4 border-b flex items-center justify-between">
              <h3 className="font-semibold">Conversations</h3>
              <Button variant="ghost" size="sm" onClick={() => setShowSessions(false)}>
                <X className="h-4 w-4" />
              </Button>
            </div>
            <ScrollArea className="flex-1">
              <div className="p-2 space-y-1">
                <Button
                  variant="outline"
                  className="w-full justify-start gap-2"
                  onClick={() => {
                    createSessionMutation.mutate()
                    setShowSessions(false)
                  }}
                >
                  <Plus className="h-4 w-4" />
                  New Conversation
                </Button>
                {sessionsData?.sessions?.map((session: ChatSession) => (
                  <div
                    key={session.session_id}
                    className={`flex items-center gap-2 p-2 rounded-lg cursor-pointer hover:bg-muted ${
                      currentSessionId === session.session_id ? 'bg-muted' : ''
                    }`}
                  >
                    <button
                      className="flex-1 text-left"
                      onClick={() => loadSession(session.session_id)}
                    >
                      <p className="text-sm font-medium truncate">{session.title || 'Untitled'}</p>
                      <p className="text-xs text-muted-foreground">
                        {session.message_count} messages
                        {session.last_message_at && (
                          <> · {format(new Date(session.last_message_at), 'MMM d')}</>
                        )}
                      </p>
                    </button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation()
                        deleteSessionMutation.mutate(session.session_id)
                      }}
                    >
                      <Trash2 className="h-3 w-3 text-muted-foreground" />
                    </Button>
                  </div>
                ))}
                {(!sessionsData?.sessions || sessionsData.sessions.length === 0) && (
                  <p className="text-sm text-muted-foreground text-center py-4">
                    No previous conversations
                  </p>
                )}
              </div>
            </ScrollArea>
          </div>
        )}

        {/* Messages Area */}
        <ScrollArea className="flex-1 px-4" ref={scrollRef}>
          {messages.length === 0 && !isStreaming ? (
            <div className="py-8 space-y-4">
              <div className="text-center">
                <Bot className="h-10 w-10 mx-auto mb-2 text-purple-500 opacity-50" />
                <p className="text-sm text-muted-foreground">
                  How can I help with this RFP?
                </p>
              </div>

              {/* Suggestions */}
              {suggestionsData?.suggestions && (
                <div className="space-y-2">
                  <p className="text-xs text-muted-foreground text-center">Try asking:</p>
                  <div className="space-y-1">
                    {suggestionsData.suggestions.slice(0, 5).map((suggestion: string, idx: number) => (
                      <button
                        key={idx}
                        type="button"
                        className="w-full text-left text-sm p-2 rounded-lg border border-dashed hover:bg-muted hover:border-purple-300 transition-colors"
                        onClick={() => handleSuggestionClick(suggestion)}
                      >
                        <MessageSquare className="h-3 w-3 inline mr-2 text-muted-foreground" />
                        {suggestion}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Chat Status Warning */}
              {chatStatus && !chatStatus.chat_available && (
                <div className="bg-yellow-50 dark:bg-yellow-950 border border-yellow-200 dark:border-yellow-800 rounded-lg p-3">
                  <p className="text-xs text-yellow-800 dark:text-yellow-200">
                    ⚠️ {chatStatus.message}
                  </p>
                </div>
              )}
            </div>
          ) : (
            <div className="py-4 space-y-4">
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex gap-2 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  {msg.role === 'assistant' && (
                    <Bot className="h-6 w-6 text-purple-500 shrink-0 mt-1" />
                  )}
                  <div
                    className={`max-w-[85%] group ${
                      msg.role === 'user'
                        ? 'bg-purple-500 text-white rounded-2xl rounded-br-sm px-4 py-2'
                        : 'bg-muted rounded-2xl rounded-bl-sm px-4 py-2'
                    }`}
                  >
                    {msg.role === 'assistant' ? (
                      <div className="prose prose-sm dark:prose-invert max-w-none">
                        <ReactMarkdown>{msg.content}</ReactMarkdown>
                      </div>
                    ) : (
                      <p className="text-sm">{msg.content}</p>
                    )}

                    {/* Citations */}
                    {msg.citations && msg.citations.length > 0 && (
                      <div className="mt-2 pt-2 border-t border-gray-200 dark:border-gray-700">
                        <p className="text-xs text-muted-foreground mb-1">Sources:</p>
                        {msg.citations.map((citation, idx) => (
                          <div key={idx} className="text-xs text-muted-foreground">
                            [{idx + 1}] {citation.source} ({Math.round(citation.similarity_score * 100)}% match)
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Copy button for assistant messages */}
                    {msg.role === 'assistant' && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="opacity-0 group-hover:opacity-100 transition-opacity mt-1 h-6 px-2"
                        onClick={() => copyToClipboard(msg.content, msg.id)}
                      >
                        {copied === msg.id ? (
                          <Check className="h-3 w-3" />
                        ) : (
                          <Copy className="h-3 w-3" />
                        )}
                      </Button>
                    )}
                  </div>
                </div>
              ))}

              {/* Streaming Message */}
              {isStreaming && (
                <div className="flex gap-2 justify-start">
                  <Bot className="h-6 w-6 text-purple-500 shrink-0 mt-1" />
                  <div className="bg-muted rounded-2xl rounded-bl-sm px-4 py-2 max-w-[85%]">
                    {streamingStatus ? (
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        {streamingStatus}
                      </div>
                    ) : streamingContent ? (
                      <div className="prose prose-sm dark:prose-invert max-w-none">
                        <ReactMarkdown>{streamingContent}</ReactMarkdown>
                      </div>
                    ) : (
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Sparkles className="h-4 w-4 animate-pulse" />
                        Thinking...
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </ScrollArea>

        {/* Input Area */}
        <div className="p-4 border-t shrink-0">
          <div className="flex gap-2">
            <Input
              ref={inputRef}
              placeholder="Ask about this RFP..."
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isStreaming || (chatStatus && !chatStatus.chat_available)}
              className="flex-1"
            />
            <Button
              onClick={sendMessage}
              disabled={!message.trim() || isStreaming || (chatStatus && !chatStatus.chat_available)}
              size="icon"
            >
              {isStreaming ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </div>
          {currentSessionId && (
            <p className="text-xs text-muted-foreground mt-1 text-center">
              Session active · Messages are saved
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
