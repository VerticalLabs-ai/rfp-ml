"""
Job management API endpoints.

Provides endpoints for:
- Starting background jobs
- Checking job status
- Cancelling jobs
"""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()


class JobResponse(BaseModel):
    """Response for job creation."""
    job_id: str
    status: str
    created_at: datetime


class JobStatus(BaseModel):
    """Job status response."""
    job_id: str
    status: str
    progress: int = 0
    result: Optional[dict] = None
    error: Optional[str] = None


class GenerationJobRequest(BaseModel):
    """Request for generation job."""
    rfp_id: str = Field(..., description="RFP ID to generate for")
    section_type: Optional[str] = Field(None, description="Section type (if generating single section)")
    generation_mode: str = Field(default="claude_enhanced", description="Generation mode")
    use_thinking: bool = Field(default=True, description="Enable thinking mode")
    thinking_budget: int = Field(default=10000, ge=1000, le=50000)


@router.post("/generate")
async def start_generation_job(request: GenerationJobRequest) -> JobResponse:
    """
    Start an async proposal generation job.

    Returns job_id for tracking progress.
    """
    try:
        from api.app.core.feature_flags import FeatureFlag, feature_flags

        if not feature_flags.is_enabled(FeatureFlag.CELERY_JOBS):
            raise HTTPException(
                status_code=501,
                detail="Background jobs not enabled. Configure REDIS_URL to enable."
            )

        from api.app.worker.tasks.generation import (
            generate_full_bid,
            generate_proposal_section,
        )

        options = {
            "use_thinking": request.use_thinking,
            "thinking_budget": request.thinking_budget,
        }

        if request.section_type:
            # Generate single section
            task = generate_proposal_section.delay(
                rfp_id=request.rfp_id,
                section_type=request.section_type,
                options=options
            )
        else:
            # Generate full bid
            task = generate_full_bid.delay(
                rfp_id=request.rfp_id,
                generation_mode=request.generation_mode,
                options=options
            )

        return JobResponse(
            job_id=task.id,
            status="pending",
            created_at=datetime.utcnow()
        )

    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="Celery not available. Install celery and redis."
        )
    except Exception as e:
        logger.error(f"Failed to start generation job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}")
async def get_job_status(job_id: str) -> JobStatus:
    """
    Get the status of a background job.

    Returns current progress and result if complete.
    """
    try:
        from api.app.core.feature_flags import FeatureFlag, feature_flags

        if not feature_flags.is_enabled(FeatureFlag.CELERY_JOBS):
            raise HTTPException(
                status_code=501,
                detail="Background jobs not enabled."
            )

        from api.app.worker.celery_app import celery_app

        result = celery_app.AsyncResult(job_id)

        # Map Celery states to our states
        status_map = {
            "PENDING": "pending",
            "STARTED": "running",
            "PROGRESS": "running",
            "SUCCESS": "completed",
            "FAILURE": "failed",
            "REVOKED": "cancelled",
        }

        status = status_map.get(result.status, result.status.lower())

        # Get progress from task meta
        progress = 0
        if result.status == "PROGRESS" and isinstance(result.info, dict):
            progress = result.info.get("progress", 0)
        elif result.ready():
            progress = 100

        # Get result or error
        job_result = None
        error = None

        if result.ready():
            if result.successful():
                job_result = result.result
            else:
                error = str(result.result) if result.result else "Task failed"

        return JobStatus(
            job_id=job_id,
            status=status,
            progress=progress,
            result=job_result,
            error=error
        )

    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="Celery not available."
        )
    except Exception as e:
        logger.error(f"Failed to get job status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{job_id}")
async def cancel_job(job_id: str) -> dict:
    """
    Cancel a running job.

    Note: May not immediately stop in-progress tasks.
    """
    try:
        from api.app.core.feature_flags import FeatureFlag, feature_flags

        if not feature_flags.is_enabled(FeatureFlag.CELERY_JOBS):
            raise HTTPException(
                status_code=501,
                detail="Background jobs not enabled."
            )

        from api.app.worker.celery_app import celery_app

        celery_app.control.revoke(job_id, terminate=True)

        return {
            "status": "cancelled",
            "job_id": job_id,
            "message": "Job cancellation requested"
        }

    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="Celery not available."
        )
    except Exception as e:
        logger.error(f"Failed to cancel job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/evaluate")
async def trigger_alert_evaluation(rfp_id: Optional[str] = None) -> JobResponse:
    """
    Manually trigger alert rule evaluation.

    Can be triggered for a specific RFP or all recent RFPs.
    """
    try:
        from api.app.core.feature_flags import FeatureFlag, feature_flags

        if not feature_flags.is_enabled(FeatureFlag.CELERY_JOBS):
            raise HTTPException(
                status_code=501,
                detail="Background jobs not enabled."
            )

        from api.app.worker.tasks.alerts import evaluate_alert_rules

        task = evaluate_alert_rules.delay(rfp_id=rfp_id)

        return JobResponse(
            job_id=task.id,
            status="pending",
            created_at=datetime.utcnow()
        )

    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="Celery not available."
        )
    except Exception as e:
        logger.error(f"Failed to trigger alert evaluation: {e}")
        raise HTTPException(status_code=500, detail=str(e))
