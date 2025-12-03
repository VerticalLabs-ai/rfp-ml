# Contract Chatbot Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement a GovGPT-style AI chatbot for answering questions about specific RFP contracts with streaming responses, session persistence, and document awareness.

**Architecture:** The backend already has chat endpoints with RAG and session management. This plan enhances the backend with streaming support and builds a full-featured frontend component with session management, markdown rendering, and streaming UI.

**Tech Stack:** FastAPI (SSE streaming), React, TanStack Query, react-markdown, Lucide icons

---

## Existing Infrastructure (No Changes Needed)

The following are already implemented and working:

- **Backend Chat Routes** (`api/app/routes/chat.py`):
  - `POST /{rfp_id}/chat` - RAG-powered Q&A with citations
  - `GET /{rfp_id}/chat/suggestions` - Dynamic suggested questions
  - `POST /{rfp_id}/sessions` - Create chat session
  - `GET /{rfp_id}/sessions` - List sessions
  - `GET /{rfp_id}/sessions/{session_id}` - Get session with messages
  - `DELETE /{rfp_id}/sessions/{session_id}` - Delete session
  - `GET /{rfp_id}/chat/status` - Check RAG/LLM availability

- **Database Models** (`api/app/models/database.py`):
  - `ChatSession` - session_id, rfp_id, title, summary, message_count, timestamps
  - `ChatMessage` - role, content, citations, confidence, rag_context

---

## Task 1: Add Streaming Chat Endpoint

**Files:**
- Modify: `api/app/routes/chat.py`

**Step 1: Write the streaming endpoint**

Add after the existing `chat_with_rfp` endpoint (around line 330):

