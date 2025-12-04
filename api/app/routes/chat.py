"""
Conversational RFP Chat API endpoints.

Provides a GovGPT-style AI chatbot that answers questions about specific RFPs
using RAG (Retrieval-Augmented Generation) for accurate, cited responses.

Features:
- Session persistence for conversation history
- RAG-powered context retrieval
- Streaming support via SSE
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from app.dependencies import DBDep, RFPDep
from app.models.database import RFPOpportunity
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()


class ChatMessage(BaseModel):
    """A single chat message."""

    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: str | None = None


class ChatRequest(BaseModel):
    """Request body for chat endpoint."""

    message: str = Field(
        ..., min_length=1, max_length=2000, description="User's question"
    )
    session_id: str | None = Field(None, description="Session ID for persistence")
    history: list[ChatMessage] = Field(
        default_factory=list,
        max_length=20,
        description="Previous conversation messages (used if no session_id)",
    )


class SessionResponse(BaseModel):
    """Response for session operations."""

    session_id: str
    rfp_id: str
    title: str | None
    message_count: int
    created_at: str
    last_message_at: str | None


class SessionListResponse(BaseModel):
    """Response for listing sessions."""

    sessions: list[SessionResponse]
    total: int


class Citation(BaseModel):
    """A citation from retrieved documents."""

    document_id: str
    content_snippet: str
    source: str
    similarity_score: float


class ChatResponse(BaseModel):
    """Response from the chat endpoint."""

    answer: str
    citations: list[Citation]
    confidence: float
    rfp_id: str
    processing_time_ms: int
    session_id: str | None = None


# Suggested questions based on common RFP queries
SUGGESTED_QUESTIONS = [
    "What are the key requirements for this RFP?",
    "What is the submission deadline?",
    "What certifications or qualifications are required?",
    "What is the expected contract value?",
    "Are there any set-aside requirements?",
    "What is the scope of work?",
    "Who is the contracting officer?",
    "What evaluation criteria will be used?",
]


def build_chat_prompt(
    question: str,
    context: str,
    history: list[ChatMessage],
    rfp_title: str,
    rfp_agency: str | None,
) -> str:
    """Build a prompt for the LLM with context and history."""
    # Build conversation history string
    history_str = ""
    if history:
        history_parts = []
        for msg in history[-5:]:  # Only use last 5 messages
            role = "User" if msg.role == "user" else "Assistant"
            history_parts.append(f"{role}: {msg.content}")
        history_str = "\n".join(history_parts)

    prompt = f"""You are an AI assistant helping users understand government RFP (Request for Proposal) documents.
You have access to relevant document excerpts from the RFP "{rfp_title}" from {rfp_agency or 'the contracting agency'}.

Based ONLY on the provided context, answer the user's question accurately and concisely.
If the answer is not found in the context, say "I don't have enough information in the available documents to answer that question."
Always cite which part of the context your answer comes from.

CONTEXT FROM RFP DOCUMENTS:
{context}

{f"PREVIOUS CONVERSATION:{chr(10)}{history_str}" if history_str else ""}

USER QUESTION: {question}

