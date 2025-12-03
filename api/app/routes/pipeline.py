"""
Pipeline monitoring API endpoints.

Provides:
- Real-time pipeline status with RFPs grouped by stage
- Pipeline history for individual RFPs
- Performance metrics
- Pagination for large datasets
"""
import logging
from datetime import datetime, timezone
from typing import Any, List

from app.dependencies import DBDep
from app.models.database import PipelineEvent, PipelineStage, RFPOpportunity
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

# Cache for pipeline status (reduces DB load)
_pipeline_cache: dict | None = None
_cache_timestamp: float = 0
_CACHE_TTL = 30  # 30 seconds cache


class PipelineRFPResponse(BaseModel):
    """RFP item in pipeline view."""
    id: int
    rfp_id: str
    title: str
    agency: str | None
    current_stage: str
    triage_score: float | None
    created_at: datetime | None
    updated_at: datetime | None

    class Config:
        from_attributes = True


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


def rfp_to_pipeline_dict(rfp: RFPOpportunity) -> dict:
    """Convert RFP model to pipeline response dict."""
    return {
        "id": rfp.id,
        "rfp_id": rfp.rfp_id,
        "title": rfp.title or "Untitled",
        "agency": rfp.agency,
        "current_stage": rfp.current_stage.value if rfp.current_stage else "discovered",
        "triage_score": rfp.triage_score,
        "created_at": rfp.created_at,
        "updated_at": rfp.updated_at,
    }


@router.get("/status")
async def get_pipeline_status(
    skip: int = Query(default=0, ge=0, description="Number of RFPs to skip per stage"),
    limit: int = Query(default=50, ge=1, le=200, description="Max RFPs per stage"),
    use_cache: bool = Query(default=True, description="Use cached data if available"),
    db: DBDep = ...,
) -> dict[str, Any]:
    """
    Get overall pipeline status with RFPs grouped by stage.

    Returns:
        - stages: Dict with stage counts
        - rfps: List of all RFPs with their current stage
        - timestamp: When data was fetched
        - cached: Whether data came from cache
    """
    import time
    global _pipeline_cache, _cache_timestamp

    # Check cache
    cache_age = time.time() - _cache_timestamp
    if use_cache and _pipeline_cache and cache_age < _CACHE_TTL:
        logger.debug(f"Returning cached pipeline status (age: {cache_age:.1f}s)")
        return {**_pipeline_cache, "cached": True, "cache_age_seconds": int(cache_age)}

    try:
        # Count RFPs by stage
        stages = {}
        for stage in PipelineStage:
            count = db.query(RFPOpportunity).filter(
                RFPOpportunity.current_stage == stage
            ).count()
            stages[stage.value] = count

        # Get RFPs for each stage (with pagination)
        rfps = []
        for stage in PipelineStage:
            stage_rfps = db.query(RFPOpportunity).filter(
                RFPOpportunity.current_stage == stage
            ).order_by(
                RFPOpportunity.updated_at.desc()
            ).offset(skip).limit(limit).all()

            for rfp in stage_rfps:
                rfps.append(rfp_to_pipeline_dict(rfp))

        result = {
            "stages": stages,
            "rfps": rfps,
            "total_count": sum(stages.values()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cached": False,
        }

        # Update cache
        _pipeline_cache = result
        _cache_timestamp = time.time()

        return result

    except Exception as e:
        logger.error(f"Failed to fetch pipeline status: {e}")
        # Return cached data on error if available
        if _pipeline_cache:
            logger.warning("Returning stale cache due to error")
            return {**_pipeline_cache, "cached": True, "stale": True}
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{rfp_id}", response_model=List[PipelineEventResponse])
async def get_rfp_pipeline(rfp_id: str, db: DBDep):
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
async def get_pipeline_metrics(db: DBDep):
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
        "calculated_at": datetime.now(timezone.utc)
    }

    return metrics


@router.delete("/cache")
async def clear_pipeline_cache():
    """Clear the pipeline status cache to force fresh data."""
    global _pipeline_cache, _cache_timestamp

    _pipeline_cache = None
    _cache_timestamp = 0

    return {"status": "cache_cleared"}