```python
from fastapi.responses import StreamingResponse
import asyncio
import json


@router.post("/{rfp_id}/chat/stream")
async def stream_chat_with_rfp(rfp: RFPDep, request: ChatRequest, db: DBDep):
    """
    Stream chat response using Server-Sent Events (SSE).

    Yields chunks as they are generated for real-time UI updates.
    """
    import time
    from app.models.database import ChatMessage as DBChatMessage
    from app.models.database import ChatSession

    start_time = time.time()
    session = None
    history = request.history

    # Load session if provided
    if request.session_id:
        session = (
            db.query(ChatSession)
            .filter(
                ChatSession.session_id == request.session_id,
                ChatSession.rfp_id == rfp.id,
                ChatSession.is_active == True,
            )
            .first()
        )
        if session:
            db_messages = session.messages[-10:]
            history = [
                ChatMessage(
                    role=m.role,
                    content=m.content,
                    timestamp=m.created_at.isoformat() if m.created_at else None,
                )
                for m in db_messages
            ]

    async def generate():
        nonlocal session
        try:
            from src.rag.chroma_rag_engine import get_rag_engine
            from src.config.llm_adapter import create_llm_interface

            rag_engine = get_rag_engine()
            if not rag_engine or rag_engine.collection.count() == 0:
                yield f"data: {json.dumps({'type': 'error', 'content': 'RAG engine not available'})}\n\n"
                return

            llm = create_llm_interface()

            # Send thinking status
            yield f"data: {json.dumps({'type': 'status', 'content': 'Searching documents...'})}\n\n"
            await asyncio.sleep(0.1)

            # Retrieve context
            enhanced_query = f"{rfp.title} {rfp.agency or ''} {request.message}"
            rag_context = rag_engine.generate_context(enhanced_query, k=5)

            if not rag_context.retrieved_documents:
                yield f"data: {json.dumps({'type': 'content', 'content': 'I couldn\\'t find specific information about that in the available documents.'})}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'citations': []})}\n\n"
                return

            yield f"data: {json.dumps({'type': 'status', 'content': 'Generating response...'})}\n\n"
            await asyncio.sleep(0.1)

            # Build prompt
            prompt = build_chat_prompt(
                question=request.message,
                context=rag_context.context_text,
                history=history,
                rfp_title=rfp.title,
                rfp_agency=rfp.agency,
            )

            # Generate response (for now, non-streaming from LLM, chunked to client)
            try:
                llm_result = llm.generate_text(prompt, use_case="chat")
                answer = llm_result.get("content", llm_result.get("text", ""))

                # Stream response in chunks for UI effect
                chunk_size = 50
                for i in range(0, len(answer), chunk_size):
                    chunk = answer[i:i + chunk_size]
                    yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"
                    await asyncio.sleep(0.02)  # Small delay for streaming effect

                # Calculate confidence
                avg_score = sum(
                    doc.similarity_score for doc in rag_context.retrieved_documents
                ) / len(rag_context.retrieved_documents)
                confidence = min(avg_score * 1.2, 1.0)

                # Extract citations
                citations_list = extract_citations(rag_context.retrieved_documents)

                # Save to session if exists
                if session:
                    try:
                        user_msg = DBChatMessage(
                            session_id=session.id,
                            role="user",
                            content=request.message,
                        )
                        db.add(user_msg)

                        assistant_msg = DBChatMessage(
                            session_id=session.id,
                            role="assistant",
                            content=answer,
                            citations=[c.model_dump() for c in citations_list],
                            confidence=round(confidence, 2),
                        )
                        db.add(assistant_msg)

                        session.message_count += 2
                        session.last_message_at = datetime.now(timezone.utc)
                        session.updated_at = datetime.now(timezone.utc)
                        db.commit()
                    except Exception:
                        db.rollback()

                processing_time = int((time.time() - start_time) * 1000)

                yield f"data: {json.dumps({'type': 'done', 'citations': [c.model_dump() for c in citations_list], 'confidence': round(confidence, 2), 'processing_time_ms': processing_time})}\n\n"

            except Exception as e:
                logger.error(f"LLM generation error: {e}")
                yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': 'An error occurred'})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

**Step 2: Test the endpoint manually**

Run: `curl -N -X POST "http://localhost:8000/api/v1/rfps/1/chat/stream" -H "Content-Type: application/json" -d '{"message": "What are the key requirements?"}'`

Expected: SSE stream with `data: {...}` chunks

**Step 3: Commit**

```bash
git add api/app/routes/chat.py
git commit -m "feat(chat): add streaming chat endpoint with SSE"
```

---

## Task 2: Add API Client Methods for Chat

**Files:**
- Modify: `frontend/src/services/api.ts`

**Step 1: Add chat API methods**

Find the existing API methods section and add:

```typescript
  // Chat endpoints
  createChatSession: (rfpId: string, title?: string) =>
    apiClient.post(`/rfps/${rfpId}/sessions`, null, { params: { title } }).then(res => res.data),

  listChatSessions: (rfpId: string) =>
    apiClient.get(`/rfps/${rfpId}/sessions`).then(res => res.data),

  getChatSession: (rfpId: string, sessionId: string) =>
    apiClient.get(`/rfps/${rfpId}/sessions/${sessionId}`).then(res => res.data),

  deleteChatSession: (rfpId: string, sessionId: string) =>
    apiClient.delete(`/rfps/${rfpId}/sessions/${sessionId}`).then(res => res.data),

  getChatSuggestions: (rfpId: string) =>
    apiClient.get(`/rfps/${rfpId}/chat/suggestions`).then(res => res.data),

  getChatStatus: (rfpId: string) =>
    apiClient.get(`/rfps/${rfpId}/chat/status`).then(res => res.data),

  // Streaming chat - returns EventSource URL
  getStreamingChatUrl: (rfpId: string) =>
    `${apiClient.defaults.baseURL}/rfps/${rfpId}/chat/stream`,
