"""
Submission management API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_db
from app.models.database import Submission, SubmissionStatus
from app.services.submission_service import SubmissionService

router = APIRouter()


class SubmissionCreate(BaseModel):
    rfp_id: str
    portal: str
    scheduled_time: Optional[datetime] = None
    priority: int = 0


class SubmissionResponse(BaseModel):
    id: int
    submission_id: str
    rfp_id: int
    portal: str
    status: SubmissionStatus
    scheduled_time: Optional[datetime]
    submitted_at: Optional[datetime]
    confirmed_at: Optional[datetime]
    confirmation_number: Optional[str]
    attempts: int
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/queue", response_model=List[SubmissionResponse])
async def get_submission_queue(
    status: Optional[SubmissionStatus] = None,
    db: Session = Depends(get_db)
):
    """Get submission queue."""
    service = SubmissionService(db)
    submissions = service.get_queue(status=status)
    return submissions


@router.post("", response_model=SubmissionResponse)
async def create_submission(
    submission_data: SubmissionCreate,
    db: Session = Depends(get_db)
):
    """Create a new submission."""
    service = SubmissionService(db)
    submission = service.create_submission(submission_data.dict())
    return submission


@router.get("/{submission_id}", response_model=SubmissionResponse)
async def get_submission(submission_id: str, db: Session = Depends(get_db)):
    """Get submission details."""
    service = SubmissionService(db)
    submission = service.get_submission(submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    return submission


@router.post("/{submission_id}/retry")
async def retry_submission(submission_id: str, db: Session = Depends(get_db)):
    """Retry a failed submission."""
    service = SubmissionService(db)
    submission = service.retry_submission(submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    return {"message": "Submission queued for retry", "submission_id": submission_id}


@router.get("/stats/overview")
async def get_submission_stats(db: Session = Depends(get_db)):
    """Get submission statistics."""
    service = SubmissionService(db)
    stats = service.get_statistics()
    return stats
