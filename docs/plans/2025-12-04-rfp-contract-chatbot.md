# RFP Contract Chatbot Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Wire existing chatbot infrastructure together so users can ask questions about specific RFPs and get RAG-powered AI responses with citations.

**Architecture:** Frontend ContractChatbot component connects to backend chat endpoints. Backend retrieves RFP-specific context via RAG engine, sends to Claude LLM, streams response back with citations. Sessions persist in database.

**Tech Stack:** React + TypeScript, FastAPI, ChromaDB RAG, Claude API (streaming), SQLAlchemy, shadcn/ui

---

## Current State Assessment

The codebase already has most pieces implemented but not fully connected:

| Component | Status | Location |
|-----------|--------|----------|
| ChatSession/ChatMessage models | ✅ Complete | `api/app/models/database.py:913-996` |
| ContractChatbot component | ✅ Complete | `frontend/src/components/ContractChatbot.tsx` |
| useStreamingChat hook | ✅ Complete | `frontend/src/hooks/useStreamingChat.ts` |
| Chat API client methods | ✅ Complete | `frontend/src/services/api.ts` |
| Chat routes (partial) | ⚠️ Needs completion | `api/app/routes/chat.py` |
| Streaming routes | ✅ Complete | `api/app/routes/streaming.py` |
| RAG engine | ✅ Complete | `src/rag/chroma_rag_engine.py` |

**Gap Analysis:** The backend chat routes need to be completed to handle session management and RFP-specific RAG context retrieval.

---

### Task 1: Complete Backend Chat Session Endpoints

**Files:**
- Modify: `api/app/routes/chat.py`
- Reference: `api/app/models/database.py:913-996`

**Step 1: Read existing chat.py to understand current implementation**

Run: `head -100 api/app/routes/chat.py`

Review the existing Pydantic models and any implemented endpoints.

**Step 2: Add session CRUD endpoints**

Add these endpoints to `api/app/routes/chat.py` after the existing code:

```python
from sqlalchemy import desc
from app.models.database import ChatSession, ChatMessage as DBChatMessage
from app.dependencies import DBDep, RFPDep
import uuid

# Session management endpoints

@router.post("/rfps/{rfp_id}/sessions", response_model=SessionResponse)
async def create_chat_session(
    rfp_id: int,
    db: DBDep,
    title: str | None = None
):
    """Create a new chat session for an RFP."""
    # Verify RFP exists
    rfp = db.query(RFPOpportunity).filter(RFPOpportunity.id == rfp_id).first()
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    session = ChatSession(
        session_id=str(uuid.uuid4()),
        rfp_id=rfp_id,
        title=title or f"Chat about {rfp.title[:50]}...",
        is_active=True,
        message_count=0
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return SessionResponse(
        session_id=session.session_id,
        rfp_id=rfp_id,
        title=session.title,
        message_count=0,
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat()
    )


@router.get("/rfps/{rfp_id}/sessions", response_model=list[SessionResponse])
async def list_chat_sessions(rfp_id: int, db: DBDep):
    """List all chat sessions for an RFP."""
    sessions = db.query(ChatSession).filter(
        ChatSession.rfp_id == rfp_id,
        ChatSession.is_active == True
    ).order_by(desc(ChatSession.updated_at)).all()

    return [
        SessionResponse(
            session_id=s.session_id,
            rfp_id=s.rfp_id,
            title=s.title,
            message_count=s.message_count,
            created_at=s.created_at.isoformat(),
            updated_at=s.updated_at.isoformat()
        )
        for s in sessions
    ]


@router.get("/rfps/{rfp_id}/sessions/{session_id}", response_model=SessionResponse)
async def get_chat_session(rfp_id: int, session_id: str, db: DBDep):
    """Get a specific chat session with its messages."""
    session = db.query(ChatSession).filter(
        ChatSession.rfp_id == rfp_id,
        ChatSession.session_id == session_id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionResponse(
        session_id=session.session_id,
        rfp_id=session.rfp_id,
        title=session.title,
        message_count=session.message_count,
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat()
    )


@router.delete("/rfps/{rfp_id}/sessions/{session_id}")
async def delete_chat_session(rfp_id: int, session_id: str, db: DBDep):
    """Delete a chat session and all its messages."""
    session = db.query(ChatSession).filter(
        ChatSession.rfp_id == rfp_id,
        ChatSession.session_id == session_id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    db.delete(session)  # Cascade deletes messages
    db.commit()

    return {"status": "deleted", "session_id": session_id}
```

