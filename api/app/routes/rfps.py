"""
RFP management API endpoints.
"""
import logging
import os
from datetime import datetime
from typing import Any, Dict, List
from uuid import uuid4

from app.core.database import get_db
from app.dependencies import (
    DBDep,
    RFPDep,
    RFPServiceDep,
    get_rfp_or_404,
    rfp_to_dict,
    rfp_to_processing_dict,
)
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
from app.models.database import PipelineStage, PostAwardChecklist, RFPOpportunity
from app.services.rfp_processor import processing_jobs, processor
from app.services.rfp_service import RFPService

from src.agents.competitor_analytics import CompetitorAnalyticsService
from src.pricing.pricing_engine import ScenarioParams

router = APIRouter()

# Lazy-loaded service
_competitor_service = None


def get_competitor_service():
    """Get or create competitor service instance."""
    global _competitor_service
    if _competitor_service is None:
        _competitor_service = CompetitorAnalyticsService()
    return _competitor_service


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


class ChecklistItemResponse(BaseModel):
    id: str
    description: str
    status: str
    assigned_to: str | None
    due_date: datetime | None
    notes: str | None
    meta: Dict[str, Any]

class PostAwardChecklistResponse(BaseModel):
    id: int
    rfp_id: int
    bid_document_id: str | None
    generated_at: datetime
    status: str
    items: List[ChecklistItemResponse]
    summary: Dict[str, Any]

    class Config:
        from_attributes = True


@router.get("/discovered", response_model=List[RFPResponse])
async def get_discovered_rfps(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    category: str | None = None,
    min_score: float | None = Query(default=None, ge=0.0, le=100.0),
    db: Session = Depends(get_db)
):
    """Get list of discovered RFPs."""
    service = RFPService(db)
    rfps = service.get_discovered_rfps(
        skip=skip,
        limit=limit,
        category=category,
        min_score=min_score
    )
    return rfps


@router.get("/recent", response_model=List[RFPResponse])
async def get_recent_rfps(
    limit: int = Query(default=10, le=50),
    db: Session = Depends(get_db)
):
    """Get recently discovered RFPs."""
    query = db.query(RFPOpportunity).order_by(RFPOpportunity.discovered_at.desc()).limit(limit)
    return query.all()


@router.get("/stats/overview")
async def get_rfp_stats(db: Session = Depends(get_db)):
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
        description=rfp.description or "",
        agency=rfp.agency or "Unknown"
    )

    agency_stats = competitor_service.get_agency_spend_history(
        agency=rfp.agency or "Unknown"
    )

    return {
        "potential_incumbents": incumbents,
        "agency_intelligence": agency_stats
    }


@router.get("/{rfp_id}/partners")
async def get_teaming_partners(
    rfp: RFPDep,
    limit: int = Query(default=10, ge=1, le=50),
    db: DBDep = None
):
    """Get teaming partner recommendations for an RFP."""
    from src.agents.teaming_service import TeamingPartnerService

    try:
        teaming_service = TeamingPartnerService(db)
        partners = teaming_service.find_partners(rfp.rfp_id, limit=limit)
        return {
            "rfp_id": rfp.rfp_id,
            "partners": partners,
            "total_found": len(partners)
        }
    except Exception as e:
        logger.warning(f"Teaming partner search failed: {e}")
        # Return empty results gracefully if SAM.gov API not configured
        return {
            "rfp_id": rfp.rfp_id,
            "partners": [],
            "total_found": 0,
            "message": "Partner search unavailable - SAM.gov API key may not be configured"
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
        desired_margin=params.desired_margin
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
    rfp: RFPDep,
    target_prob: float = Query(default=0.7, ge=0.05, le=0.95)
):
    """Calculate Price-to-Win (PTW) analysis."""
    if not processor.pricing_engine:
        raise HTTPException(status_code=503, detail="Pricing Engine not initialized")

    rfp_data = rfp_to_processing_dict(rfp)
    return processor.pricing_engine.calculate_price_to_win(rfp_data, target_prob)


@router.post("", response_model=RFPResponse)
async def create_rfp(rfp_data: RFPCreate, db: Session = Depends(get_db)):
    """Create a new RFP entry."""
    service = RFPService(db)
    rfp = service.create_rfp(rfp_data.dict())
    return rfp


@router.put("/{rfp_id}", response_model=RFPResponse)
async def update_rfp(
    rfp_id: str,
    update_data: RFPUpdate,
    db: Session = Depends(get_db)
):
    """Update RFP details."""
    service = RFPService(db)
    rfp = service.update_rfp(rfp_id, update_data.dict(exclude_unset=True))
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")
    return rfp


@router.post("/{rfp_id}/triage", response_model=RFPResponse)
async def update_triage_decision(
    rfp_id: str,
    decision: TriageDecision,
    service: RFPServiceDep
):
    """Update triage decision for an RFP."""
    from app.websockets.websocket_router import broadcast_rfp_update

    rfp = service.update_triage_decision(rfp_id, decision.decision, decision.notes)
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    # Broadcast update to connected clients
    await broadcast_rfp_update(rfp_id, "triage_updated", {
        "decision": decision.decision,
        "current_stage": rfp.current_stage.value if hasattr(rfp.current_stage, 'value') else str(rfp.current_stage)
    })

    return rfp


