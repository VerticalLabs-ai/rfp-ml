"""
Proposal generation tasks for Celery.

Handles long-running LLM generation tasks:
- Individual section generation
- Full bid document generation
"""

import asyncio
import logging
import os
import sys

from celery import shared_task

from api.app.dependencies import rfp_to_processing_dict

# Add project paths
project_root = os.path.dirname(
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    )
)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

logger = logging.getLogger(__name__)


def broadcast_progress(job_id: str, progress: int, status: str, **kwargs):
    """Broadcast job progress via WebSocket (async wrapper)."""
    try:
        from api.app.websockets.channels import broadcast_job_progress

        asyncio.run(broadcast_job_progress(job_id, progress, status, **kwargs))
    except Exception as e:
        logger.warning(f"Failed to broadcast progress: {e}")


@shared_task(
    bind=True, name="api.app.worker.tasks.generation.generate_proposal_section"
)
def generate_proposal_section(
    self, rfp_id: str, section_type: str, options: dict | None = None
) -> dict:
    """
    Generate a single proposal section.

    Args:
        rfp_id: The RFP ID to generate section for
        section_type: Type of section (executive_summary, technical_approach, etc.)
        options: Optional generation options (use_thinking, thinking_budget)

    Returns:
        Dict with generated content and metadata
    """
    job_id = self.request.id
    options = options or {}

    logger.info(
        f"Starting section generation - Job: {job_id}, RFP: {rfp_id}, Section: {section_type}"
    )

    try:
        # Update progress: Starting
        self.update_state(state="PROGRESS", meta={"progress": 0, "status": "starting"})
        broadcast_progress(job_id, 0, "starting", section_type=section_type)

        # Get database session
        from api.app.core.database import SessionLocal
        from api.app.models.database import CompanyProfile, RFPOpportunity

        with SessionLocal() as db:
            # Load RFP
            rfp = (
                db.query(RFPOpportunity).filter(RFPOpportunity.rfp_id == rfp_id).first()
            )

            if not rfp:
                return {
                    "status": "error",
                    "error": f"RFP not found: {rfp_id}",
                    "section_type": section_type,
                }

            self.update_state(
                state="PROGRESS", meta={"progress": 10, "status": "loaded_rfp"}
            )
            broadcast_progress(job_id, 10, "loaded_rfp")

            # Load company profile
            profile = db.query(CompanyProfile).first()

            rfp_data = {
                "title": rfp.title,
                "agency": rfp.agency,
                "description": rfp.description or "",
                "naics_code": rfp.naics_code or "",
                "award_amount": rfp.award_amount or 0,
            }

            company_profile = {}
            if profile:
                company_profile = {
                    "company_name": profile.name,
                    "certifications": profile.certifications or [],
                    "core_competencies": profile.core_competencies or [],
                }

            self.update_state(
                state="PROGRESS", meta={"progress": 20, "status": "loaded_profile"}
            )
            broadcast_progress(job_id, 20, "loaded_profile")

            # Get RAG context
            rag_context = ""
            try:
                from src.rag.chroma_rag_engine import get_rag_engine

                rag = get_rag_engine()
                if rag and rag.is_built and rag.collection.count() > 0:
                    results = rag.retrieve(f"{rfp.title} {section_type}", top_k=3)
                    for result in results:
                        rag_context += f"\n{result.get('content', '')[:500]}"
            except Exception as e:
                logger.warning(f"RAG retrieval failed: {e}")

            self.update_state(
                state="PROGRESS", meta={"progress": 30, "status": "generating"}
            )
            broadcast_progress(job_id, 30, "generating")

            # Generate section using Claude LLM Manager
            from src.config.claude_llm_config import ClaudeLLMManager, ClaudeModel

            manager = ClaudeLLMManager()

            # Model selection: default to Haiku, options: haiku, sonnet, opus
            model_name = options.get("model", "haiku").lower()
            model_map = {
                "haiku": ClaudeModel.HAIKU_4_5,
                "sonnet": ClaudeModel.SONNET_4_5,
                "opus": ClaudeModel.OPUS_4_5,
            }
            selected_model = model_map.get(model_name, ClaudeModel.HAIKU_4_5)

            # Thinking mode: default False, only supported on Sonnet/Opus
            use_thinking = options.get("use_thinking", False)

            # Haiku doesn't support extended thinking
            if selected_model == ClaudeModel.HAIKU_4_5 and use_thinking:
                logger.info("Thinking mode not supported for Haiku, disabling")
                use_thinking = False

            use_opus = selected_model == ClaudeModel.OPUS_4_5

            result = manager.generate_comprehensive_proposal_section(
                section_type=section_type,
                rfp_data=rfp_data,
                company_profile=company_profile,
                rag_context=rag_context,
                enable_thinking=use_thinking,
                use_opus=use_opus,
            )

            self.update_state(
                state="PROGRESS", meta={"progress": 90, "status": "completed"}
            )
            broadcast_progress(job_id, 90, "completing")

            if result["status"] == "success":
                # Store result in RFP (optional)
                # Could save to bid_document or proposal_sections

                self.update_state(
                    state="PROGRESS", meta={"progress": 100, "status": "completed"}
                )
                broadcast_progress(job_id, 100, "completed")

                return {
                    "status": "success",
                    "section_type": section_type,
                    "content": result["content"],
                    "word_count": result.get("word_count", 0),
                    "model": result.get("model"),
                    "usage": result.get("usage"),
                    "thinking_enabled": result.get("thinking_enabled"),
                }
            else:
                return {
                    "status": "error",
                    "error": result.get("error", "Generation failed"),
                    "section_type": section_type,
                }

    except Exception as e:
        logger.error(f"Section generation failed: {e}")
        broadcast_progress(job_id, 0, "failed", error=str(e))
        return {"status": "error", "error": str(e), "section_type": section_type}