```

**Step 2: Verify TypeScript compilation**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

**Step 3: Commit**

```bash
git add frontend/src/services/api.ts
git commit -m "feat(api): add chat session management endpoints"
```

---

## Task 3: Create ContractChatbot Component - Types and State

**Files:**
- Create: `frontend/src/components/ContractChatbot.tsx`

**Step 1: Create the component file with types and state**

```tsx
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { format } from 'date-fns'
import {
  Bot,
  Check,
  ChevronDown,
  Copy,
  FileText,
  History,
  Loader2,
  MessageSquare,
  Paperclip,
  Plus,
  Send,
  Sparkles,
  Trash2,
  X,
  XCircle,
} from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { toast } from 'sonner'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
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

  // TODO: Implement queries and mutations in next task

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
        {/* Placeholder - will be replaced in next tasks */}
        <div className="flex-1 flex items-center justify-center text-muted-foreground">
          <p>Chat component loading...</p>
        </div>
      </CardContent>
    </Card>
  )
}
```

**Step 2: Verify TypeScript compilation**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors (may need to install react-markdown)

**Step 3: Install react-markdown if needed**

Run: `cd frontend && npm install react-markdown`

**Step 4: Commit**

```bash
git add frontend/src/components/ContractChatbot.tsx
git commit -m "feat(chat): scaffold ContractChatbot component with types"
```

---

## Task 4: Implement Chat Queries and Session Management

**Files:**
- Modify: `frontend/src/components/ContractChatbot.tsx`

**Step 1: Add queries after the refs section**

Replace `// TODO: Implement queries and mutations in next task` with:

```tsx
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
```

**Step 2: Verify TypeScript compilation**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

**Step 3: Commit**

```bash
git add frontend/src/components/ContractChatbot.tsx
git commit -m "feat(chat): add session management queries and mutations"
```

---

## Task 5: Implement Streaming Message Handler

**Files:**
- Modify: `frontend/src/components/ContractChatbot.tsx`

**Step 1: Add streaming handler after the loadSession callback**

```tsx
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

  // Handle suggestion click
  const handleSuggestionClick = (suggestion: string) => {
    setMessage(suggestion)
    inputRef.current?.focus()
  }
```

**Step 2: Verify TypeScript compilation**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

**Step 3: Commit**

```bash
git add frontend/src/components/ContractChatbot.tsx
git commit -m "feat(chat): implement streaming message handler with SSE"
```

---

## Task 6: Implement Chat UI - Messages and Input

**Files:**
- Modify: `frontend/src/components/ContractChatbot.tsx`

**Step 1: Replace the CardContent placeholder with full UI**

Replace the entire `<CardContent>` section with:

```tsx
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
```

**Step 2: Verify TypeScript compilation**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

**Step 3: Commit**

```bash
git add frontend/src/components/ContractChatbot.tsx
git commit -m "feat(chat): implement full chat UI with messages, suggestions, sessions"
```

---

## Task 7: Integrate Chatbot into RFPDetail Page

**Files:**
- Modify: `frontend/src/pages/RFPDetail.tsx`

**Step 1: Import the new component**

Add to imports at the top:

```tsx
import { ContractChatbot } from '@/components/ContractChatbot'
```

**Step 2: Replace the existing floating chat panel**

Find the `{/* Floating AI Chat Panel */}` section (around line 1676) and replace the entire section (from `<div className="fixed bottom-6 right-6 z-50">` to its closing `</div>`) with:

```tsx
      {/* Contract Chatbot */}
      <ContractChatbot
        rfpId={rfpId!}
        rfpTitle={rfp.title}
        isOpen={isChatOpen}
        onClose={() => setIsChatOpen(false)}
      />

      {/* Chat Toggle Button */}
      {!isChatOpen && (
        <Button
          size="lg"
          className="fixed bottom-6 right-6 z-50 rounded-full h-14 w-14 shadow-lg bg-purple-500 hover:bg-purple-600"
          onClick={() => setIsChatOpen(true)}
        >
          <Bot className="h-6 w-6" />
        </Button>
      )}
```

**Step 3: Remove unused chat state and handlers**