Provide a helpful, accurate response based on the context above. If citing specific information, mention where it came from."""

    return prompt


def extract_citations(
    retrieved_docs: list[Any], max_citations: int = 3
) -> list[Citation]:
    """Extract citations from retrieved documents."""
    citations = []
    for doc in retrieved_docs[:max_citations]:
        # Get a snippet of the content
        content = doc.content if hasattr(doc, "content") else str(doc)
        snippet = content[:200] + "..." if len(content) > 200 else content

        citations.append(
            Citation(
                document_id=(
                    doc.document_id if hasattr(doc, "document_id") else "unknown"
                ),
                content_snippet=snippet,
                source=(
                    doc.source_dataset
                    if hasattr(doc, "source_dataset")
                    else "RFP Document"
                ),
                similarity_score=(
                    doc.similarity_score if hasattr(doc, "similarity_score") else 0.0
                ),
            )
        )
    return citations


@router.post("/{rfp_id}/chat", response_model=ChatResponse)
async def chat_with_rfp(rfp: RFPDep, request: ChatRequest, db: DBDep):
    """
    Chat with an RFP using AI-powered Q&A.

    Uses RAG to retrieve relevant document sections and generate
    accurate, cited responses about the RFP.

    If session_id is provided, loads history from the session and
    persists messages to it. Otherwise, uses the history from the request.
    """
    import time

    from app.models.database import ChatMessage as DBChatMessage
    from app.models.database import ChatSession

    start_time = time.time()
    session = None
    history = request.history

    try:
        # Load session if session_id is provided
        if request.session_id:
            session = (
                db.query(ChatSession)
                .filter(
                    ChatSession.session_id == request.session_id,
                    ChatSession.rfp_id == rfp.id,
                    ChatSession.is_active is True,
                )
                .first()
            )

            if session:
                # Load history from session (last 10 messages for context)
                db_messages = session.messages[-10:]
                history = [
                    ChatMessage(
                        role=m.role,
                        content=m.content,
                        timestamp=m.created_at.isoformat() if m.created_at else None,
                    )
                    for m in db_messages
                ]
            else:
                logger.warning(
                    f"Session {request.session_id} not found, using request history"
                )

        # Import RAG and LLM components
        from src.config.llm_adapter import create_llm_interface
        from src.rag.chroma_rag_engine import get_rag_engine

        # Initialize components
        rag_engine = get_rag_engine()
        if not rag_engine:
            raise HTTPException(status_code=503, detail="RAG engine not available")
        llm = create_llm_interface()

        # ChromaDB is always ready (persistence is automatic)
        if rag_engine.collection.count() == 0:
            logger.warning("RAG collection is empty")
            raise HTTPException(
                status_code=503, detail="RAG index is empty. Please rebuild the index."
            )

        # Enhance query with RFP context for better retrieval
        enhanced_query = f"{rfp.title} {rfp.agency or ''} {request.message}"

        # Retrieve relevant documents
        rag_context = rag_engine.generate_context(enhanced_query, k=5)

        if not rag_context.retrieved_documents:
            # Fallback response if no documents found
            answer = (
                "I couldn't find specific information about that in the available documents. "
                "Try rephrasing your question or asking about a different aspect of the RFP."
            )
            citations_list: list[Citation] = []
            confidence = 0.0
        else:
            # Build prompt with context
            prompt = build_chat_prompt(
                question=request.message,
                context=rag_context.context_text,
                history=history,
                rfp_title=rfp.title,
                rfp_agency=rfp.agency,
            )

            # Generate response using LLM
            try:
                llm_result = llm.generate_text(prompt, use_case="chat")
                answer = llm_result.get("content", llm_result.get("text", ""))

                # Calculate confidence based on retrieval scores
                avg_score = sum(
                    doc.similarity_score for doc in rag_context.retrieved_documents
                ) / len(rag_context.retrieved_documents)
                confidence = min(avg_score * 1.2, 1.0)  # Scale up slightly, cap at 1.0

            except Exception as e:
                logger.warning(f"LLM generation failed: {e}, using fallback")
                # Fallback: Summarize retrieved content
                answer = "Based on the available documents:\n\n"
                for i, doc in enumerate(rag_context.retrieved_documents[:3], 1):
                    content = (
                        doc.content[:300] if len(doc.content) > 300 else doc.content
                    )
                    answer += f"{i}. {content}\n\n"
                confidence = 0.5

            # Extract citations
            citations_list = extract_citations(rag_context.retrieved_documents)

        processing_time = int((time.time() - start_time) * 1000)

        # Persist messages to session if one was provided/found
        if session:
            try:
                # Save user message
                user_msg = DBChatMessage(
                    session_id=session.id,
                    role="user",
                    content=request.message,
                )
                db.add(user_msg)

                # Save assistant message with citations
                assistant_msg = DBChatMessage(
                    session_id=session.id,
                    role="assistant",
                    content=answer,
                    citations=[c.model_dump() for c in citations_list],
                    confidence=round(confidence, 2),
                )
                db.add(assistant_msg)

                # Update session metadata
                session.message_count += 2
                session.last_message_at = datetime.now(timezone.utc)
                session.updated_at = datetime.now(timezone.utc)

                db.commit()
            except Exception:
                db.rollback()
                logger.exception(
                    f"Failed to persist chat messages for session {session.session_id}"
                )

        return ChatResponse(
            answer=answer,
            citations=citations_list,
            confidence=round(confidence, 2),
            rfp_id=rfp.rfp_id,
            processing_time_ms=processing_time,
            session_id=session.session_id if session else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error for RFP {rfp.rfp_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to process chat request: {str(e)}"
        )


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
                ChatSession.is_active is True,
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
            from src.config.llm_adapter import create_llm_interface
            from src.rag.chroma_rag_engine import get_rag_engine

            rag_engine = get_rag_engine()
            if not rag_engine or rag_engine.collection.count() == 0:
                yield f"data: {json.dumps({'type': 'error', 'content': 'RAG engine not available'})}\n\n"
                return

            llm = create_llm_interface()

            # Send thinking status
            yield f"data: {json.dumps({'type': 'status', 'content': 'Searching documents...'})}\n\n"
            await asyncio.sleep(0.1)

            # Validate message
            if not request.message or not request.message.strip():
                yield f"data: {json.dumps({'type': 'error', 'content': 'Message cannot be empty'})}\n\n"
                return

            if len(request.message) > 5000:
                yield f"data: {json.dumps({'type': 'error', 'content': 'Message too long (max 5000 chars)'})}\n\n"
                return

            # Retrieve context
            enhanced_query = f"{rfp.title} {rfp.agency or ''} {request.message}"
            rag_context = rag_engine.generate_context(enhanced_query, k=5)

            if not rag_context.retrieved_documents:
                error_msg = {
                    "type": "content",
                    "content": "I couldn't find specific information about that in the available documents.",
                }
                yield f"data: {json.dumps(error_msg)}\n\n"
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
                    chunk = answer[i : i + chunk_size]
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
                    except Exception as e:
                        logger.error(f"Failed to save chat to session {session.id}: {e}")
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


@router.get("/{rfp_id}/chat/suggestions")
async def get_chat_suggestions(rfp: RFPDep):
    """
    Get suggested questions for an RFP.

    Returns a list of relevant questions based on the RFP type and content.
    """
    # Start with generic suggestions
    suggestions = list(SUGGESTED_QUESTIONS)

    # Add RFP-specific suggestions based on available data
    specific_suggestions = []

    if rfp.naics_code:
        specific_suggestions.append(
            f"What NAICS code ({rfp.naics_code}) experience is required?"
        )

    if rfp.agency:
        specific_suggestions.append(f"What is {rfp.agency}'s evaluation process?")

    if rfp.response_deadline:
        specific_suggestions.append(
            "What documents must be included in the submission?"
        )

    if rfp.category:
        specific_suggestions.append(
            f"What are typical requirements for {rfp.category} contracts?"
        )

    # Combine and limit
    all_suggestions = specific_suggestions + suggestions
    return {"rfp_id": rfp.rfp_id, "suggestions": all_suggestions[:10]}


@router.post("/{rfp_id}/sessions")
async def create_chat_session(
    rfp: RFPDep,
    db: DBDep,
    title: str | None = None,
) -> SessionResponse:
    """
    Create a new chat session for an RFP.

    Sessions persist conversation history for continued discussions.
    """
    from app.models.database import ChatSession

    session_id = str(uuid.uuid4())

    session = ChatSession(
        session_id=session_id,
        rfp_id=rfp.id,
        title=title or f"Chat about {rfp.title[:50]}",
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return SessionResponse(
        session_id=session.session_id,
        rfp_id=rfp.rfp_id,
        title=session.title,
        message_count=0,
        created_at=session.created_at.isoformat(),
        last_message_at=None,
    )


@router.get("/{rfp_id}/sessions")
async def list_chat_sessions(
    rfp: RFPDep,
    db: DBDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> SessionListResponse:
    """
    List all chat sessions for an RFP.
    """
    from app.models.database import ChatSession

    query = (
        db.query(ChatSession)
        .filter(ChatSession.rfp_id == rfp.id, ChatSession.is_active is True)
        .order_by(ChatSession.updated_at.desc())
    )

    total = query.count()
    sessions = query.offset(skip).limit(limit).all()

    return SessionListResponse(
        sessions=[
            SessionResponse(
                session_id=s.session_id,
                rfp_id=rfp.rfp_id,
                title=s.title,
                message_count=s.message_count,
                created_at=s.created_at.isoformat(),
                last_message_at=(
                    s.last_message_at.isoformat() if s.last_message_at else None
                ),
            )
            for s in sessions
        ],
        total=total,
    )


@router.get("/{rfp_id}/sessions/{session_id}")
async def get_chat_session(
    rfp: RFPDep,
    session_id: str,
    db: DBDep,
):
    """
    Get a chat session with all its messages.
    """
    from app.models.database import ChatSession

    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.session_id == session_id,
            ChatSession.rfp_id == rfp.id,
        )
        .first()
    )

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        **session.to_dict(),
        "rfp_id": rfp.rfp_id,
        "messages": [m.to_dict() for m in session.messages],
    }


@router.delete("/{rfp_id}/sessions/{session_id}")
async def delete_chat_session(
    rfp: RFPDep,
    session_id: str,
    db: DBDep,
):
    """
    Delete (deactivate) a chat session.
    """
    from app.models.database import ChatSession

    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.session_id == session_id,
            ChatSession.rfp_id == rfp.id,
        )
        .first()
    )

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.is_active = False
    db.commit()

    return {"status": "deleted", "session_id": session_id}


@router.get("/{rfp_id}/chat/status")
async def get_chat_status(rfp: RFPDep):
    """
    Check if chat is available for an RFP.

    Returns the status of RAG and LLM components.
    """
    status = {
        "rfp_id": rfp.rfp_id,
        "chat_available": False,
        "rag_status": "unknown",
        "llm_status": "unknown",
        "message": "",
    }

    try:
        from src.rag.chroma_rag_engine import get_rag_engine

        rag = get_rag_engine()
        if rag:
            doc_count = rag.collection.count()
            status["rag_status"] = "ready" if doc_count > 0 else "empty"
            status["rag_documents"] = doc_count
        else:
            status["rag_status"] = "not_initialized"
            status["rag_documents"] = 0
    except Exception as e:
        status["rag_status"] = f"error: {str(e)}"

    try:
        from src.config.llm_adapter import create_llm_interface

        llm = create_llm_interface()
        llm_status = llm.get_status()
        status["llm_status"] = (
            "ready" if llm_status.get("current_backend") else "not_configured"
        )
        status["llm_backend"] = llm_status.get("current_backend", "unknown")
    except Exception as e:
        status["llm_status"] = f"error: {str(e)}"

    # Determine overall availability
    status["chat_available"] = (
        status["rag_status"] == "ready" and status["llm_status"] == "ready"
    )

    if status["chat_available"]:
        status["message"] = "Chat is ready"
    else:
        issues = []
        if status["rag_status"] != "ready":
            issues.append("RAG index not available")
        if status["llm_status"] != "ready":
            issues.append("LLM not configured")
        status["message"] = "; ".join(issues)

    return status
