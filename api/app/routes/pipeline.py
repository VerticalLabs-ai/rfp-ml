"""
Pipeline monitoring API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_db
from app.models.database import RFPOpportunity, PipelineEvent, PipelineStage

router = APIRouter()


class PipelineStatusResponse(BaseModel):
    rfp_id: str
    title: str
    current_stage: PipelineStage
    triage_score: float
    started_at: datetime
    updated_at: datetime
    duration_hours: float

    class Config:
        from_attributes = True


class PipelineEventResponse(BaseModel):
    from_stage: str
    to_stage: str
    timestamp: datetime
    duration_seconds: float
    automated: bool
    notes: str

    class Config:
        from_attributes = True


@router.get("/status")
async def get_pipeline_status(db: Session = Depends(get_db)):
    """Get overall pipeline status."""
    # Count RFPs by stage
    stages = {}
    for stage in PipelineStage:
        count = db.query(RFPOpportunity).filter(
            RFPOpportunity.current_stage == stage
        ).count()
        stages[stage.value] = count

    return {
        "stages": stages,
        "timestamp": datetime.utcnow()
    }


@router.get("/{rfp_id}", response_model=List[PipelineEventResponse])
async def get_rfp_pipeline(rfp_id: str, db: Session = Depends(get_db)):
    """Get pipeline history for an RFP."""
    rfp = db.query(RFPOpportunity).filter(
        RFPOpportunity.rfp_id == rfp_id
    ).first()

    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    events = db.query(PipelineEvent).filter(
        PipelineEvent.rfp_id == rfp.id
    ).order_by(PipelineEvent.timestamp).all()

    return [{
        "from_stage": event.from_stage.value if event.from_stage else "start",
        "to_stage": event.to_stage.value,
        "timestamp": event.timestamp,
        "duration_seconds": event.duration_seconds or 0,
        "automated": event.automated,
        "notes": event.notes or ""
    } for event in events]


@router.get("/metrics/performance")
async def get_pipeline_metrics(db: Session = Depends(get_db)):
    """Get pipeline performance metrics."""
    # Average processing time by stage
    from sqlalchemy import func

    avg_times = db.query(
        PipelineEvent.to_stage,
        func.avg(PipelineEvent.duration_seconds).label("avg_duration")
    ).group_by(PipelineEvent.to_stage).all()

    metrics = {
        "avg_stage_duration": {
            stage.value: duration for stage, duration in avg_times
        },
        "calculated_at": datetime.utcnow()
    }

    return metrics