**Step 3: Run linter to check for errors**

Run: `cd api && python -c "from app.routes import chat; print('OK')"`

Expected: `OK` (no import errors)

**Step 4: Commit**

```bash
git add api/app/routes/chat.py
git commit -m "feat(chat): add session CRUD endpoints"
```

---

### Task 2: Add Chat Message Endpoint with RAG Context

**Files:**
- Modify: `api/app/routes/chat.py`
- Reference: `src/rag/chroma_rag_engine.py`
- Reference: `api/app/services/streaming.py`

**Step 1: Add imports for RAG and LLM at top of chat.py**

```python
from src.rag.chroma_rag_engine import get_rag_engine
from app.services.streaming import get_streaming_service
from datetime import datetime
```

**Step 2: Add the chat message endpoint**

```python
@router.post("/rfps/{rfp_id}/sessions/{session_id}/messages", response_model=ChatResponse)
async def send_chat_message(
    rfp_id: int,
    session_id: str,
    request: ChatRequest,
    db: DBDep
):
    """Send a message and get AI response with RAG context."""
    import time
    start_time = time.time()

    # Get session
    session = db.query(ChatSession).filter(
        ChatSession.rfp_id == rfp_id,
        ChatSession.session_id == session_id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get RFP for context
    rfp = db.query(RFPOpportunity).filter(RFPOpportunity.id == rfp_id).first()
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    # Save user message
    user_msg = DBChatMessage(
        session_id=session.id,
        role="user",
        content=request.message
    )
    db.add(user_msg)

    # Get RAG context
    rag_engine = get_rag_engine()
    rag_results = rag_engine.retrieve(request.message, top_k=5)

    # Build context from RAG results and RFP data
    context_parts = [
        f"RFP Title: {rfp.title}",
        f"Agency: {rfp.agency or 'Unknown'}",
        f"Description: {rfp.description or 'No description'}",
    ]

    if rfp.requirements:
        context_parts.append(f"Requirements: {rfp.requirements[:2000]}")

    # Add RAG retrieved content
    citations = []
    for i, result in enumerate(rag_results):
        context_parts.append(f"\nRelevant Document {i+1}:\n{result['content'][:1000]}")
        citations.append(Citation(
            text=result['content'][:500],
            source=result.get('metadata', {}).get('source', 'RFP Document'),
            similarity=result.get('similarity', 0.0)
        ))

    context = "\n".join(context_parts)

    # Build prompt
    system_prompt = f"""You are an AI assistant helping users understand government RFP (Request for Proposal) documents.
Answer questions based on the provided RFP context. Be specific and cite relevant parts of the RFP when possible.
If you don't know the answer or it's not in the provided context, say so clearly.

RFP Context:
{context}"""

    # Get message history for context
    history_messages = db.query(DBChatMessage).filter(
        DBChatMessage.session_id == session.id
    ).order_by(DBChatMessage.created_at).limit(10).all()

    messages_for_llm = [{"role": "system", "content": system_prompt}]
    for msg in history_messages:
        messages_for_llm.append({"role": msg.role, "content": msg.content})
    messages_for_llm.append({"role": "user", "content": request.message})

    # Call LLM
    streaming_service = get_streaming_service()
    response_text = await streaming_service.generate_response(
        messages=messages_for_llm,
        model="claude-sonnet-4-20250514"
    )

    processing_time = int((time.time() - start_time) * 1000)

    # Save assistant message
    assistant_msg = DBChatMessage(
        session_id=session.id,
        role="assistant",
        content=response_text,
        citations=[c.model_dump() for c in citations],
        processing_time_ms=processing_time,
        model_used="claude-sonnet-4-20250514"
    )
    db.add(assistant_msg)

    # Update session
    session.message_count += 2
    session.last_message_at = datetime.utcnow()
    session.updated_at = datetime.utcnow()

    db.commit()

    return ChatResponse(
        answer=response_text,
        citations=citations,
        confidence=sum(c.similarity for c in citations) / len(citations) if citations else 0.5,
        processing_time_ms=processing_time
    )
```

**Step 3: Test import**

Run: `cd api && python -c "from app.routes import chat; print('OK')"`

Expected: `OK`

**Step 4: Commit**

