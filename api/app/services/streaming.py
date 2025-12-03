"""
Streaming Service Layer for LLM responses and real-time data.

Provides Server-Sent Events (SSE) streaming for:
- LLM text generation (Claude)
- RAG context retrieval
- Chat responses
"""

import json
import logging
import os
import sys
from collections.abc import AsyncGenerator
from typing import Any

from fastapi.responses import StreamingResponse

from src.config.claude_llm_config import ClaudeModel

# Add project root to path for imports
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

logger = logging.getLogger(__name__)


class StreamingService:
    """
    Service for streaming LLM responses and real-time data via SSE.

    Uses the Anthropic streaming API for Claude models and integrates
    with the existing RAG engine for context retrieval.
    """

    def __init__(self):
        self._client = None
        self._rag_engine = None
        self._initialize_components()

    def _initialize_components(self):
        """Initialize Anthropic client and RAG engine lazily."""
        # Client initialized on first use to avoid import issues
        pass

    def _get_anthropic_client(self):
        """Get or create async Anthropic client for non-blocking I/O."""
        if self._client is None:
            try:
                import anthropic

                api_key = os.getenv("ANTHROPIC_API_KEY")
                if api_key:
                    self._client = anthropic.AsyncAnthropic(api_key=api_key)
                    logger.info("Async Anthropic client initialized for streaming")
                else:
                    logger.warning("ANTHROPIC_API_KEY not set")
            except ImportError:
                logger.error("anthropic package not installed")
        return self._client

    def _get_rag_engine(self):
        """Get ChromaDB RAG engine singleton."""
        if self._rag_engine is None:
            try:
                from src.rag.chroma_rag_engine import get_rag_engine

                self._rag_engine = get_rag_engine()
                stats = self._rag_engine.get_statistics()
                logger.info(f"RAG engine ready: {stats['total_documents']} documents")
            except Exception as e:
                logger.error(f"Failed to initialize RAG engine: {e}")
        return self._rag_engine

    async def stream_llm_response(
        self,
        prompt: str,
        system_message: str | None = None,
        task_type: str = "generation",
        model: str = ClaudeModel.HAIKU_4_5.value,
        max_tokens: int = 16000,
        enable_thinking: bool = False,
        thinking_budget: int = 10000,
    ) -> AsyncGenerator[str, None]:
        """
        Stream LLM response chunks via SSE format.

        Args:
            prompt: The user prompt
            system_message: Optional system message for context
            task_type: Type of task (generation, chat, etc.)
            model: Claude model to use
            max_tokens: Maximum tokens in response
            enable_thinking: Enable extended thinking mode
            thinking_budget: Tokens allocated for thinking

        Yields:
            SSE-formatted data chunks
        """
        client = self._get_anthropic_client()
        if not client:
            yield self._format_sse_event(
                "error", {"error": "Anthropic client not available"}
            )
            return

        # Build messages
        messages = [{"role": "user", "content": prompt}]

        # Build API parameters
        api_params = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages,
        }

        if system_message:
            api_params["system"] = system_message

        # Add thinking if enabled
        if enable_thinking:
            api_params["thinking"] = {
                "type": "enabled",
                "budget_tokens": thinking_budget,
            }

        try:
            # Send start event
            yield self._format_sse_event(
                "start",
                {
                    "task_type": task_type,
                    "model": model,
                    "thinking_enabled": enable_thinking,
                },
            )

            # Stream response using async client for non-blocking I/O
            async with client.messages.stream(**api_params) as stream:
                async for event in stream:
                    if hasattr(event, "type"):
                        if event.type == "content_block_start":
                            if hasattr(event, "content_block"):
                                block = event.content_block
                                if hasattr(block, "type"):
                                    if block.type == "thinking":
                                        yield self._format_sse_event(
                                            "thinking_start", {}
                                        )
                                    elif block.type == "text":
                                        yield self._format_sse_event("text_start", {})

                        elif event.type == "content_block_delta":
                            if hasattr(event, "delta"):
                                delta = event.delta
                                if hasattr(delta, "type"):
                                    if delta.type == "thinking_delta":
                                        yield self._format_sse_event(
                                            "thinking", {"content": delta.thinking}
                                        )
                                    elif delta.type == "text_delta":
                                        yield self._format_sse_event(
                                            "text", {"content": delta.text}
                                        )

                        elif event.type == "content_block_stop":
                            yield self._format_sse_event("block_stop", {})

                        elif event.type == "message_delta":
                            if hasattr(event, "usage"):
                                yield self._format_sse_event(
                                    "usage",
                                    {"output_tokens": event.usage.output_tokens},
                                )

                        elif event.type == "message_start":
                            if hasattr(event, "message") and hasattr(
                                event.message, "usage"
                            ):
                                yield self._format_sse_event(
                                    "usage",
                                    {"input_tokens": event.message.usage.input_tokens},
                                )

            # Send complete event
            yield self._format_sse_event("complete", {"status": "success"})

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield self._format_sse_event("error", {"error": str(e)})

    async def stream_chat_response(
        self,
        rfp_id: str,
        message: str,
        history: list[dict] | None = None,
        db_session: Any | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat response with RAG context.

        Args:
            rfp_id: The RFP ID for context
            message: User message
            history: Optional conversation history
            db_session: Database session for RFP lookup

        Yields:
            SSE-formatted data chunks
        """
        # Get RFP context
        rfp_context = ""
        if db_session:
            from app.models.database import RFPOpportunity

            rfp = (
                db_session.query(RFPOpportunity)
                .filter(RFPOpportunity.rfp_id == rfp_id)
                .first()
            )
            if rfp:
                rfp_context = f"RFP: {rfp.title}\nAgency: {rfp.agency}\nDescription: {rfp.description or ''}"

        # Get RAG context
        rag_context = ""
        citations = []
        rag_engine = self._get_rag_engine()
        if rag_engine and rag_engine.is_built:
            try:
                enhanced_query = f"{rfp_context[:500]} {message}"
                results = rag_engine.retrieve(enhanced_query, k=5)
                for i, result in enumerate(results):
                    rag_context += f"\n\nContext { i + 1 }:\n{result.get('content', result.get('text', ''))}"
                    citations.append(
                        {
                            "index": i,
                            "content": result.get("content", result.get("text", ""))[
                                :200
                            ],
                            "similarity": result.get(
                                "similarity_score", result.get("score", 0)
                            ),
                        }
                    )
            except Exception as e:
                logger.warning(f"RAG retrieval failed: {e}")

        # Build conversation
        history_text = ""
        if history:
            for msg in history[-5:]:  # Last 5 messages
                role = msg.get("role", "user")
                content = msg.get("content", "")
                history_text += f"\n{role.upper()}: {content}"

        # Build prompt
        system_message = """You are an AI assistant helping with government RFP (Request for Proposal) analysis.
Answer questions based on the provided RFP context and retrieved information.
Be concise, accurate, and cite specific parts of the RFP when relevant.
If you're not sure about something, say so."""

        prompt = f"""RFP Context:
{rfp_context}

Retrieved Information:
{rag_context}

{f'Conversation History:{history_text}' if history_text else ''}

User Question: {message}

Please provide a helpful response:"""

        # Send citations first
        yield self._format_sse_event("citations", {"citations": citations})

        # Stream the response
        async for chunk in self.stream_llm_response(
            prompt=prompt,
            system_message=system_message,
            task_type="chat",
            max_tokens=2000,
            enable_thinking=False,
        ):
            yield chunk

    async def stream_section_generation(
        self,
        rfp_id: str,
        section_type: str,
        db_session: Any | None = None,
        use_thinking: bool = False,
        thinking_budget: int = 10000,
        model: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream proposal section generation with full RFP context.

        Args:
            rfp_id: The RFP ID
            section_type: Type of section (executive_summary, technical_approach, etc.)
            db_session: Database session
            use_thinking: Enable thinking mode (only available for Sonnet/Opus)
            thinking_budget: Tokens for thinking
            model: Claude model to use (haiku, sonnet, opus). Defaults to Haiku.

        Yields:
            SSE-formatted data chunks
        """
        # Default to Haiku if no model specified
        if model is None:
            model = ClaudeModel.HAIKU_4_5.value

        # Haiku doesn't support extended thinking - auto-disable if Haiku selected
        is_haiku = "haiku" in model.lower()
        if is_haiku and use_thinking:
            logger.info("Thinking mode not supported for Haiku, disabling")
            use_thinking = False

        # Get RFP, company profile, Q&A, and documents
        rfp_data = {}
        company_profile = {}
        qa_context = ""
        document_context = ""
        rfp_db_id = None

        logger.info(
            f"stream_section_generation: rfp_id={rfp_id}, section={section_type}"
        )

        if db_session:
            from app.models.database import (
                CompanyProfile,
                RFPDocument,
                RFPOpportunity,
                RFPQandA,
            )

            # Get RFP data
            rfp = (
                db_session.query(RFPOpportunity)
                .filter(RFPOpportunity.rfp_id == rfp_id)
                .first()
            )
            if rfp:
                rfp_db_id = rfp.id
                rfp_data = {
                    "title": rfp.title,
                    "agency": rfp.agency,
                    "description": rfp.description or "",
                    "naics_code": rfp.naics_code or "",
                    "award_amount": rfp.award_amount or 0,
                    "estimated_value": rfp.estimated_value or 0,
                    "rfp_number": rfp.rfp_id or rfp_id,
                    "solicitation_number": rfp.solicitation_number or "",
                    "response_deadline": (
                        rfp.response_deadline.strftime("%B %d, %Y")
                        if rfp.response_deadline
                        else "Not specified"
                    ),
                    "category": rfp.category or "",
                }

            # Get enhanced company profile
            profile = db_session.query(CompanyProfile).first()
            if profile:
                company_profile = {
                    "company_name": profile.name,
                    "legal_name": profile.legal_name or profile.name,
                    "certifications": profile.certifications or [],
                    "naics_codes": profile.naics_codes or [],
                    "core_competencies": profile.core_competencies or [],
                    "established_year": profile.established_year,
                    "employee_count": profile.employee_count or "Not specified",
                    "past_performance": profile.past_performance or [],
                    "uei": profile.uei or "",
                    "cage_code": profile.cage_code or "",
                    "headquarters": profile.headquarters or "",
                }

            # Get Q&A context - filter by section relevance if available
            if rfp_db_id:
                qa_items = (
                    db_session.query(RFPQandA)
                    .filter(RFPQandA.rfp_id == rfp_db_id)
                    .all()
                )
                logger.info(f"Q&A loaded: {len(qa_items)} items for rfp_id={rfp_db_id}")
                if qa_items:
                    # Build Q&A context, prioritizing section-relevant items
                    relevant_qa = []
                    other_qa = []
                    for qa in qa_items:
                        related = qa.related_sections or []
                        if (
                            section_type in related
                            or qa.category == section_type.replace("_", " ")
                        ):
                            relevant_qa.append(qa)
                        else:
                            other_qa.append(qa)

                    # Combine: relevant first, then others (limit total)
                    prioritized_qa = (
                        relevant_qa[:10] + other_qa[: max(0, 15 - len(relevant_qa))]
                    )

                    if prioritized_qa:
                        qa_lines = []
                        for qa in prioritized_qa:
                            q = qa.question_text[:300] if qa.question_text else ""
                            a = (
                                qa.answer_text[:500]
                                if qa.answer_text
                                else "No answer provided"
                            )
                            category = f" [{qa.category}]" if qa.category else ""
                            qa_lines.append(
                                f"**Q{qa.question_number or ''}:{category}** {q}\n**A:** {a}"
                            )
                        qa_context = "\n\n".join(qa_lines)
                        logger.info(
                            f"Q&A context: {len(prioritized_qa)} items, {len(qa_context)} chars"
                        )

            # Get document content
            if rfp_db_id:
                try:
                    from src.utils.document_reader import extract_all_document_content

                    docs = (
                        db_session.query(RFPDocument)
                        .filter(RFPDocument.rfp_id == rfp_db_id)
                        .all()
                    )
                    if docs:
                        # Filter to documents with file_path (downloaded files)
                        docs_for_extraction = [
                            {
                                "file_path": doc.file_path,
                                "filename": doc.filename,
                                "document_type": doc.document_type,
                            }
                            for doc in docs
                            if doc.file_path
                        ]

                        # Log document status
                        docs_without_path = [d for d in docs if not d.file_path]
                        if docs_without_path:
                            logger.warning(
                                f"Documents not downloaded: {[d.filename for d in docs_without_path]}. "
                                "Use 'Refresh' to download."
                            )

                        if docs_for_extraction:
                            logger.info(
                                f"Extracting content from {len(docs_for_extraction)} documents"
                            )
                            extracted = extract_all_document_content(
                                docs_for_extraction
                            )
                            if extracted.get("documents"):
                                doc_parts = []
                                for doc_info in extracted["documents"][
                                    :3
                                ]:  # Limit to 3 docs
                                    doc_name = doc_info.get("filename", "Document")
                                    doc_text = doc_info.get("content", "")[
                                        :2000
                                    ]  # Limit each doc
                                    if doc_text:
                                        doc_parts.append(f"### {doc_name}\n{doc_text}")
                                document_context = "\n\n".join(doc_parts)
                                logger.info(
                                    f"Document context: {len(doc_parts)} docs, {len(document_context)} chars"
                                )
                except Exception as e:
                    logger.warning(f"Document extraction failed: {e}")

        # Get RAG context
        rag_context = ""
        rag_engine = self._get_rag_engine()
        if rag_engine and rag_engine.is_built and rfp_data.get("title"):
            try:
                results = rag_engine.retrieve(
                    f"{rfp_data['title']} {section_type}", k=3
                )
                for result in results:
                    rag_context += (
                        f"\n{result.get('content', result.get('text', ''))[:500]}"
                    )
            except Exception as e:
                logger.warning(f"RAG retrieval failed: {e}")

        # Build section generation prompt using Claude LLM config patterns for instructions
        section_instructions = self._get_section_instructions(section_type)

        # Format company credentials
        certs_str = ", ".join(company_profile.get("certifications", [])) or "N/A"
        naics_str = ", ".join(company_profile.get("naics_codes", [])) or "N/A"
        competencies_str = (
            ", ".join(company_profile.get("core_competencies", [])[:8]) or "N/A"
        )

        # Format past performance summary
        past_perf_str = ""
        past_perf = company_profile.get("past_performance", [])
        if past_perf and isinstance(past_perf, list):
            perf_items = []
            for p in past_perf[:5]:
                if isinstance(p, dict):
                    perf_items.append(
                        f"- {p.get('client', 'Client')}: {p.get('description', p.get('project', ''))[:100]}"
                    )
                elif isinstance(p, str):
                    perf_items.append(f"- {p[:100]}")
            past_perf_str = "\n".join(perf_items) if perf_items else "N/A"
        else:
            past_perf_str = "N/A"

        system_message = f"""You are an expert government contracting proposal writer.
You specialize in writing compelling, compliant, and comprehensive {section_type.replace('_', ' ')} sections.
Write in a professional, confident tone appropriate for government contracting.
Be specific and detailed - use the provided Q&A, company credentials, and document content.
Reference specific requirements from the RFP documents and Q&A when relevant."""

        prompt = f"""
## RFP Information
- **Title:** {rfp_data.get('title', 'Government Contract')}
- **RFP/Solicitation Number:** {rfp_data.get('rfp_number', rfp_id)} / {rfp_data.get('solicitation_number', 'N/A')}
- **Agency:** {rfp_data.get('agency', 'Government Agency')}
- **NAICS Code:** {rfp_data.get('naics_code', 'N/A')}
- **Category:** {rfp_data.get('category', 'N/A')}
- **Estimated Value:** ${rfp_data.get('estimated_value', 0):,.2f}
- **Response Deadline:** {rfp_data.get('response_deadline', 'Not specified')}

### RFP Description
{rfp_data.get('description', 'No description available.')[:3000]}

---

## Company Information
- **Company Name:** {company_profile.get('company_name', 'Our Company')}
- **Legal Name:** {company_profile.get('legal_name', 'N/A')}
- **Established:** {company_profile.get('established_year', 'N/A')}
- **Employee Count:** {company_profile.get('employee_count', 'N/A')}
- **Headquarters:** {company_profile.get('headquarters', 'N/A')}
- **UEI:** {company_profile.get('uei', 'N/A')}
- **CAGE Code:** {company_profile.get('cage_code', 'N/A')}
- **Certifications:** {certs_str}
- **NAICS Codes:** {naics_str}
- **Core Competencies:** {competencies_str}

### Past Performance Summary
{past_perf_str}

---

## RFP Q&A (Requirements & Clarifications)
{qa_context if qa_context else 'No Q&A available for this RFP.'}

---

## RFP Document Excerpts
{document_context[:4000] if document_context else 'No document content available.'}

---

## Historical Context (Similar Proposals)
{rag_context[:1000] if rag_context else 'No historical context available.'}

---

# Task: Generate {section_type.replace('_', ' ').title()} Section

{section_instructions}

**Important:** Use the Q&A responses to address specific requirements. Reference company certifications and past performance where relevant. Be specific to THIS RFP - avoid generic content.

Generate the {section_type.replace('_', ' ')} section now:
"""

        # Stream generation
        # max_tokens must be > thinking_budget for extended thinking to work
        effective_max_tokens = max(16000, thinking_budget + 6000)
        async for chunk in self.stream_llm_response(
            prompt=prompt,
            system_message=system_message,
            task_type=section_type,
            model=model,
            max_tokens=effective_max_tokens,
            enable_thinking=use_thinking,
            thinking_budget=thinking_budget,
        ):
            yield chunk

    def _get_section_instructions(self, section_type: str) -> str:
        """Get instructions for specific section types."""
        instructions = {
            "executive_summary": """Generate a compelling executive summary that:
- Opens with understanding of the agency's needs
- Summarizes key qualifications
- Highlights competitive advantages
- Provides clear value statement
- Closes with commitment to successful delivery""",
            "technical_approach": """Generate a detailed technical approach that:
- Describes methodology to meet requirements
- Outlines processes and workflows
- Details quality assurance measures
- Explains project management approach
- Addresses risk management
- Includes implementation timeline""",
            "company_qualifications": """Generate company qualifications that:
- Details relevant experience and track record
- Highlights past performance on similar contracts
- Lists certifications and credentials
- Demonstrates organizational capabilities
- Showcases team expertise""",
            "management_approach": """Generate a management approach that:
- Describes organizational structure
- Details key personnel qualifications
- Explains communication procedures
- Outlines quality management system
- Details continuous improvement processes""",
            "pricing_narrative": """Generate a pricing narrative that:
- Explains pricing methodology
- Justifies proposed pricing
- Demonstrates cost efficiency
- Highlights cost control measures
- Shows sustainable delivery""",
            "past_performance": """Generate a past performance section that:
- Details 3-5 relevant contract examples
- Highlights successful outcomes and metrics
- Demonstrates experience with similar scope/size
- Shows consistent track record of on-time, on-budget delivery
- Includes client references where appropriate""",
            "staffing_plan": """Generate a staffing plan that:
- Identifies key personnel and their roles
- Describes qualifications and experience of team members
- Shows organizational structure and reporting relationships
- Demonstrates capability to scale as needed
- Addresses succession planning and knowledge transfer""",
            "quality_assurance": """Generate a quality assurance section that:
- Describes QA/QC processes and procedures
- Details inspection and testing methods
- Outlines quality metrics and reporting
- Shows continuous improvement approach
- Demonstrates ISO or industry certifications""",
            "risk_mitigation": """Generate a risk mitigation section that:
- Identifies potential risks (technical, schedule, cost, performance)
- Assesses probability and impact of each risk
- Describes specific mitigation strategies
- Outlines contingency plans
- Shows proactive risk management approach""",
            "compliance_matrix": """Generate a compliance matrix that:
- Maps all RFP requirements to proposed solutions
- Demonstrates full compliance with mandatory requirements
- Explains approach for each requirement
- Identifies any exceptions or deviations
- Cross-references to detailed proposal sections""",
        }
        return instructions.get(
            section_type,
            f"""
Generate a comprehensive {section_type.replace('_', ' ')} section that:
- Addresses all relevant requirements
- Demonstrates capabilities and qualifications
- Uses professional government contracting language
- Is persuasive and compelling
""",
        )

    def _format_sse_event(self, event_type: str, data: dict) -> str:
        """Format data as SSE event."""
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

    def is_rag_available(self) -> bool:
        """Check if RAG engine is available and built. Public API method."""
        rag_engine = self._get_rag_engine()
        return rag_engine is not None and getattr(rag_engine, "is_built", False)

    def create_sse_response(
        self, generator: AsyncGenerator, media_type: str = "text/event-stream"
    ) -> StreamingResponse:
        """
        Wrap async generator in FastAPI StreamingResponse.

        Args:
            generator: Async generator yielding SSE events
            media_type: Content type (default: text/event-stream)

        Returns:
            FastAPI StreamingResponse configured for SSE
        """
        return StreamingResponse(
            generator,
            media_type=media_type,
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            },
        )


# Singleton instance
_streaming_service: StreamingService | None = None


def get_streaming_service() -> StreamingService:
    """Get or create streaming service singleton."""
    global _streaming_service
    if _streaming_service is None:
        _streaming_service = StreamingService()
    return _streaming_service