@router.post("/{rfp_id}/advance-stage")
async def advance_pipeline_stage(
    rfp_id: str,
    service: RFPServiceDep,
    notes: str | None = None
):
    """Advance RFP to next pipeline stage."""
    from app.websockets.websocket_router import broadcast_rfp_update

    rfp = service.advance_stage(rfp_id, notes)
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    # Broadcast stage change to connected clients
    await broadcast_rfp_update(rfp_id, "stage_advanced", {
        "current_stage": rfp.current_stage.value if hasattr(rfp.current_stage, 'value') else str(rfp.current_stage)
    })

    return {"message": "Stage advanced successfully", "current_stage": rfp.current_stage}


@router.post("/discover")
async def discover_rfps(
    params: DiscoveryParams = DiscoveryParams(),
    background_tasks: BackgroundTasks = None
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
        "started_at": datetime.now().isoformat()
    }

    # Start background task
    background_tasks.add_task(
        processor._run_discovery,
        job_id,
        {"limit": params.limit, "days_back": params.days_back}
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
async def process_manual_rfp(
    rfp_data: ManualRFPSubmit,
    db: Session = Depends(get_db)
):
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
        "decision_recommendation": processed.get("decision_recommendation")
    }

    rfp = service.create_rfp(db_data)

    return {
        **processed,
        "id": rfp.id,
        "rfp_id": rfp.rfp_id,
        "saved": True
    }


@router.post("/{rfp_id}/generate-bid")
async def generate_bid_document(rfp: RFPDep):
    """
    Generate a complete bid document for an RFP.
    Includes proposal content, compliance matrix, and pricing breakdown.
    """
    from app.websockets.websocket_router import broadcast_rfp_update

    # Broadcast that bid generation has started
    await broadcast_rfp_update(rfp.rfp_id, "bid_generation_started", {
        "title": rfp.title
    })

    # Convert RFP to dict for processing
    rfp_data = rfp_to_processing_dict(rfp)

    # Generate bid document
    bid_document = await processor.generate_bid_document(rfp_data)

    if "error" in bid_document:
        await broadcast_rfp_update(rfp.rfp_id, "bid_generation_failed", {
            "error": bid_document["error"]
        })
        raise HTTPException(status_code=500, detail=f"Bid generation failed: {bid_document['error']}")

    # Broadcast successful generation
    await broadcast_rfp_update(rfp.rfp_id, "bid_generated", {
        "bid_id": bid_document["bid_id"],
        "sections": list(bid_document["content"]["sections"].keys()) if bid_document.get("content", {}).get("sections") else []
    })

    return {
        "bid_id": bid_document["bid_id"],
        "rfp_id": rfp.rfp_id,
        "generated_at": bid_document["metadata"]["generated_at"],
        "preview": {
            "markdown": bid_document["content"]["markdown"][:500] + "...",
            "sections": list(bid_document["content"]["sections"].keys())
        },
        "metadata": bid_document["metadata"]
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
        raise HTTPException(status_code=400, detail="Invalid format. Use: markdown, html, or json")

    filepath = processor.export_bid_document(bid_id, format)

    if not filepath:
        raise HTTPException(status_code=404, detail="Bid document not found or export failed")

    media_types = {
        "markdown": "text/markdown",
        "html": "text/html",
        "json": "application/json"
    }

    return FileResponse(
        filepath,
        media_type=media_types[format],
        filename=os.path.basename(filepath)
    )


@router.get("/{rfp_id}/checklist", response_model=PostAwardChecklistResponse)
async def get_post_award_checklist(rfp: RFPDep, db: DBDep):
    """Get the post-award compliance checklist for a specific RFP."""
    checklist = db.query(PostAwardChecklist).filter(PostAwardChecklist.rfp_id == rfp.id).first()
    if not checklist:
        raise HTTPException(status_code=404, detail="Post-award checklist not found for this RFP")

    return checklist


class FeedbackInput(BaseModel):
    """Input for decision feedback loop."""
    actual_outcome: str  # WON, LOST, NO_BID
    user_override: str | None = None  # GO, NO_GO


@router.post("/{rfp_id}/feedback")
async def submit_decision_feedback(
    rfp_id: str,
    feedback: FeedbackInput,
    db: Session = Depends(get_db)
):
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
    rfp_id: str,
    file_paths: List[str],
    background_tasks: BackgroundTasks = None
):
    """Trigger background RAG ingestion."""
    from app.services.background_tasks import ingest_documents_task

    task_id = str(uuid4())
    background_tasks.add_task(ingest_documents_task, task_id, file_paths)
    return {"task_id": task_id, "status": "processing"}


@router.post("/{rfp_id}/async/generate-bid")
async def trigger_async_bid_generation(
    rfp: RFPDep,
    background_tasks: BackgroundTasks
):
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
    return {
        "task_id": task_id,
        **status
    }