```bash
git add api/app/routes/chat.py
git commit -m "feat(chat): add message endpoint with RAG context"
```

---

### Task 3: Add Streaming Chat Endpoint

**Files:**
- Modify: `api/app/routes/chat.py`

**Step 1: Add streaming endpoint**

```python
from fastapi.responses import StreamingResponse
import json

@router.get("/rfps/{rfp_id}/sessions/{session_id}/stream")
async def stream_chat_message(
    rfp_id: int,
    session_id: str,
    message: str,
    db: DBDep
):
    """Stream a chat response with RAG context."""

    # Get session and RFP
    session = db.query(ChatSession).filter(
        ChatSession.rfp_id == rfp_id,
        ChatSession.session_id == session_id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    rfp = db.query(RFPOpportunity).filter(RFPOpportunity.id == rfp_id).first()
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    async def generate():
        # Get RAG context
        rag_engine = get_rag_engine()
        rag_results = rag_engine.retrieve(message, top_k=5)

        # Send citations first
        citations = []
        for result in rag_results:
            citations.append({
                "text": result['content'][:500],
                "source": result.get('metadata', {}).get('source', 'RFP Document'),
                "similarity": result.get('similarity', 0.0)
            })

        yield f"data: {json.dumps({'type': 'citations', 'citations': citations})}\n\n"

        # Build context
        context_parts = [
            f"RFP Title: {rfp.title}",
            f"Agency: {rfp.agency or 'Unknown'}",
            f"Description: {rfp.description or 'No description'}",
        ]

        for i, result in enumerate(rag_results):
            context_parts.append(f"\nRelevant Document {i+1}:\n{result['content'][:1000]}")

        context = "\n".join(context_parts)

        system_prompt = f"""You are an AI assistant helping users understand government RFP documents.
Answer based on the provided context. Be specific and cite relevant parts.

RFP Context:
{context}"""

        # Stream LLM response
        streaming_service = get_streaming_service()
        async for chunk in streaming_service.stream_response(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            model="claude-sonnet-4-20250514"
        ):
            yield f"data: {json.dumps({'type': 'text', 'content': chunk})}\n\n"

        yield f"data: {json.dumps({'type': 'complete'})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
```

**Step 2: Test import**

Run: `cd api && python -c "from app.routes import chat; print('OK')"`

Expected: `OK`

**Step 3: Commit**

```bash
git add api/app/routes/chat.py
git commit -m "feat(chat): add streaming chat endpoint with SSE"
```

---

### Task 4: Add Suggested Questions Endpoint

**Files:**
- Modify: `api/app/routes/chat.py`

**Step 1: Add suggestions endpoint**

```python
@router.get("/rfps/{rfp_id}/chat/suggestions")
async def get_chat_suggestions(rfp_id: int, db: DBDep):
    """Get suggested questions based on RFP content."""

    rfp = db.query(RFPOpportunity).filter(RFPOpportunity.id == rfp_id).first()
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    # Generate context-aware suggestions
    suggestions = [
        "What are the key requirements for this RFP?",
        "What is the submission deadline?",
        "Who are the eligible bidders for this contract?",
    ]

    # Add dynamic suggestions based on RFP content
    if rfp.award_amount:
        suggestions.append(f"What is the budget or estimated value?")

    if rfp.naics_code:
        suggestions.append(f"What NAICS codes are required?")

    if rfp.agency:
        suggestions.append(f"Tell me about the contracting agency.")

    # Check for documents
    if rfp.documents and len(rfp.documents) > 0:
        suggestions.append("What documents are attached to this RFP?")

    # Check for Q&A
    if rfp.qanda_items and len(rfp.qanda_items) > 0:
        suggestions.append("Are there any Q&A responses for this RFP?")

    return {"suggestions": suggestions[:6]}  # Return max 6 suggestions
```

**Step 2: Test import**

Run: `cd api && python -c "from app.routes import chat; print('OK')"`

Expected: `OK`

**Step 3: Commit**

```bash
git add api/app/routes/chat.py
git commit -m "feat(chat): add suggested questions endpoint"
```

---

### Task 5: Register Chat Routes in Main App

**Files:**
- Modify: `api/app/main.py`

**Step 1: Check current route registration**

Run: `grep -n "chat" api/app/main.py`

Check if chat routes are already registered.

**Step 2: Add chat route registration if missing**

