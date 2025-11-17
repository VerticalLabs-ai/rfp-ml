"""
RFP management API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.models.database import RFPOpportunity, PipelineStage
from app.services.rfp_service import RFPService
from pydantic import BaseModel

router = APIRouter()


# Pydantic schemas
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
