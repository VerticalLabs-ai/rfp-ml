"""
RFP management API endpoints.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.dependencies import DBDep, RFPDep, RFPServiceDep, rfp_to_processing_dict
from app.models.database import (
    BidDocument,
    PipelineStage,
    PostAwardChecklist,
    RFPDocument,
    RFPOpportunity,
)
from app.services.rfp_processor import processing_jobs, processor
from app.services.rfp_service import RFPService
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from src.agents.competitor_analytics import CompetitorAnalyticsService
from src.pricing.pricing_engine import ScenarioParams
from src.utils.document_reader import extract_all_document_content

logger = logging.getLogger(__name__)


router = APIRouter()

# Lazy-loaded service
_competitor_service = None


def get_competitor_service():
    """Get or create competitor service instance."""
    global _competitor_service
    if _competitor_service is None:
        _competitor_service = CompetitorAnalyticsService()
    return _competitor_service


def save_proposal_sections_to_db(
    rfp_id: int, rfp_id_str: str, bid_document_data: dict, db: Session
) -> None:
    """
    Parse and save proposal sections to database for Proposal Copilot.

    Args:
        rfp_id: Database ID of the RFP
        rfp_id_str: String RFP ID (e.g., "RFP-20251202...")
        bid_document_data: The generated bid document dict
        db: Database session
    """
    import re
    from datetime import datetime, timezone

    try:
        # Get sections from the generated content
        sections = bid_document_data.get("content", {}).get("sections", {})
        markdown_content = bid_document_data.get("content", {}).get("markdown", "")

        # Map of section headers to section IDs
        section_patterns = {
            "executive_summary": r"##\s*Executive\s+Summary\s*\n(.*?)(?=\n##|\Z)",
            "technical_approach": r"##\s*Technical\s+Approach\s*\n(.*?)(?=\n##|\Z)",
            "management_approach": r"##\s*Management\s+Approach\s*\n(.*?)(?=\n##|\Z)",
            "past_performance": r"##\s*Past\s+Performance\s*\n(.*?)(?=\n##|\Z)",
            "staffing_plan": r"##\s*Staffing\s+Plan\s*\n(.*?)(?=\n##|\Z)",
            "quality_assurance": r"##\s*Quality\s+Assurance\s*\n(.*?)(?=\n##|\Z)",
            "risk_mitigation": r"##\s*Risk\s+Mitigation\s*\n(.*?)(?=\n##|\Z)",
            "compliance_matrix": r"##\s*Compliance\s+Matrix\s*\n(.*?)(?=\n##|\Z)",
            "pricing": r"##\s*(?:Pricing|Cost)\s*(?:Proposal|Summary|Breakdown)?\s*\n(.*?)(?=\n##|\Z)",
        }

        # Parse sections from markdown if not already in sections dict
        for section_id, pattern in section_patterns.items():
            if section_id not in sections or not sections[section_id]:
                match = re.search(pattern, markdown_content, re.IGNORECASE | re.DOTALL)
                if match:
                    sections[section_id] = match.group(1).strip()

        # Ensure all sections are strings (not dicts)
        for section_id, content in list(sections.items()):
            if isinstance(content, dict):
                # Convert dict to formatted string based on section type
                if section_id == "technical_approach":
                    parts = []
                    if "methodology" in content:
                        parts.append(f"**Methodology:** {content['methodology']}")
                    if "deliverables" in content:
                        deliverables = content.get("deliverables", [])
                        if deliverables:
                            parts.append(
                                f"**Deliverables:** {', '.join(deliverables) if isinstance(deliverables, list) else deliverables}"
                            )
                    if "timeline" in content:
                        parts.append(f"**Timeline:** {content['timeline']}")
                    sections[section_id] = "\n\n".join(parts) if parts else str(content)

                elif section_id == "pricing":
                    parts = []
                    if "recommended_price" in content:
                        parts.append(
                            f"**Recommended Price:** ${content['recommended_price']:,.2f}"
                            if isinstance(content["recommended_price"], (int, float))
                            else f"**Recommended Price:** {content['recommended_price']}"
                        )
                    if "pricing_strategies" in content:
                        strategies = content.get("pricing_strategies", [])
                        if strategies:
                            parts.append("**Pricing Strategies:**")
                            for s in strategies[:5]:
                                if isinstance(s, dict):
                                    parts.append(
                                        f"- {s.get('strategy', s.get('name', str(s)))}"
                                    )
                                else:
                                    parts.append(f"- {s}")
                    sections[section_id] = "\n".join(parts) if parts else str(content)

                elif section_id == "compliance_matrix":
                    # Already handled below, but keep as fallback
                    import json

                    sections[section_id] = json.dumps(content, indent=2)

                else:
                    # Generic dict to string conversion
                    import json

                    sections[section_id] = json.dumps(content, indent=2)

        # Ensure compliance_matrix is a string for storage (detailed handling)
        if "compliance_matrix" in sections and isinstance(
            sections["compliance_matrix"], dict
        ):
            # Convert dict compliance matrix to readable text
            cm = sections["compliance_matrix"]
            if "requirements_and_responses" in cm:
                lines = [
                    "| Requirement | Response | Status |",
                    "|-------------|----------|--------|",
                ]
                for item in cm.get("requirements_and_responses", []):
                    req = item.get("requirement", "")[:50]
                    resp = item.get("response", "")[:50]
                    status = item.get("compliance_status", "")
                    lines.append(f"| {req} | {resp} | {status} |")
                sections["compliance_matrix"] = "\n".join(lines)

        # Check if BidDocument exists for this RFP
        existing = db.query(BidDocument).filter(BidDocument.rfp_id == rfp_id).first()

        if existing:
            # Replace sections entirely with new generated content
            # (old sections may have dict format that causes validation errors)
            existing.content_json = {"sections": sections}
            existing.updated_at = datetime.now(timezone.utc)
            existing.status = "generated"
        else:
            # Create new BidDocument
            bid_doc = BidDocument(
                rfp_id=rfp_id,
                document_id=bid_document_data.get("bid_id", f"bid-{uuid4().hex[:8]}"),
                content_json={"sections": sections},
                status="generated",
            )
            db.add(bid_doc)

        db.commit()
        logger.info("Saved %d proposal sections for RFP %s", len(sections), rfp_id_str)

    except Exception as e:
        logger.exception(
            "Failed to save proposal sections for RFP %s: %s", rfp_id_str, e
        )
        db.rollback()


# Pydantic schemas
class DiscoveryParams(BaseModel):
    limit: int = 50
    days_back: int = 30

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v: int) -> int:
        if v < 1 or v > 500:
            raise ValueError("limit must be between 1 and 500")
        return v

    @field_validator("days_back")
    @classmethod
    def validate_days_back(cls, v: int) -> int:
        if v < 1 or v > 365:
            raise ValueError("days_back must be between 1 and 365")
        return v


# Module-level default instance for DiscoveryParams
_DEFAULT_DISCOVERY_PARAMS = DiscoveryParams()


class ScenarioInput(BaseModel):
    """Input for pricing scenario simulation."""

    labor_cost_multiplier: float = 1.0
    material_cost_multiplier: float = 1.0
    risk_contingency_percent: float = 0.0
    desired_margin: float = 0.0


class RFPBase(BaseModel):
    solicitation_number: str | None = None
    title: str
    description: str | None = None
    agency: str | None = None
    office: str | None = None
    naics_code: str | None = None
    category: str | None = None
    response_deadline: datetime | None = None


class RFPCreate(RFPBase):
    rfp_id: str


class RFPResponse(RFPBase):
    id: int
    rfp_id: str
    current_stage: PipelineStage
    triage_score: float | None = None
    overall_score: float | None = None
    decision_recommendation: str | None = None
    discovered_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RFPUpdate(BaseModel):
    current_stage: PipelineStage | None = None
    assigned_to: str | None = None
    priority: int | None = None


class TriageDecision(BaseModel):
    decision: str  # approve, reject, flag
    notes: str | None = None


class ManualRFPSubmit(BaseModel):
    """Schema for manually submitting an RFP for processing."""

    title: str
    agency: str | None = None
    solicitation_number: str | None = None
    description: str | None = None
    url: str | None = None
    award_amount: float | None = None
    response_deadline: datetime | None = None
    category: str | None = "general"


class BidGenerationOptions(BaseModel):
    """Options for bid document generation with Claude 4.5 support."""

    generation_mode: str = (
        "template"  # template, claude_standard, claude_enhanced, claude_premium
    )
    enable_thinking: bool = True  # Enable Claude's extended thinking mode
    thinking_budget: int = 10000  # Token budget for thinking (higher = more thorough)

    @field_validator("generation_mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        valid_modes = [
            "template",
            "claude_standard",
            "claude_enhanced",
            "claude_premium",
        ]
        if v.lower() not in valid_modes:
            raise ValueError(f"generation_mode must be one of: {valid_modes}")
        return v.lower()

    @field_validator("thinking_budget")
    @classmethod
    def validate_thinking_budget(cls, v: int) -> int:
        if v < 1000 or v > 50000:
            raise ValueError("thinking_budget must be between 1000 and 50000")
        return v


class ChecklistItemResponse(BaseModel):
    id: str
    description: str
    status: str
    assigned_to: str | None
    due_date: datetime | None
    notes: str | None
    meta: dict[str, Any]


class PostAwardChecklistResponse(BaseModel):
    id: int
    rfp_id: int
    bid_document_id: str | None
    generated_at: datetime
    status: str
    items: list[ChecklistItemResponse]
    summary: dict[str, Any]

    class Config:
        from_attributes = True


@router.get("/discovered", response_model=list[RFPResponse])
async def get_discovered_rfps(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    category: str | None = None,
    min_score: float | None = Query(default=None, ge=0.0, le=100.0),
    search: str | None = Query(
        default=None,
        description="Search term for title, description, agency, NAICS code",
    ),
    sort_by: str = Query(
        default="score", description="Sort by: score, deadline, or recent"
    ),
    db: DBDep = ...,
):
    """Get list of discovered RFPs with search and filtering."""
    service = RFPService(db)
    rfps = service.get_discovered_rfps(
        skip=skip,
        limit=limit,
        category=category,
        min_score=min_score,
        search=search,
        sort_by=sort_by,
    )
    return rfps


@router.get("/recent", response_model=list[RFPResponse])
async def get_recent_rfps(limit: int = Query(default=10, le=50), db: DBDep = ...):
    """Get recently discovered RFPs."""
    query = (
        db.query(RFPOpportunity)
        .order_by(RFPOpportunity.discovered_at.desc())
        .limit(limit)
    )
    return query.all()


@router.get("/stats/overview")
async def get_rfp_stats(db: DBDep):
    """Get overview statistics for RFPs."""
    service = RFPService(db)
    stats = service.get_statistics()
    return stats


@router.get("/{rfp_id}", response_model=RFPResponse)
async def get_rfp(rfp: RFPDep):
    """Get RFP details by ID."""
    return rfp


@router.get("/{rfp_id}/competitors")
async def get_competitors(rfp: RFPDep):
    """Get competitor analysis for an RFP."""
    competitor_service = get_competitor_service()
    incumbents = competitor_service.identify_potential_incumbents(
        description=rfp.description or "", agency=rfp.agency or "Unknown"
    )

    agency_stats = competitor_service.get_agency_spend_history(
        agency=rfp.agency or "Unknown"
    )

    return {"potential_incumbents": incumbents, "agency_intelligence": agency_stats}


@router.get("/{rfp_id}/partners")
async def get_teaming_partners(
    rfp: RFPDep, limit: int = Query(default=10, ge=1, le=50), db: DBDep = ...
):
    """Get teaming partner recommendations for an RFP."""
    from src.agents.teaming_service import TeamingPartnerService

    try:
        teaming_service = TeamingPartnerService(db)
        partners = teaming_service.find_partners(rfp.rfp_id, limit=limit)
        return {
            "rfp_id": rfp.rfp_id,
            "partners": partners,
            "total_found": len(partners),
        }
    except Exception as e:
        logger.warning("Teaming partner search failed: %s", e)
        # Return empty results gracefully if SAM.gov API not configured
        return {
            "rfp_id": rfp.rfp_id,
            "partners": [],
            "total_found": 0,
            "message": "Partner search unavailable - SAM.gov API key may not be configured",
        }


@router.post("/{rfp_id}/pricing/scenarios")
async def run_pricing_scenarios(rfp: RFPDep, params: ScenarioInput):
    """Run pricing 'War Gaming' scenarios."""
    if not processor.pricing_engine:
        raise HTTPException(status_code=503, detail="Pricing Engine not initialized")

    rfp_data = rfp_to_processing_dict(rfp)
    custom_params = ScenarioParams(
        labor_cost_multiplier=params.labor_cost_multiplier,
        material_cost_multiplier=params.material_cost_multiplier,
        risk_contingency_percent=params.risk_contingency_percent,
        desired_margin=params.desired_margin,
    )

    return processor.pricing_engine.run_war_gaming(rfp_data, custom_params)


@router.get("/{rfp_id}/pricing/subcontractors")
async def get_subcontractor_opportunities(rfp: RFPDep):
    """Identify potential subcontracting opportunities."""
    if not processor.pricing_engine:
        raise HTTPException(status_code=503, detail="Pricing Engine not initialized")

    rfp_data = rfp_to_processing_dict(rfp)
    return processor.pricing_engine.identify_subcontractors(rfp_data)


@router.get("/{rfp_id}/pricing/ptw")
async def get_price_to_win(
    rfp: RFPDep, target_prob: float = Query(default=0.7, ge=0.05, le=0.95)
):
    """Calculate Price-to-Win (PTW) analysis."""
    if not processor.pricing_engine:
        raise HTTPException(status_code=503, detail="Pricing Engine not initialized")

    rfp_data = rfp_to_processing_dict(rfp)
    return processor.pricing_engine.calculate_price_to_win(rfp_data, target_prob)


@router.post("", response_model=RFPResponse)
async def create_rfp(rfp_data: RFPCreate, db: DBDep):
    """Create a new RFP entry."""
    service = RFPService(db)
    rfp = service.create_rfp(rfp_data.model_dump())
    return rfp


@router.put("/{rfp_id}", response_model=RFPResponse)
async def update_rfp(rfp_id: str, update_data: RFPUpdate, db: DBDep):
    """Update RFP details."""
    service = RFPService(db)
    rfp = service.update_rfp(rfp_id, update_data.model_dump(exclude_unset=True))
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")
    return rfp


@router.delete("/{rfp_id}")
async def delete_rfp(rfp_id: str, db: DBDep):
    """
    Delete an RFP and all related data (documents, Q&A, bids).
    This allows re-importing the same RFP from scratch.
    """
    from app.models.database import BidDocument, RFPDocument, RFPQandA

    # Find the RFP
    rfp = db.query(RFPOpportunity).filter(RFPOpportunity.rfp_id == rfp_id).first()
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    rfp_title = rfp.title

    # Delete related records
    db.query(RFPDocument).filter(RFPDocument.rfp_id == rfp.id).delete()
    db.query(RFPQandA).filter(RFPQandA.rfp_id == rfp.id).delete()
    db.query(BidDocument).filter(BidDocument.rfp_id == rfp.id).delete()

    # Delete the RFP itself
    db.delete(rfp)
    db.commit()

    logger.info("Deleted RFP %s: %s", rfp_id, rfp_title)

    return {"message": f"RFP '{rfp_title}' deleted successfully", "rfp_id": rfp_id}


@router.post("/{rfp_id}/triage", response_model=RFPResponse)
async def update_triage_decision(
    rfp_id: str, decision: TriageDecision, service: RFPServiceDep
):
    """Update triage decision for an RFP."""
    from app.websockets.websocket_router import broadcast_rfp_update

    rfp = service.update_triage_decision(rfp_id, decision.decision, decision.notes)
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    # Broadcast update to connected clients
    await broadcast_rfp_update(
        rfp_id,
        "triage_updated",
        {
            "decision": decision.decision,
            "current_stage": (
                rfp.current_stage.value
                if hasattr(rfp.current_stage, "value")
                else str(rfp.current_stage)
            ),
        },
    )

    return rfp


@router.post("/{rfp_id}/advance-stage")
async def advance_pipeline_stage(
    rfp_id: str, service: RFPServiceDep, notes: str | None = None
):
    """Advance RFP to next pipeline stage."""
    from app.websockets.websocket_router import broadcast_rfp_update

    rfp = service.advance_stage(rfp_id, notes)
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    # Broadcast stage change to connected clients
    await broadcast_rfp_update(
        rfp_id,
        "stage_advanced",
        {
            "current_stage": (
                rfp.current_stage.value
                if hasattr(rfp.current_stage, "value")
                else str(rfp.current_stage)
            )
        },
    )

    return {
        "message": "Stage advanced successfully",
        "current_stage": rfp.current_stage,
    }


@router.post("/discover")
async def discover_rfps(
    params: DiscoveryParams = _DEFAULT_DISCOVERY_PARAMS,
    background_tasks: BackgroundTasks = ...,
):
    """
    Trigger automated RFP discovery.
    """
    job_id = str(uuid4())

    # Initialize job status
    processing_jobs[job_id] = {
        "status": "running",
        "discovered_count": 0,
        "processed_count": 0,
        "rfps": [],
        "started_at": datetime.now(timezone.utc).isoformat(),
    }

    # Start background task
    background_tasks.add_task(
        processor._run_discovery,
        job_id,
        {"limit": params.limit, "days_back": params.days_back},
    )

    return {"job_id": job_id, "message": "Discovery started"}


@router.get("/discover/status/{job_id}")
async def get_discovery_status(job_id: str):
    """Get status of an RFP discovery job."""
    status = processor.get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    return status


@router.post("/process")
async def process_manual_rfp(rfp_data: ManualRFPSubmit, db: DBDep):
    """
    Manually add an RFP and process it through the ML pipeline.
    Returns processed RFP with triage score, decision, etc.
    """
    # Process through ML pipeline
    processed = await processor.process_single_rfp(rfp_data.dict())

    # Save to database
    service = RFPService(db)
    rfp_id = f"RFP-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    db_data = {
        "rfp_id": rfp_id,
        "title": rfp_data.title,
        "agency": rfp_data.agency,
        "solicitation_number": rfp_data.solicitation_number,
        "description": rfp_data.description,
        "category": rfp_data.category,
        "response_deadline": rfp_data.response_deadline,
        "triage_score": processed.get("triage_score"),
        "decision_recommendation": processed.get("decision_recommendation"),
    }

    rfp = service.create_rfp(db_data)

    return {**processed, "id": rfp.id, "rfp_id": rfp.rfp_id, "saved": True}


@router.post("/{rfp_id}/generate-bid")
async def generate_bid_document(
    rfp: RFPDep,
    db: DBDep,
    options: BidGenerationOptions | None = None,
):
    """
    Generate a complete bid document for an RFP.
    Includes proposal content, compliance matrix, and pricing breakdown.

    Generation Modes:
    - template: Fast template-based generation (no API calls)
    - claude_standard: Claude Sonnet 4.5 without extended thinking
    - claude_enhanced: Claude Sonnet 4.5 with extended thinking (recommended)
    - claude_premium: Claude Opus 4.5 with extended thinking (highest quality)

    Args:
        rfp: The RFP to generate a bid for
        db: Database session
        options: Generation options including mode and thinking settings
    """
    from app.models.database import RFPQandA
    from app.websockets.websocket_router import broadcast_rfp_update

    from src.bid_generation.compliance_signals import create_compliance_detector

    # Default options if not provided
    if options is None:
        options = BidGenerationOptions()

    # Broadcast that bid generation has started
    await broadcast_rfp_update(
        rfp.rfp_id,
        "bid_generation_started",
        {
            "title": rfp.title,
            "generation_mode": options.generation_mode,
            "enable_thinking": options.enable_thinking,
        },
    )

    # Convert RFP to dict for processing
    rfp_data = rfp_to_processing_dict(rfp)

    # Fetch Q&A items from database
    qa_records = db.query(RFPQandA).filter(RFPQandA.rfp_id == rfp.id).all()
    qa_items = (
        [
            {
                "question_text": qa.question_text,
                "answer_text": qa.answer_text,
                "category": qa.category,
                "asked_date": qa.asked_date.isoformat() if qa.asked_date else None,
            }
            for qa in qa_records
        ]
        if qa_records
        else None
    )

    # Fetch and extract content from RFP documents (PDFs, DOCX, etc.)
    document_content = None
    if options.generation_mode != "template":
        try:
            doc_records = (
                db.query(RFPDocument).filter(RFPDocument.rfp_id == rfp.id).all()
            )
            if doc_records:
                # Convert to list of dicts for extraction
                docs_for_extraction = [
                    {
                        "file_path": doc.file_path,
                        "filename": doc.filename,
                        "document_type": doc.document_type,
                    }
                    for doc in doc_records
                    if doc.file_path  # Only include downloaded documents
                ]

                if docs_for_extraction:
                    extracted = extract_all_document_content(docs_for_extraction)
                    if extracted["documents"]:
                        document_content = extracted
                        logger.info(
                            f"Extracted content from {extracted['document_count']} documents "
                            f"({extracted['total_chars']} chars) for RFP {rfp.rfp_id}"
                        )
        except Exception as e:
            logger.warning("Failed to extract document content: %s", e)

    # Detect compliance signals from RFP data and Q&A
    compliance_signals = None
    if options.generation_mode != "template":
        try:
            detector = create_compliance_detector()
            signals = detector.detect_signals(rfp_data, qa_items)
            compliance_signals = detector.to_dict(signals)

            # Log detected signals for visibility
            if signals.detected_signals:
                logger.info(
                    f"Detected compliance signals for {rfp.rfp_id}: {signals.detected_signals}"
                )
        except Exception as e:
            logger.warning("Failed to detect compliance signals: %s", e)

    # Generate bid document with options and compliance context
    bid_document = await processor.generate_bid_document(
        rfp_data,
        generation_mode=options.generation_mode,
        enable_thinking=options.enable_thinking,
        thinking_budget=options.thinking_budget,
        qa_items=qa_items,
        compliance_signals=compliance_signals,
        document_content=document_content,
    )

    if "error" in bid_document:
        await broadcast_rfp_update(
            rfp.rfp_id, "bid_generation_failed", {"error": bid_document["error"]}
        )
        raise HTTPException(
            status_code=500, detail=f"Bid generation failed: {bid_document['error']}"
        )

    # Save sections to database for Proposal Copilot
    save_proposal_sections_to_db(
        rfp_id=rfp.id, rfp_id_str=rfp.rfp_id, bid_document_data=bid_document, db=db
    )

    # Broadcast successful generation
    await broadcast_rfp_update(
        rfp.rfp_id,
        "bid_generated",
        {
            "bid_id": bid_document["bid_id"],
            "sections": (
                list(bid_document["content"]["sections"].keys())
                if bid_document.get("content", {}).get("sections")
                else []
            ),
            "generation_mode": options.generation_mode,
            "claude_enhanced": bid_document["metadata"].get("claude_enhanced", False),
        },
    )

    return {
        "bid_id": bid_document["bid_id"],
        "rfp_id": rfp.rfp_id,
        "generated_at": bid_document["metadata"]["generated_at"],
        "preview": {
            "markdown": bid_document["content"]["markdown"][:500] + "...",
            "sections": list(bid_document["content"]["sections"].keys()),
        },
        "metadata": bid_document["metadata"],
    }


@router.get("/bids/{bid_id}")
async def get_bid_document(bid_id: str):
    """Get a generated bid document by ID."""
    bid_document = processor.get_bid_document(bid_id)

    if not bid_document:
        raise HTTPException(status_code=404, detail="Bid document not found")

    return bid_document


@router.get("/bids/{bid_id}/download/{format}")
async def download_bid_document(bid_id: str, format: str):
    """
    Download a bid document in the specified format.
    Supported formats: markdown, html, json
    """
    from fastapi.responses import FileResponse

    if format not in ["markdown", "html", "json"]:
        raise HTTPException(
            status_code=400, detail="Invalid format. Use: markdown, html, or json"
        )

    filepath = processor.export_bid_document(bid_id, format)

    if not filepath:
        raise HTTPException(
            status_code=404, detail="Bid document not found or export failed"
        )

    media_types = {
        "markdown": "text/markdown",
        "html": "text/html",
        "json": "application/json",
    }

    return FileResponse(
        filepath, media_type=media_types[format], filename=os.path.basename(filepath)
    )


class PricingTableOptions(BaseModel):
    """Options for generating a pricing table."""

    num_websites: int = 3
    base_years: int = 3
    optional_years: int = 2
    base_budget_per_site: float = 50000.0
    custom_rates: dict[str, float] | None = None


@router.post("/{rfp_id}/pricing-table")
async def generate_pricing_table(
    rfp_id: str,
    options: PricingTableOptions | None = None,
    db: DBDep = ...,
):
    """
    Generate a detailed pricing table for the RFP bid.
    Includes multi-year breakdown with optional years.
    """
    from src.bid_generation.pricing_table_generator import (
        create_pricing_table_generator,
    )

    # Get RFP
    rfp = db.query(RFPOpportunity).filter(RFPOpportunity.rfp_id == rfp_id).first()
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    # Get company profile (use default if none)
    from app.models.database import CompanyProfile

    profile = db.query(CompanyProfile).filter(CompanyProfile.is_default).first()

    company_profile = {
        "company_name": profile.name if profile else "Your Company",
    }

    rfp_data = {
        "rfp_id": rfp.rfp_id,
        "title": rfp.title,
        "description": rfp.description,
        "agency": rfp.agency,
    }

    # Generate pricing table
    opts = options or PricingTableOptions()
    generator = create_pricing_table_generator(custom_rates=opts.custom_rates)

    pricing_table = generator.generate_website_pricing(
        rfp_data=rfp_data,
        company_profile=company_profile,
        num_websites=opts.num_websites,
        base_years=opts.base_years,
        optional_years=opts.optional_years,
        base_budget_per_site=opts.base_budget_per_site,
    )

    return generator.to_dict(pricing_table)


@router.get("/{rfp_id}/pricing-table/csv")
async def download_pricing_table_csv(
    rfp_id: str,
    num_websites: int = 3,
    base_years: int = 3,
    optional_years: int = 2,
    base_budget_per_site: float = 50000.0,
    db: DBDep = ...,
):
    """
    Download the pricing table as a CSV file.
    """
    from fastapi.responses import StreamingResponse

    from src.bid_generation.pricing_table_generator import (
        create_pricing_table_generator,
    )

    # Get RFP
    rfp = db.query(RFPOpportunity).filter(RFPOpportunity.rfp_id == rfp_id).first()
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    # Get company profile
    from app.models.database import CompanyProfile

    profile = db.query(CompanyProfile).filter(CompanyProfile.is_default).first()

    company_profile = {
        "company_name": profile.name if profile else "Your Company",
    }

    rfp_data = {
        "rfp_id": rfp.rfp_id,
        "title": rfp.title,
    }

    # Generate pricing table
    generator = create_pricing_table_generator()
    pricing_table = generator.generate_website_pricing(
        rfp_data=rfp_data,
        company_profile=company_profile,
        num_websites=num_websites,
        base_years=base_years,
        optional_years=optional_years,
        base_budget_per_site=base_budget_per_site,
    )

    csv_content = generator.to_csv(pricing_table)

    # Return as streaming response
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=pricing_table_{rfp_id}.csv"
        },
    )


@router.get("/{rfp_id}/checklist", response_model=PostAwardChecklistResponse)
async def get_post_award_checklist(rfp: RFPDep, db: DBDep):
    """Get the post-award compliance checklist for a specific RFP."""
    checklist = (
        db.query(PostAwardChecklist).filter(PostAwardChecklist.rfp_id == rfp.id).first()
    )
    if not checklist:
        raise HTTPException(
            status_code=404, detail="Post-award checklist not found for this RFP"
        )

    return checklist


class FeedbackInput(BaseModel):
    """Input for decision feedback loop."""

    actual_outcome: str  # WON, LOST, NO_BID
    user_override: str | None = None  # GO, NO_GO


@router.post("/{rfp_id}/feedback")
async def submit_decision_feedback(rfp_id: str, feedback: FeedbackInput, db: DBDep):
    """
    Submit feedback on a Go/No-Go decision to improve the model.
    """
    if not processor.pricing_engine:
        # In a real app we might want a dedicated DecisionEngine instance in processor
        # For now, we'll assume if pricing engine is there, the system is initialized
        pass

    # Log feedback via the engine (which logs to file/stdout)
    # In the future, this would update weights in the DB

    # We need access to the GoNoGoEngine instance.
    # Currently it's instantiated inside the processor or main script.
    # Let's assume we can access it via the processor if we added it there,
    # or we instantiate a temporary one for logging if stateless.

    # For this implementation, we'll use the one in the processor if available,
    # or just log it here.

    return {"message": "Feedback received", "rfp_id": rfp_id}


@router.post("/{rfp_id}/async/ingest")
async def trigger_async_ingestion(
    rfp_id: str, file_paths: list[str], background_tasks: BackgroundTasks = ...
):
    """Trigger background RAG ingestion."""
    from app.services.background_tasks import ingest_documents_task

    task_id = str(uuid4())
    background_tasks.add_task(ingest_documents_task, task_id, rfp_id, file_paths)
    return {"task_id": task_id, "status": "processing"}


@router.post("/{rfp_id}/async/generate-bid")
async def trigger_async_bid_generation(rfp: RFPDep, background_tasks: BackgroundTasks):
    """Trigger background bid generation."""
    from app.services.background_tasks import generate_bid_task

    rfp_data = rfp_to_processing_dict(rfp)
    task_id = str(uuid4())
    background_tasks.add_task(generate_bid_task, task_id, rfp_data)
    return {"task_id": task_id, "status": "processing"}


@router.get("/tasks/{task_id}")
async def get_background_task_status(task_id: str):
    """Get status of a background task."""
    from app.services.background_tasks import get_task_status

    status = get_task_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task_id": task_id, **status}


# ============================================================================
# Compliance Matrix Endpoints
# ============================================================================


@router.get("/{rfp_id}/compliance-matrix")
async def get_compliance_matrix(rfp: RFPDep, db: DBDep):
    """
    Get the compliance matrix for an RFP.
    Returns extracted requirements and compliance status.
    """
    from app.models.database import ComplianceMatrix

    matrix = (
        db.query(ComplianceMatrix).filter(ComplianceMatrix.rfp_id == rfp.id).first()
    )

    if not matrix:
        # Return empty structure if no matrix exists yet
        return {
            "requirements_extracted": 0,
            "requirements_met": 0,
            "compliance_score": 0.0,
            "requirements": [],
            "created_at": None,
            "updated_at": None,
        }

    # Parse matrix_data which contains the requirements
    requirements = []
    if matrix.matrix_data:
        raw_requirements = matrix.matrix_data.get("requirements", [])
        for i, req in enumerate(raw_requirements):
            requirements.append(
                {
                    "id": req.get("id", f"REQ-{i + 1}"),
                    "requirement_text": req.get(
                        "text", req.get("requirement_text", "")
                    ),
                    "category": req.get("category", "general"),
                    "priority": req.get("priority", "medium"),
                    "status": req.get("status", "pending"),
                    "response_notes": req.get("response", req.get("response_notes")),
                    "source_section": req.get("source_section"),
                }
            )

    return {
        "requirements_extracted": matrix.requirements_extracted or len(requirements),
        "requirements_met": matrix.requirements_met or 0,
        "compliance_score": matrix.compliance_score or 0.0,
        "requirements": requirements,
        "created_at": matrix.created_at.isoformat() if matrix.created_at else None,
        "updated_at": matrix.updated_at.isoformat() if matrix.updated_at else None,
    }


# ============================================================================
# Activity Log Endpoints
# ============================================================================


@router.get("/{rfp_id}/activity")
async def get_activity_log(rfp: RFPDep, db: DBDep):
    """
    Get the activity log (pipeline events) for an RFP.
    Returns all stage transitions and actions.
    """
    from app.models.database import PipelineEvent

    events = (
        db.query(PipelineEvent)
        .filter(PipelineEvent.rfp_id == rfp.id)
        .order_by(PipelineEvent.timestamp.desc())
        .all()
    )

    return [
        {
            "id": event.id,
            "from_stage": event.from_stage.value if event.from_stage else None,
            "to_stage": event.to_stage.value if event.to_stage else None,
            "timestamp": event.timestamp.isoformat() if event.timestamp else None,
            "user": event.user,
            "automated": event.automated,
            "notes": event.notes,
            "event_metadata": event.event_metadata or {},
        }
        for event in events
    ]


# ============================================================================
# Archive Endpoint
# ============================================================================


@router.post("/{rfp_id}/archive")
async def archive_rfp(rfp: RFPDep, db: DBDep):
    """
    Archive an RFP. Sets the stage to 'rejected' with archive metadata.
    """
    from app.models.database import PipelineEvent

    old_stage = rfp.current_stage

    # Update RFP stage
    rfp.current_stage = PipelineStage.REJECTED
    rfp.rfp_metadata = rfp.rfp_metadata or {}
    rfp.rfp_metadata["archived"] = True
    rfp.rfp_metadata["archived_at"] = datetime.now(timezone.utc).isoformat()

    # Create pipeline event
    event = PipelineEvent(
        rfp_id=rfp.id,
        from_stage=old_stage,
        to_stage=PipelineStage.REJECTED,
        timestamp=datetime.now(timezone.utc),
        automated=False,
        notes="RFP archived by user",
    )
    db.add(event)
    db.commit()

    return {"message": "RFP archived successfully", "rfp_id": rfp.rfp_id}


# ============================================================================
# AI Chat Endpoints
# ============================================================================


class ChatMessage(BaseModel):
    """Chat message input."""

    message: str = Field(..., min_length=1, max_length=5000)
    conversation_id: str | None = None


@router.post("/{rfp_id}/chat")
async def send_chat_message(rfp: RFPDep, chat: ChatMessage):
    """
    Send a chat message about the RFP and get an AI response.
    Uses the RFP context to provide relevant answers.
    """
    try:
        # Build context from RFP data
        context_parts = [
            f"RFP Title: {rfp.title}",
            f"Agency: {rfp.agency or 'Not specified'}",
            f"Description: {rfp.description or 'No description'}",
        ]

        if rfp.naics_code:
            context_parts.append(f"NAICS Code: {rfp.naics_code}")

        if rfp.response_deadline:
            context_parts.append(
                f"Deadline: {rfp.response_deadline.strftime('%Y-%m-%d')}"
            )

        # Get Q&A items for additional context
        qa_items = rfp.qa_items[:5] if rfp.qa_items else []
        if qa_items:
            context_parts.append("\nRelevant Q&A:")
            for qa in qa_items:
                context_parts.append(f"Q: {qa.question_text}")
                if qa.answer_text:
                    context_parts.append(f"A: {qa.answer_text}")

        context = "\n".join(context_parts)

        # Try to use Claude for response
        try:
            from src.config.claude_llm_config import ClaudeModel, create_claude_client

            client = create_claude_client()
            response = client.messages.create(
                model=ClaudeModel.SONNET_4_5.value,
                max_tokens=1024,
                system=f"""You are an AI assistant helping with government RFP (Request for Proposal) analysis.