If not already present, add after other route registrations:

```python
from app.routes import chat

app.include_router(
    chat.router,
    prefix=f"{settings.API_V1_STR}/chat",
    tags=["chat"]
)
```

**Step 3: Verify server starts**

Run: `cd api && python -c "from app.main import app; print('App loaded OK')"`

Expected: `App loaded OK`

**Step 4: Commit**

```bash
git add api/app/main.py
git commit -m "feat(routes): register chat routes in main app"
```

---

### Task 6: Integrate ContractChatbot in RFPDetail Page

**Files:**
- Modify: `frontend/src/pages/RFPDetail.tsx`
- Reference: `frontend/src/components/ContractChatbot.tsx`

**Step 1: Check if ContractChatbot is already imported**

Run: `grep -n "ContractChatbot" frontend/src/pages/RFPDetail.tsx`

**Step 2: Add import if missing**

At the top of RFPDetail.tsx:

```typescript
import { ContractChatbot } from '@/components/ContractChatbot'
```

**Step 3: Add ContractChatbot component to the page**

Find the return statement and add the chatbot component. It should be a floating component at the bottom of the page:

```typescript
// Inside the return, before the closing fragment or main container
<ContractChatbot
  rfpId={rfpId}
  rfpTitle={rfp?.title || 'RFP'}
  className="fixed bottom-4 right-4 z-50"
/>
```

**Step 4: Verify build**

Run: `cd frontend && npm run build 2>&1 | head -30`

Expected: Build succeeds or shows only warnings (not errors)

**Step 5: Commit**

```bash
git add frontend/src/pages/RFPDetail.tsx
git commit -m "feat(ui): integrate ContractChatbot in RFP detail page"
```

---

### Task 7: Update API Client for New Endpoints

**Files:**
- Modify: `frontend/src/services/api.ts`

**Step 1: Check existing chat methods**

Run: `grep -A5 "chat" frontend/src/services/api.ts | head -40`

**Step 2: Add or update chat API methods**

Ensure these methods exist in the api object:

```typescript
// Chat session management
createChatSession: (rfpId: string, title?: string) =>
  apiClient.post(`/chat/rfps/${rfpId}/sessions`, null, { params: { title } }),

listChatSessions: (rfpId: string) =>
  apiClient.get(`/chat/rfps/${rfpId}/sessions`),

getChatSession: (rfpId: string, sessionId: string) =>
  apiClient.get(`/chat/rfps/${rfpId}/sessions/${sessionId}`),

deleteChatSession: (rfpId: string, sessionId: string) =>
  apiClient.delete(`/chat/rfps/${rfpId}/sessions/${sessionId}`),

// Chat messages
sendChatMessage: (rfpId: string, sessionId: string, message: string) =>
  apiClient.post(`/chat/rfps/${rfpId}/sessions/${sessionId}/messages`, { message }),

// Streaming endpoint URL builder (for EventSource)
getChatStreamUrl: (rfpId: string, sessionId: string, message: string) =>
  `/api/v1/chat/rfps/${rfpId}/sessions/${sessionId}/stream?message=${encodeURIComponent(message)}`,

// Suggestions
getChatSuggestions: (rfpId: string) =>
  apiClient.get(`/chat/rfps/${rfpId}/chat/suggestions`),
```

**Step 3: Verify build**

Run: `cd frontend && npm run build 2>&1 | head -20`

Expected: Build succeeds

**Step 4: Commit**

```bash
git add frontend/src/services/api.ts
git commit -m "feat(api): update chat API client methods"
```

---

### Task 8: Add Export Conversation Feature

**Files:**
- Modify: `frontend/src/components/ContractChatbot.tsx`

**Step 1: Add export function**

Add this function inside the ContractChatbot component:

```typescript
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
}
```

**Step 2: Add export button to the chat header**

Find the chat header section and add:

```typescript
<Button
  variant="ghost"
  size="icon"
  onClick={exportConversation}
  disabled={messages.length === 0}
  title="Export conversation"
>
  <Download className="h-4 w-4" />
</Button>
```

**Step 3: Add Download import if missing**

```typescript
import { Download } from 'lucide-react'
```

**Step 4: Verify build**

Run: `cd frontend && npm run build 2>&1 | head -20`

Expected: Build succeeds

**Step 5: Commit**

```bash
git add frontend/src/components/ContractChatbot.tsx
git commit -m "feat(chat): add export conversation feature"
```

