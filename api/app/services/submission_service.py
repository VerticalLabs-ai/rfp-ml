"""
Submission management service.
"""
import uuid
from datetime import datetime
from typing import Any, Dict, List

from app.models.database import RFPOpportunity, Submission, SubmissionAuditLog, SubmissionStatus
from sqlalchemy.orm import Session


class SubmissionService:
    """Service for submission management operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_queue(
        self,
        status: SubmissionStatus | None = None
    ) -> List[Submission]:
        """Get submission queue."""
        query = self.db.query(Submission)

        if status:
            query = query.filter(Submission.status == status)

        return query.order_by(
            Submission.priority.desc(),
            Submission.deadline.asc()
        ).all()

    def get_submission(self, submission_id: str) -> Submission | None:
        """Get submission by ID."""
        return self.db.query(Submission).filter(
            Submission.submission_id == submission_id
        ).first()

    def create_submission(self, submission_data: Dict[str, Any]) -> Submission:
        """Create a new submission."""
        # Get RFP
        rfp_id_str = submission_data.pop("rfp_id")
        rfp = self.db.query(RFPOpportunity).filter(
            RFPOpportunity.rfp_id == rfp_id_str
        ).first()

        if not rfp:
            raise ValueError(f"RFP not found: {rfp_id_str}")

        # Create submission
        submission = Submission(
            submission_id=str(uuid.uuid4()),
            rfp_id=rfp.id,
            deadline=rfp.response_deadline,
            **submission_data
        )

        self.db.add(submission)
        self.db.commit()
        self.db.refresh(submission)

        # Create audit log
        self._create_audit_log(
            submission.id,
            "submission_created",
            success=True,
            details={"portal": submission.portal}
        )

        return submission

    def retry_submission(self, submission_id: str) -> Submission | None:
        """Retry a failed submission."""
        submission = self.get_submission(submission_id)
        if not submission:
            return None

        if submission.attempts >= submission.max_retries:
            return None  # Max retries exceeded

        submission.status = SubmissionStatus.QUEUED
        submission.attempts += 1
        submission.updated_at = datetime.utcnow()

        self.db.commit()

        self._create_audit_log(
            submission.id,
            "submission_retry",
            success=True,
            details={"attempt": submission.attempts}
        )

        self.db.refresh(submission)
        return submission

    def get_statistics(self) -> Dict[str, Any]:
        """Get submission statistics."""
        total = self.db.query(Submission).count()
        queued = self.db.query(Submission).filter(
            Submission.status == SubmissionStatus.QUEUED
        ).count()
        submitted = self.db.query(Submission).filter(
            Submission.status == SubmissionStatus.SUBMITTED
        ).count()
        confirmed = self.db.query(Submission).filter(
            Submission.status == SubmissionStatus.CONFIRMED
        ).count()
        failed = self.db.query(Submission).filter(
            Submission.status == SubmissionStatus.FAILED
        ).count()

        return {
            "total_submissions": total,
            "queued": queued,
            "submitted": submitted,
            "confirmed": confirmed,
            "failed": failed,
            "success_rate": (confirmed / total * 100) if total > 0 else 0
        }

    def _create_audit_log(
        self,
        submission_id: int,
        event_type: str,
        success: bool,
        details: Dict | None = None,
        error_message: str | None = None
    ):
        """Create audit log entry."""
        log = SubmissionAuditLog(
            submission_id=submission_id,
            event_type=event_type,
            success=success,
            details=details or {},
            error_message=error_message
        )
        self.db.add(log)
        self.db.commit()
