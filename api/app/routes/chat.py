"""
Conversational RFP Chat API endpoints.

Provides a GovGPT-style AI chatbot that answers questions about specific RFPs
using RAG (Retrieval-Augmented Generation) for accurate, cited responses.
"""
import logging
from datetime import datetime
from typing import Any

from app.dependencies import RFPDep
from fastapi import APIRouter, HTTPException
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
    message: str = Field(..., min_length=1, max_length=2000, description="User's question")
    history: list[ChatMessage] = Field(
        default_factory=list,
        max_length=20,
        description="Previous conversation messages"
    )


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
    rfp_agency: str | None
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
    retrieved_docs: list[Any],
    max_citations: int = 3
) -> list[Citation]:
    """Extract citations from retrieved documents."""
    citations = []
    for doc in retrieved_docs[:max_citations]:
        # Get a snippet of the content
        content = doc.content if hasattr(doc, 'content') else str(doc)
        snippet = content[:200] + "..." if len(content) > 200 else content

        citations.append(Citation(
            document_id=doc.document_id if hasattr(doc, 'document_id') else "unknown",
            content_snippet=snippet,
            source=doc.source_dataset if hasattr(doc, 'source_dataset') else "RFP Document",
            similarity_score=doc.similarity_score if hasattr(doc, 'similarity_score') else 0.0
        ))
    return citations


@router.post("/{rfp_id}/chat", response_model=ChatResponse)
async def chat_with_rfp(rfp: RFPDep, request: ChatRequest):
    """
    Chat with an RFP using AI-powered Q&A.

    Uses RAG to retrieve relevant document sections and generate
    accurate, cited responses about the RFP.
    """
    import time
    start_time = time.time()

    try:
        # Import RAG and LLM components
        from src.rag.rag_engine import RAGEngine
        from src.config.llm_adapter import create_llm_interface

        # Initialize components
        rag_engine = RAGEngine()
        llm = create_llm_interface()

        # Check if RAG index is built
        if not rag_engine.is_built:
            logger.warning("RAG index not built, attempting to build...")
            try:
                rag_engine.build_index()
            except Exception as e:
                logger.error(f"Failed to build RAG index: {e}")
                raise HTTPException(
                    status_code=503,
                    detail="RAG index not available. Please try again later."
                )

        # Enhance query with RFP context for better retrieval
        enhanced_query = f"{rfp.title} {rfp.agency or ''} {request.message}"

        # Retrieve relevant documents
        rag_context = rag_engine.generate_context(enhanced_query, k=5)

        if not rag_context.retrieved_documents:
            # Fallback response if no documents found
            return ChatResponse(
                answer="I couldn't find specific information about that in the available documents. "
                       "Try rephrasing your question or asking about a different aspect of the RFP.",
                citations=[],
                confidence=0.0,
                rfp_id=rfp.rfp_id,
                processing_time_ms=int((time.time() - start_time) * 1000)
            )

        # Build prompt with context
        prompt = build_chat_prompt(
            question=request.message,
            context=rag_context.context_text,
            history=request.history,
            rfp_title=rfp.title,
            rfp_agency=rfp.agency
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
                content = doc.content[:300] if len(doc.content) > 300 else doc.content
                answer += f"{i}. {content}\n\n"
            confidence = 0.5

        # Extract citations
        citations = extract_citations(rag_context.retrieved_documents)

        processing_time = int((time.time() - start_time) * 1000)

        return ChatResponse(
            answer=answer,
            citations=citations,
            confidence=round(confidence, 2),
            rfp_id=rfp.rfp_id,
            processing_time_ms=processing_time
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error for RFP {rfp.rfp_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process chat request: {str(e)}"
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
        specific_suggestions.append(f"What NAICS code ({rfp.naics_code}) experience is required?")

    if rfp.agency:
        specific_suggestions.append(f"What is {rfp.agency}'s evaluation process?")

    if rfp.response_deadline:
        specific_suggestions.append("What documents must be included in the submission?")

    if rfp.category:
        specific_suggestions.append(f"What are typical requirements for {rfp.category} contracts?")

    # Combine and limit
    all_suggestions = specific_suggestions + suggestions
    return {
        "rfp_id": rfp.rfp_id,
        "suggestions": all_suggestions[:10]
    }


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
        "message": ""
    }

    try:
        from src.rag.rag_engine import RAGEngine
        rag = RAGEngine()
        status["rag_status"] = "ready" if rag.is_built else "not_built"
        status["rag_documents"] = len(rag.vector_index.document_ids) if rag.is_built else 0
    except Exception as e:
        status["rag_status"] = f"error: {str(e)}"

    try:
        from src.config.llm_adapter import create_llm_interface
        llm = create_llm_interface()
        llm_status = llm.get_status()
        status["llm_status"] = "ready" if llm_status.get("current_backend") else "not_configured"
        status["llm_backend"] = llm_status.get("current_backend", "unknown")
    except Exception as e:
        status["llm_status"] = f"error: {str(e)}"

    # Determine overall availability
    status["chat_available"] = (
        status["rag_status"] == "ready" and
        status["llm_status"] == "ready"
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
