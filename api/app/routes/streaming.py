"""
Streaming API endpoints for real-time LLM responses.

Provides Server-Sent Events (SSE) endpoints for:
- Proposal section generation with streaming output
- Chat responses with RAG context
- General LLM completion streaming
"""
import logging
from typing import Annotated

from app.dependencies import DBDep
from app.services.streaming import get_streaming_service
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()


class StreamGenerateRequest(BaseModel):
    """Request for streaming section generation."""
    section_type: str = Field(
        ...,
        description="Section type: executive_summary, technical_approach, company_qualifications, management_approach, pricing_narrative"
    )
    use_thinking: bool = Field(
        default=True,
        description="Enable extended thinking mode for better quality"
    )
    thinking_budget: int = Field(
        default=10000,
        ge=1000,
        le=50000,
        description="Token budget for thinking (if enabled)"
    )


class StreamChatRequest(BaseModel):
    """Request for streaming chat response."""
    message: str = Field(..., min_length=1, max_length=2000)
    history: list[dict] = Field(
        default_factory=list,
        max_length=20,
        description="Previous messages as [{role, content}]"
    )


class StreamCompletionRequest(BaseModel):
    """Request for general streaming completion."""
    prompt: str = Field(..., min_length=1, max_length=10000)
    system_message: str | None = Field(None, max_length=5000)
    max_tokens: int = Field(default=4096, ge=100, le=16000)
    enable_thinking: bool = False
    thinking_budget: int = Field(default=10000, ge=1000, le=50000)


@router.get("/{rfp_id}/generate/{section_type}")
async def stream_section_generation(
    rfp_id: str,
    section_type: str,
    db: DBDep,
    use_thinking: Annotated[bool, Query(description="Enable thinking mode")] = True,
    thinking_budget: Annotated[int, Query(ge=1000, le=50000)] = 10000,
) -> StreamingResponse:
    """
    Stream proposal section generation for an RFP.

    Returns Server-Sent Events with the following event types:
    - start: Generation started
    - thinking_start: Thinking block started
    - thinking: Thinking content chunk
    - text_start: Text block started
    - text: Text content chunk
    - block_stop: Block completed
    - usage: Token usage update
    - complete: Generation finished
    - error: Error occurred

    Supported section types:
    - executive_summary
    - technical_approach
    - company_qualifications
    - management_approach
    - pricing_narrative
    """
    valid_sections = [
        "executive_summary",
        "technical_approach",
        "company_qualifications",
        "management_approach",
        "pricing_narrative",
        "past_performance",
        "staffing_plan",
        "quality_assurance",
        "risk_mitigation",
        "compliance_matrix",
    ]

    if section_type not in valid_sections:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid section_type. Must be one of: {', '.join(valid_sections)}"
        )

    # Verify RFP exists
    from app.models.database import RFPOpportunity
    rfp = db.query(RFPOpportunity).filter(RFPOpportunity.rfp_id == rfp_id).first()
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    streaming_service = get_streaming_service()

    return streaming_service.create_sse_response(
        streaming_service.stream_section_generation(
            rfp_id=rfp_id,
            section_type=section_type,
            db_session=db,
            use_thinking=use_thinking,
            thinking_budget=thinking_budget,
        )
    )


@router.get("/{rfp_id}/chat")
async def stream_chat_response(
    rfp_id: str,
    message: Annotated[str, Query(min_length=1, max_length=2000)],
    db: DBDep,
    history: Annotated[str | None, Query(description="JSON-encoded history")] = None,
) -> StreamingResponse:
    """
    Stream chat response for an RFP with RAG context.

    The history parameter should be a JSON-encoded array of message objects:
    [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]

    Returns Server-Sent Events with:
    - citations: Retrieved citations from RAG
    - text: Response content chunks
    - complete: Response finished
    - error: Error occurred
    """
    import json

    # Verify RFP exists
    from app.models.database import RFPOpportunity
    rfp = db.query(RFPOpportunity).filter(RFPOpportunity.rfp_id == rfp_id).first()
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    # Parse history if provided
    parsed_history = []
    if history:
        try:
            parsed_history = json.loads(history)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid history JSON format")

    streaming_service = get_streaming_service()

    return streaming_service.create_sse_response(
        streaming_service.stream_chat_response(
            rfp_id=rfp_id,
            message=message,
            history=parsed_history,
            db_session=db,
        )
    )


@router.post("/complete")
async def stream_completion(
    request: StreamCompletionRequest,
) -> StreamingResponse:
    """
    Stream a general LLM completion.

    This endpoint is for direct LLM access without RFP context.
    Useful for general text generation, refinement, or editing.

    Returns Server-Sent Events with standard streaming events.
    """
    streaming_service = get_streaming_service()

    return streaming_service.create_sse_response(
        streaming_service.stream_llm_response(
            prompt=request.prompt,
            system_message=request.system_message,
            task_type="completion",
            max_tokens=request.max_tokens,
            enable_thinking=request.enable_thinking,
            thinking_budget=request.thinking_budget,
        )
    )


@router.get("/status")
async def get_streaming_status() -> dict:
    """
    Check streaming service status.

    Returns the availability of streaming components:
    - anthropic_available: Whether Anthropic client is configured
    - rag_available: Whether RAG engine is available
    - ready: Whether streaming is fully operational
    """
    import os

    streaming_service = get_streaming_service()

    anthropic_available = bool(os.getenv("ANTHROPIC_API_KEY"))
    rag_available = False

    try:
        rag_available = streaming_service.is_rag_available()
    except Exception:
        pass

    return {
        "anthropic_available": anthropic_available,
        "rag_available": rag_available,
        "ready": anthropic_available,
        "supported_sections": [
            "executive_summary",
            "technical_approach",
            "company_qualifications",
            "management_approach",
            "pricing_narrative",
            "past_performance",
            "staffing_plan",
            "quality_assurance",
            "risk_mitigation",
            "compliance_matrix",
        ],
        "supported_events": [
            "start",
            "thinking_start",
            "thinking",
            "text_start",
            "text",
            "block_stop",
            "usage",
            "complete",
            "error",
            "citations",
        ],
    }