You have access to the following RFP context:

{context}

Provide helpful, concise answers about this RFP. Focus on:
- Key requirements and compliance considerations
- Potential risks and opportunities
- Strategic recommendations
Keep responses brief (2-3 paragraphs max) and actionable.""",
                messages=[{"role": "user", "content": chat.message}],
            )

            ai_response = response.content[0].text

        except Exception as e:
            logger.warning("Claude API failed, using fallback: %s", e)
            # Fallback response
            ai_response = f"""I can help you analyze this RFP for "{rfp.title}".

Based on the available information:
- Agency: {rfp.agency or 'Not specified'}
- Deadline: {rfp.response_deadline.strftime('%Y-%m-%d') if rfp.response_deadline else 'Not specified'}

For more detailed analysis, please ensure the Claude API is properly configured. You asked: "{chat.message[:100]}..."

Please try specific questions about requirements, compliance, or strategy."""

        return {
            "message_id": str(uuid4()),
            "response": ai_response,
            "conversation_id": chat.conversation_id or str(uuid4()),
        }

    except Exception as e:
        logger.exception("Chat error occurred")
        raise HTTPException(status_code=500, detail=f"Chat failed: {e!s}") from e


@router.get("/{rfp_id}/chat")
async def get_chat_history(conversation_id: str | None = None):
    """
    Get chat history for an RFP (placeholder - would need persistent storage).
    Currently returns empty as chat history is stored client-side.
    """
    # In a production system, you would store chat history in the database
    # For now, chat history is maintained client-side
    return {
        "messages": [],
        "conversation_id": conversation_id,
    }