Remove these lines that are no longer needed (the component handles its own state):
- `const [chatMessage, setChatMessage] = useState('')`
- `const [chatMessages, setChatMessages] = useState<ChatMessage[]>([])`
- `const chatScrollRef = useRef<HTMLDivElement>(null)`
- The `chatMutation` definition
- The `handleSendMessage` function
- The `ChatMessage` interface (if not used elsewhere)

**Step 4: Verify TypeScript compilation**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

**Step 5: Build and test**

Run: `cd frontend && npm run build`
Expected: Build succeeds

**Step 6: Commit**

```bash
git add frontend/src/pages/RFPDetail.tsx frontend/src/components/ContractChatbot.tsx
git commit -m "feat(chat): integrate ContractChatbot into RFPDetail page"
```

---

## Task 8: Add Chat Button to RFP Cards in Discovery

**Files:**
- Modify: `frontend/src/components/RFPCard.tsx`

**Step 1: Find the RFPCard component and add chat button**

Add a chat button to the card actions area. Find the existing action buttons and add:

```tsx
<Button
  variant="ghost"
  size="sm"
  onClick={(e) => {
    e.stopPropagation()
    // Navigate to RFP detail with chat open
    navigate(`/rfp/${rfp.rfp_id}?chat=open`)
  }}
  title="Chat with AI about this RFP"
>
  <MessageSquare className="h-4 w-4" />
</Button>
```

**Step 2: Import MessageSquare if not already**

```tsx
import { MessageSquare } from 'lucide-react'
```

**Step 3: Verify TypeScript compilation**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

**Step 4: Commit**

```bash
git add frontend/src/components/RFPCard.tsx
git commit -m "feat(chat): add chat button to RFP cards in discovery"
```

---

## Task 9: Handle chat=open Query Parameter in RFPDetail

**Files:**
- Modify: `frontend/src/pages/RFPDetail.tsx`

**Step 1: Add query parameter handling**

Add after `const queryClient = useQueryClient()`:

```tsx
const [searchParams] = useSearchParams()
```

Then modify the initial isChatOpen state:

```tsx
const [isChatOpen, setIsChatOpen] = useState(() => searchParams.get('chat') === 'open')
```

**Step 2: Add useSearchParams import**

Ensure `useSearchParams` is imported from `react-router-dom`.

**Step 3: Verify TypeScript compilation**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

**Step 4: Commit**

```bash
git add frontend/src/pages/RFPDetail.tsx
git commit -m "feat(chat): auto-open chat panel from URL parameter"
```

---

## Task 10: Final Integration Test

**Step 1: Start the backend**

Run: `cd /Users/mgunnin/Developer/08_Clients/ibyte/rfp_ml && docker-compose up -d`

**Step 2: Start the frontend**

Run: `cd frontend && npm run dev`

**Step 3: Manual test checklist**

- [ ] Navigate to RFP Discovery page
- [ ] Click chat button on an RFP card
- [ ] Verify chat panel opens on RFP detail page
- [ ] Type a question and press Enter
- [ ] Verify streaming response appears with "Searching..." then content
- [ ] Verify markdown renders correctly
- [ ] Click copy button on assistant message
- [ ] Click History icon and create new session
- [ ] Verify session is listed
- [ ] Close chat and reopen - verify messages persist (within session)
- [ ] Test suggested questions clicking

**Step 4: Build verification**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no errors

**Step 5: Final commit**

```bash
git add .
git commit -m "feat: complete Contract Chatbot implementation with streaming"
```

---

## Summary of Changes

### Backend
- `api/app/routes/chat.py`: Added `POST /{rfp_id}/chat/stream` SSE endpoint

### Frontend
- `frontend/src/services/api.ts`: Added chat session management API methods
- `frontend/src/components/ContractChatbot.tsx`: New full-featured chat component
- `frontend/src/pages/RFPDetail.tsx`: Integrated ContractChatbot, removed old inline chat
- `frontend/src/components/RFPCard.tsx`: Added chat button for quick access

### Dependencies
- `react-markdown`: For rendering assistant responses