---

### Task 9: Add Message History Endpoint

**Files:**
- Modify: `api/app/routes/chat.py`

**Step 1: Add history endpoint**

```python
@router.get("/rfps/{rfp_id}/sessions/{session_id}/messages")
async def get_chat_history(
    rfp_id: int,
    session_id: str,
    db: DBDep,
    limit: int = 50
):
    """Get chat history for a session."""

    session = db.query(ChatSession).filter(
        ChatSession.rfp_id == rfp_id,
        ChatSession.session_id == session_id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = db.query(DBChatMessage).filter(
        DBChatMessage.session_id == session.id
    ).order_by(DBChatMessage.created_at).limit(limit).all()

    return {
        "session_id": session_id,
        "messages": [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "citations": msg.citations or [],
                "created_at": msg.created_at.isoformat()
            }
            for msg in messages
        ]
    }
```

**Step 2: Test import**

Run: `cd api && python -c "from app.routes import chat; print('OK')"`

Expected: `OK`

**Step 3: Commit**

```bash
git add api/app/routes/chat.py
git commit -m "feat(chat): add message history endpoint"
```

---

### Task 10: Integration Testing

**Files:**
- Create: `tests/test_chat_api.py`

**Step 1: Create test file**

```python
"""Tests for chat API endpoints."""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_create_chat_session():
    """Test creating a new chat session."""
    # First, get an existing RFP ID
    response = client.get("/api/v1/rfps/?limit=1")
    assert response.status_code == 200
    rfps = response.json()

    if not rfps.get("items"):
        pytest.skip("No RFPs in database")

    rfp_id = rfps["items"][0]["id"]

    # Create session
    response = client.post(f"/api/v1/chat/rfps/{rfp_id}/sessions")
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert data["rfp_id"] == rfp_id


def test_list_chat_sessions():
    """Test listing chat sessions."""
    response = client.get("/api/v1/rfps/?limit=1")
    if not response.json().get("items"):
        pytest.skip("No RFPs in database")

    rfp_id = response.json()["items"][0]["id"]

    response = client.get(f"/api/v1/chat/rfps/{rfp_id}/sessions")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_chat_suggestions():
    """Test getting chat suggestions."""
    response = client.get("/api/v1/rfps/?limit=1")
    if not response.json().get("items"):
        pytest.skip("No RFPs in database")

    rfp_id = response.json()["items"][0]["id"]

    response = client.get(f"/api/v1/chat/rfps/{rfp_id}/chat/suggestions")
    assert response.status_code == 200
    data = response.json()
    assert "suggestions" in data
    assert len(data["suggestions"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

**Step 2: Run tests**

Run: `cd api && python -m pytest tests/test_chat_api.py -v`

Expected: All tests pass (or skip if no RFPs)

**Step 3: Commit**

```bash
git add tests/test_chat_api.py
git commit -m "test(chat): add integration tests for chat API"
```

---

### Task 11: Final Verification

**Step 1: Restart backend**

Run: `docker-compose restart backend`

**Step 2: Verify backend logs**

Run: `docker-compose logs backend --tail=20`

Expected: No errors, server started successfully

**Step 3: Test frontend build**

Run: `cd frontend && npm run build`

Expected: Build succeeds

**Step 4: Manual testing checklist**

- [ ] Navigate to an RFP detail page
- [ ] Verify chat button appears in bottom-right
- [ ] Click to open chat interface
- [ ] Verify suggested questions appear
- [ ] Send a test message
- [ ] Verify response streams in
- [ ] Check citations are displayed
- [ ] Test export conversation
- [ ] Test clear conversation

**Step 5: Final commit**

```bash
git add .
git commit -m "feat(chat): complete RFP contract chatbot integration"
```

---

## Summary

This plan wires together existing infrastructure:

1. **Backend** (Tasks 1-4, 9): Complete chat routes with session management, RAG context retrieval, streaming, and suggestions
2. **Route Registration** (Task 5): Register chat routes in FastAPI app
3. **Frontend Integration** (Tasks 6-8): Integrate ContractChatbot component, update API client, add export feature
4. **Testing** (Tasks 10-11): Integration tests and manual verification

**Total Tasks:** 11
**Estimated Code Changes:** ~400 lines (mostly backend endpoints)
**Risk Level:** Low (using existing infrastructure)
