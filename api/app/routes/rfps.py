"""
RFP management API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
import os
from uuid import uuid4

from app.core.database import get_db
from app.models.database import RFPOpportunity, PipelineStage, PostAwardChecklist
from app.services.rfp_service import RFPService
from app.services.rfp_processor import processor, processing_jobs
from src.agents.competitor_analytics import CompetitorAnalyticsService
from src.agents.teaming_service import TeamingPartnerService
from src.pricing.pricing_engine import ScenarioParams
from pydantic import BaseModel

router = APIRouter()

# Global instance
competitor_service = CompetitorAnalyticsService()

# Pydantic schemas
class DiscoveryParams(BaseModel):
    limit: int = 50
    days_back: int = 30

class ScenarioInput(BaseModel):
    """Input for pricing scenario simulation."""
    labor_cost_multiplier: float = 1.0
    material_cost_multiplier: float = 1.0
    risk_contingency_percent: float = 0.0
    desired_margin: float = 0.0

class RFPBase(BaseModel):
    solicitation_number: Optional[str] = None
    title: str
    description: Optional[str] = None
    agency: Optional[str] = None
    office: Optional[str] = None
    naics_code: Optional[str] = None
    category: Optional[str] = None
    response_deadline: Optional[datetime] = None


class RFPCreate(RFPBase):
    rfp_id: str


class RFPResponse(RFPBase):
    id: int
    rfp_id: str
    current_stage: PipelineStage
    triage_score: Optional[float] = None
    overall_score: Optional[float] = None
    decision_recommendation: Optional[str] = None
    discovered_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RFPUpdate(BaseModel):
    current_stage: Optional[PipelineStage] = None
    assigned_to: Optional[str] = None
    priority: Optional[int] = None


class TriageDecision(BaseModel):
    decision: str  # approve, reject, flag
    notes: Optional[str] = None


class ManualRFPSubmit(BaseModel):
    """Schema for manually submitting an RFP for processing."""
    title: str
    agency: Optional[str] = None
    solicitation_number: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    award_amount: Optional[float] = None
    response_deadline: Optional[datetime] = None
    category: Optional[str] = "general"


class ChecklistItemResponse(BaseModel):
    id: str
    description: str
    status: str
    assigned_to: Optional[str]
    due_date: Optional[datetime]
    notes: Optional[str]
    meta: Dict[str, Any]

class PostAwardChecklistResponse(BaseModel):
    id: int
    rfp_id: int
    bid_document_id: Optional[str]
    generated_at: datetime
    status: str
    items: List[ChecklistItemResponse]
    summary: Dict[str, Any]

    class Config:
        from_attributes = True


@router.get("/discovered", response_model=List[RFPResponse])
async def get_discovered_rfps(
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    min_score: Optional[float] = None,
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
async def get_rfp(rfp_id: str, db: Session = Depends(get_db)):
    """Get RFP details by ID."""
    service = RFPService(db)
    rfp = service.get_rfp_by_id(rfp_id)
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")
    return rfp


@router.get("/{rfp_id}/competitors")
async def get_competitors(rfp_id: str, db: Session = Depends(get_db)):
    """Get competitor analysis for an RFP."""
    service = RFPService(db)
    rfp = service.get_rfp_by_id(rfp_id)
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")
        
    # Perform analysis
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


@router.post("/{rfp_id}/pricing/scenarios")
async def run_pricing_scenarios(
    rfp_id: str,
    params: ScenarioInput,
    db: Session = Depends(get_db)
):
    """Run pricing 'War Gaming' scenarios."""
    service = RFPService(db)
    rfp = service.get_rfp_by_id(rfp_id)
    
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    # Convert RFP to dict
    rfp_data = {
        "rfp_id": rfp.rfp_id,
        "title": rfp.title,
        "agency": rfp.agency,
        "description": rfp.description,
        "naics_code": rfp.naics_code,
        "category": rfp.category
    }
    
    if not processor.pricing_engine:
        raise HTTPException(status_code=503, detail="Pricing Engine not initialized")
        
    custom_params = ScenarioParams(
        labor_cost_multiplier=params.labor_cost_multiplier,
        material_cost_multiplier=params.material_cost_multiplier,
        risk_contingency_percent=params.risk_contingency_percent,
        desired_margin=params.desired_margin
    )
    
    results = processor.pricing_engine.run_war_gaming(rfp_data, custom_params)
    
    return results


@router.get("/{rfp_id}/pricing/subcontractors")
async def get_subcontractor_opportunities(
    rfp_id: str,
    db: Session = Depends(get_db)
):
    """Identify potential subcontracting opportunities."""
    service = RFPService(db)
    rfp = service.get_rfp_by_id(rfp_id)
    
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    if not processor.pricing_engine:
        raise HTTPException(status_code=503, detail="Pricing Engine not initialized")

    # Convert RFP to dict
    rfp_data = {
        "rfp_id": rfp.rfp_id,
        "title": rfp.title,
        "agency": rfp.agency,
        "description": rfp.description,
        "naics_code": rfp.naics_code,
        "category": rfp.category
    }
    
    opportunities = processor.pricing_engine.identify_subcontractors(rfp_data)
    
    return opportunities


@router.get("/{rfp_id}/pricing/ptw")
async def get_price_to_win(
    rfp_id: str,
    target_prob: float = 0.7,
    db: Session = Depends(get_db)
):
    """Calculate Price-to-Win (PTW) analysis."""
    service = RFPService(db)
    rfp = service.get_rfp_by_id(rfp_id)
    
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")
    
    if not processor.pricing_engine:
        raise HTTPException(status_code=503, detail="Pricing Engine not initialized")
        
    rfp_data = {
        "rfp_id": rfp.rfp_id,
        "title": rfp.title,
        "agency": rfp.agency,
        "description": rfp.description,
        "naics_code": rfp.naics_code,
        "category": rfp.category
    }
    
    result = processor.pricing_engine.calculate_price_to_win(rfp_data, target_prob)
    
    return result


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
    db: Session = Depends(get_db)
):
    """Update triage decision for an RFP."""
    service = RFPService(db)
    rfp = service.update_triage_decision(rfp_id, decision.decision, decision.notes)
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")
    return rfp


@router.post("/{rfp_id}/advance-stage")
async def advance_pipeline_stage(
    rfp_id: str,
    notes: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Advance RFP to next pipeline stage."""
    service = RFPService(db)
    rfp = service.advance_stage(rfp_id, notes)
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")
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
async def generate_bid_document(
    rfp_id: str,
    db: Session = Depends(get_db)
):
    """
    Generate a complete bid document for an RFP.
    Includes proposal content, compliance matrix, and pricing breakdown.
    """
    service = RFPService(db)
    rfp = service.get_rfp_by_id(rfp_id)
    
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")
    
    # Convert RFP to dict for processing
    rfp_data = {
        "rfp_id": rfp.rfp_id,
        "title": rfp.title,
        "agency": rfp.agency,
        "solicitation_number": rfp.solicitation_number,
        "description": rfp.description,
        "category": rfp.category,
        "naics_code": rfp.naics_code,
        "response_deadline": rfp.response_deadline.isoformat() if rfp.response_deadline else None
    }
    
    # Generate bid document
    bid_document = await processor.generate_bid_document(rfp_data)
    
    if "error" in bid_document:
        raise HTTPException(status_code=500, detail=f"Bid generation failed: {bid_document['error']}")
    
    return {
        "bid_id": bid_document["bid_id"],
        "rfp_id": rfp_id,
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
async def get_post_award_checklist(rfp_id: str, db: Session = Depends(get_db)):
    """Get the post-award compliance checklist for a specific RFP."""
    service = RFPService(db)
    rfp = service.get_rfp_by_id(rfp_id)
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")
    
    checklist = db.query(PostAwardChecklist).filter(PostAwardChecklist.rfp_id == rfp.id).first()
    if not checklist:
        raise HTTPException(status_code=404, detail="Post-award checklist not found for this RFP")
    
    return checklist

@router.get("/{rfp_id}/partners")
async def get_teaming_partners(rfp_id: str, limit: int = 10, db: Session = Depends(get_db)):
    """
    Find potential teaming partners for an RFP based on NAICS and keyword matching
    against the ingested SAM.gov database.
    """
    service = TeamingPartnerService(db)
    partners = service.find_partners(rfp_id, limit=limit)
    return partners