@shared_task(bind=True, name="api.app.worker.tasks.generation.generate_full_bid")
def generate_full_bid(
    self,
    rfp_id: str,
    generation_mode: str = "claude_enhanced",
    options: dict | None = None,
) -> dict:
    """
    Generate a complete bid document.

    Args:
        rfp_id: The RFP ID
        generation_mode: Mode (template, claude_standard, claude_enhanced, claude_premium)
        options: Additional options

    Returns:
        Dict with bid document and metadata
    """
    job_id = self.request.id
    options = options or {}

    logger.info(
        f"Starting full bid generation - Job: {job_id}, RFP: {rfp_id}, Mode: {generation_mode}"
    )

    try:
        self.update_state(state="PROGRESS", meta={"progress": 0, "status": "starting"})
        broadcast_progress(job_id, 0, "starting")

        # Get database session
        from api.app.core.database import SessionLocal
        from api.app.models.database import RFPOpportunity

        with SessionLocal() as db:
            rfp = (
                db.query(RFPOpportunity).filter(RFPOpportunity.rfp_id == rfp_id).first()
            )

            if not rfp:
                return {"status": "error", "error": f"RFP not found: {rfp_id}"}

            self.update_state(
                state="PROGRESS", meta={"progress": 10, "status": "loaded_rfp"}
            )
            broadcast_progress(job_id, 10, "loaded_rfp")

            # Use existing processor
            from api.app.services.rfp_processor import processor

            self.update_state(
                state="PROGRESS", meta={"progress": 20, "status": "generating"}
            )
            broadcast_progress(job_id, 20, "generating")

            # Determine mode
            thinking_budget = options.get("thinking_budget", 10000)

            # Generate using existing processor
            result = processor.generate_bid_document(
                rfp_data=rfp_to_processing_dict(rfp),
                generation_mode=generation_mode,
                thinking_budget=thinking_budget,
            )

            self.update_state(
                state="PROGRESS", meta={"progress": 90, "status": "completing"}
            )
            broadcast_progress(job_id, 90, "completing")

            if result and result.get("content"):
                self.update_state(
                    state="PROGRESS", meta={"progress": 100, "status": "completed"}
                )
                broadcast_progress(job_id, 100, "completed")

                return {
                    "status": "success",
                    "bid_document_id": result.get("bid_document_id"),
                    "content": result.get("content"),
                    "metadata": result.get("metadata"),
                }
            else:
                return {"status": "error", "error": "Bid generation failed"}

    except Exception as e:
        logger.error(f"Full bid generation failed: {e}")
        broadcast_progress(job_id, 0, "failed", error=str(e))
        return {"status": "error", "error": str(e)}
