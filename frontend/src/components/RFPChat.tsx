import { useState, useRef, useEffect } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { MessageCircle, Send, X, ChevronDown, ChevronUp, Loader2, ExternalLink, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp?: string
  citations?: Citation[]
  confidence?: number
}

interface Citation {
  document_id: string
  content_snippet: string
  source: string
  similarity_score: number
}

interface ChatResponse {
  answer: string
  citations: Citation[]
  confidence: number
  rfp_id: string
  processing_time_ms: number
}

interface RFPChatProps {
  rfpId: string
  rfpTitle: string
  className?: string
}

export function RFPChat({ rfpId, rfpTitle, className }: RFPChatProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [isMinimized, setIsMinimized] = useState(false)
  const [message, setMessage] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Fetch suggested questions
  const { data: suggestions } = useQuery({
    queryKey: ['chat', 'suggestions', rfpId],
    queryFn: () => api.get<{ suggestions: string[] }>(`/chat/${rfpId}/chat/suggestions`),
    enabled: isOpen && messages.length === 0,
  })

  // Check chat availability
  const { data: chatStatus } = useQuery({
    queryKey: ['chat', 'status', rfpId],
    queryFn: () => api.get<{ chat_available: boolean; message: string }>(`/chat/${rfpId}/chat/status`),
    enabled: isOpen,
  })

  // Send message mutation
  const sendMessage = useMutation({
    mutationFn: async (userMessage: string) => {
      const history = messages.map(m => ({
        role: m.role,
        content: m.content,
        timestamp: m.timestamp || new Date().toISOString()
      }))

      return api.post<ChatResponse>(`/chat/${rfpId}/chat`, {
        message: userMessage,
        history: history.slice(-10) // Last 10 messages
      })
    },
    onSuccess: (response) => {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: response.answer,
        timestamp: new Date().toISOString(),
        citations: response.citations,
        confidence: response.confidence
      }])
    },
    onError: (error: Error) => {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Sorry, I encountered an error: ${error.message}. Please try again.`,
        timestamp: new Date().toISOString()
      }])
    }
  })

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Focus textarea when chat opens
  useEffect(() => {
    if (isOpen && !isMinimized) {
      textareaRef.current?.focus()
    }
  }, [isOpen, isMinimized])

  const handleSend = () => {
    if (!message.trim() || sendMessage.isPending) return

    const userMessage = message.trim()
    setMessages(prev => [...prev, {
      role: 'user',
      content: userMessage,
      timestamp: new Date().toISOString()
    }])
    setMessage('')
    sendMessage.mutate(userMessage)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleSuggestionClick = (suggestion: string) => {
    setMessage(suggestion)
    textareaRef.current?.focus()
  }

  if (!isOpen) {
    return (
      <Button
        onClick={() => setIsOpen(true)}
        className={cn("fixed bottom-4 right-4 rounded-full h-14 w-14 shadow-lg", className)}
        size="icon"
      >
        <MessageCircle className="h-6 w-6" />
      </Button>
    )
  }

  return (
    <Card className={cn(
      "fixed bottom-4 right-4 w-96 shadow-xl transition-all duration-200",
      isMinimized ? "h-14" : "h-[500px]",
      className
    )}>
      <CardHeader className="p-3 border-b flex flex-row items-center justify-between space-y-0">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-primary" />
          <CardTitle className="text-sm font-medium truncate max-w-[200px]">
            Ask about {rfpTitle}
          </CardTitle>
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={() => setIsMinimized(!isMinimized)}
          >
            {isMinimized ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={() => setIsOpen(false)}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>

      {!isMinimized && (
        <CardContent className="p-0 flex flex-col h-[calc(100%-3.5rem)]">
          {/* Chat availability warning */}
          {chatStatus && !chatStatus.chat_available && (
            <div className="px-3 py-2 bg-yellow-50 border-b text-xs text-yellow-700">
              {chatStatus.message}
            </div>
          )}

          {/* Messages area */}
          <div className="flex-1 overflow-y-auto p-3 space-y-3">
            {messages.length === 0 && (
              <div className="text-center py-4">
                <MessageCircle className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
                <p className="text-sm text-muted-foreground mb-4">
                  Ask me anything about this RFP
                </p>

                {/* Suggested questions */}
                {suggestions?.suggestions && suggestions.suggestions.length > 0 && (
                  <div className="space-y-2">
                    <p className="text-xs text-muted-foreground">Suggested questions:</p>
                    <div className="flex flex-wrap gap-1 justify-center">
                      {suggestions.suggestions.slice(0, 4).map((suggestion, idx) => (
                        <Button
                          key={idx}
                          variant="outline"
                          size="sm"
                          className="text-xs h-auto py-1 px-2"
                          onClick={() => handleSuggestionClick(suggestion)}
                        >
                          {suggestion.length > 40 ? suggestion.slice(0, 40) + '...' : suggestion}
                        </Button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={cn(
                  "flex",
                  msg.role === 'user' ? "justify-end" : "justify-start"
                )}
              >
                <div className={cn(
                  "max-w-[85%] rounded-lg px-3 py-2 text-sm",
                  msg.role === 'user'
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted"
                )}>
                  <p className="whitespace-pre-wrap">{msg.content}</p>

                  {/* Citations */}
                  {msg.citations && msg.citations.length > 0 && (
                    <div className="mt-2 pt-2 border-t border-border/50">
                      <p className="text-xs opacity-70 mb-1">Sources:</p>
                      <div className="space-y-1">
                        {msg.citations.map((citation, cidx) => (
                          <div
                            key={cidx}
                            className="text-xs opacity-80 flex items-start gap-1"
                          >
                            <ExternalLink className="h-3 w-3 mt-0.5 flex-shrink-0" />
                            <span className="truncate" title={citation.content_snippet}>
                              {citation.source} ({Math.round(citation.similarity_score * 100)}% match)
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Confidence indicator */}
                  {msg.confidence !== undefined && (
                    <div className="mt-1">
                      <Badge variant="outline" className="text-xs">
                        {Math.round(msg.confidence * 100)}% confident
                      </Badge>
                    </div>
                  )}
                </div>
              </div>
            ))}

            {/* Loading indicator */}
            {sendMessage.isPending && (
              <div className="flex justify-start">
                <div className="bg-muted rounded-lg px-3 py-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input area */}
          <div className="p-3 border-t">
            <div className="flex gap-2">
              <Textarea
                ref={textareaRef}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask a question..."
                className="min-h-[40px] max-h-[100px] resize-none text-sm"
                disabled={sendMessage.isPending}
              />
              <Button
                onClick={handleSend}
                disabled={!message.trim() || sendMessage.isPending}
                size="icon"
                className="flex-shrink-0"
              >
                {sendMessage.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Press Enter to send, Shift+Enter for new line
            </p>
          </div>
        </CardContent>
      )}
    </Card>
  )
}

export default RFPChat
