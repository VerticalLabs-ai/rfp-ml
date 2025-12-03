"""
Submission Agent: Autonomous bid submission to government portals.
"""
import json
import logging
import os
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum

from src.config.paths import PathConfig

logger = logging.getLogger(__name__)


class SubmissionStatus(Enum):
    """Submission status enumeration."""
    QUEUED = "queued"
    VALIDATING = "validating"
    FORMATTING = "formatting"
    SUBMITTING = "submitting"
    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    REJECTED = "rejected"


@dataclass
class SubmissionJob:
    """Submission job data model."""
    job_id: str
    rfp_id: str
    bid_document_id: str
    portal: str
    deadline: datetime
    priority: int
    status: SubmissionStatus
    attempts: int = 0
    max_retries: int = 3
    created_at: datetime | None = None
    submitted_at: datetime | None = None
    confirmed_at: datetime | None = None
    error_message: str | None = None
    confirmation_number: str | None = None
    metadata: dict | None = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.metadata is None:
            self.metadata = {}


class SubmissionAgent:
    """
    Autonomous agent for bid submission to government portals.

    Handles:
    - Queue management
    - Portal-specific submission logic
    - Retry with exponential backoff
    - Confirmation tracking
    - Notification dispatch
    """

    def __init__(
        self,
        document_generator=None,
        notification_service=None,
        max_concurrent_submissions: int = 5,
        data_dir: str | None = None
    ):
        """
        Initialize Submission Agent.

        Args:
            document_generator: Document generator instance
            notification_service: Notification service instance
            max_concurrent_submissions: Max parallel submissions
            data_dir: Data directory path
        """
        # Ensure PathConfig directories are initialized
        PathConfig.ensure_directories()

        self.document_generator = document_generator
        self.notification_service = notification_service
        self.max_concurrent = max_concurrent_submissions
        self.data_dir = data_dir or str(PathConfig.DATA_DIR)

        # Submission queue
        self.queue: list[SubmissionJob] = []
        self.active_submissions: dict[str, SubmissionJob] = {}

        # Portal adapters
        self.portal_adapters = {}
        self._initialize_adapters()

        # Output directories
        self.submission_dir = os.path.join(data_dir, "submissions")
        self.audit_dir = os.path.join(data_dir, "submission_audits")
        os.makedirs(self.submission_dir, exist_ok=True)
        os.makedirs(self.audit_dir, exist_ok=True)

        logger.info(f"SubmissionAgent initialized with max {self.max_concurrent} concurrent submissions")

    def _initialize_adapters(self):
        """Initialize portal adapters."""
        from src.agents.portal_adapters import MockPortalAdapter, SAMGovAdapter

        # Initialize available portal adapters
        try:
            sam_api_key = os.getenv("SAM_GOV_API_KEY")
            if sam_api_key:
                self.portal_adapters["sam.gov"] = SAMGovAdapter(sam_api_key)
                logger.info("SAM.gov adapter initialized")
        except Exception as e:
            logger.warning(f"Could not initialize SAM.gov adapter: {e}")

        # Mock adapter for testing
        self.portal_adapters["mock"] = MockPortalAdapter()
        logger.info("Mock portal adapter initialized")

    def submit_bid(
        self,
        rfp_data: dict,
        bid_document: dict,
        portal: str,
        scheduled_time: datetime | None = None,
        priority: int = 0
    ) -> SubmissionJob:
        """
        Submit a bid to the specified portal.

        Args:
            rfp_data: RFP data dictionary
            bid_document: Generated bid document
            portal: Target portal name
            scheduled_time: Optional scheduled submission time
            priority: Priority level (higher = more urgent)

        Returns:
            SubmissionJob instance
        """
        # Create submission job
        job = SubmissionJob(
            job_id=str(uuid.uuid4()),
            rfp_id=rfp_data.get("rfp_id", str(uuid.uuid4())),
            bid_document_id=bid_document.get("document_id", str(uuid.uuid4())),
            portal=portal,
            deadline=rfp_data.get("response_deadline", datetime.now(timezone.utc) + timedelta(days=7)),
            priority=priority,
            status=SubmissionStatus.QUEUED
        )

        # Add to queue
        self.queue.append(job)
        self.queue.sort(key=lambda x: (x.priority, x.deadline), reverse=True)

        logger.info(f"Submission job {job.job_id} queued for portal {portal}")

        # Log audit event
        self._log_audit_event(
            job.job_id,
            "job_created",
            success=True,
            details={"portal": portal, "rfp_id": job.rfp_id}
        )

        # Send notification
        if self.notification_service:
            self.notification_service.send_notification(
                "Submission Queued",
                f"Bid for RFP {job.rfp_id} queued for submission to {portal}"
            )

        return job

    def validate_submission(self, job: SubmissionJob, bid_document: dict) -> tuple[bool, list[str]]:
        """
        Validate bid meets portal requirements.

        Args:
            job: Submission job
            bid_document: Bid document to validate

        Returns:
            Tuple of (is_valid, error_messages)
        """
        job.status = SubmissionStatus.VALIDATING

        adapter = self.portal_adapters.get(job.portal)
        if not adapter:
            return False, [f"No adapter available for portal: {job.portal}"]

        try:
            errors = adapter.validate_requirements(bid_document)
            is_valid = len(errors) == 0

            if not is_valid:
                logger.warning(f"Validation failed for job {job.job_id}: {errors}")
                self._log_audit_event(
                    job.job_id,
                    "validation_failed",
                    success=False,
                    details={"errors": errors}
                )
            else:
                logger.info(f"Validation passed for job {job.job_id}")
                self._log_audit_event(
                    job.job_id,
                    "validation_passed",
                    success=True
                )

            return is_valid, errors

        except Exception as e:
            logger.error(f"Validation error for job {job.job_id}: {e}")
            return False, [str(e)]

    def process_queue(self):
        """Process pending submissions from the queue."""
        logger.info(f"Processing submission queue ({len(self.queue)} jobs pending)")

        while self.queue and len(self.active_submissions) < self.max_concurrent:
            job = self.queue.pop(0)

            # Check if deadline passed
            if job.deadline and job.deadline < datetime.now(timezone.utc):
                logger.error(f"Job {job.job_id} deadline passed, marking as failed")
                job.status = SubmissionStatus.FAILED
                job.error_message = "Deadline passed"
                self._save_job_state(job)
                continue

            # Process submission
            try:
                self._process_submission(job)
            except Exception as e:
                logger.error(f"Error processing job {job.job_id}: {e}")
                job.status = SubmissionStatus.FAILED
                job.error_message = str(e)
                self._save_job_state(job)

    def _process_submission(self, job: SubmissionJob):
        """Process a single submission."""
        logger.info(f"Processing submission job {job.job_id}")

        # Move to active submissions
        self.active_submissions[job.job_id] = job

        # Simulate bid document retrieval (in real implementation, load from database)
        bid_document = {
            "document_id": job.bid_document_id,
            "rfp_id": job.rfp_id,
            "format": "PDF",
            "content": "Mock bid document content"
        }

        # Validate
        is_valid, errors = self.validate_submission(job, bid_document)
        if not is_valid:
            job.status = SubmissionStatus.FAILED
            job.error_message = "; ".join(errors)
            self._save_job_state(job)
            del self.active_submissions[job.job_id]
            return

        # Format for portal
        job.status = SubmissionStatus.FORMATTING
        adapter = self.portal_adapters[job.portal]

        try:
            formatted_data = adapter.format_submission(bid_document)
        except Exception as e:
            logger.error(f"Formatting failed for job {job.job_id}: {e}")
            job.status = SubmissionStatus.FAILED
            job.error_message = f"Formatting error: {e}"
            self._save_job_state(job)
            del self.active_submissions[job.job_id]
            return

        # Submit
        job.status = SubmissionStatus.SUBMITTING
        job.submitted_at = datetime.now(timezone.utc)

        try:
            result = adapter.submit(formatted_data)
            job.confirmation_number = result.get("confirmation_number")
            job.status = SubmissionStatus.SUBMITTED
            job.confirmed_at = datetime.now(timezone.utc)

            logger.info(f"Submission {job.job_id} successful. Confirmation: {job.confirmation_number}")

            self._log_audit_event(
                job.job_id,
                "submission_successful",
                success=True,
                details={"confirmation": job.confirmation_number}
            )

            # Notify
            if self.notification_service:
                self.notification_service.send_notification(
                    "Submission Successful",
                    f"Bid for RFP {job.rfp_id} submitted successfully. Confirmation: {job.confirmation_number}"
                )

        except Exception as e:
            logger.error(f"Submission failed for job {job.job_id}: {e}")
            job.status = SubmissionStatus.FAILED
            job.error_message = str(e)
            job.attempts += 1

            self._log_audit_event(
                job.job_id,
                "submission_failed",
                success=False,
                details={"error": str(e), "attempt": job.attempts}
            )

            # Retry if attempts left
            if job.attempts < job.max_retries:
                logger.info(f"Queueing job {job.job_id} for retry (attempt {job.attempts}/{job.max_retries})")
                job.status = SubmissionStatus.QUEUED
                self.queue.append(job)

        # Save final state
        self._save_job_state(job)

        # Remove from active
        del self.active_submissions[job.job_id]

    def retry_failed_submission(self, job_id: str):
        """Retry a failed submission."""
        # Load job from disk
        job = self._load_job_state(job_id)
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        if job.attempts >= job.max_retries:
            logger.error(f"Job {job_id} max retries exceeded")
            return

        job.status = SubmissionStatus.QUEUED
        self.queue.append(job)
        logger.info(f"Job {job_id} queued for retry")

    def get_job_status(self, job_id: str) -> dict | None:
        """Get status of a submission job."""
        job = self._load_job_state(job_id)
        if job:
            return asdict(job)
        return None

    def _save_job_state(self, job: SubmissionJob):
        """Save job state to disk."""
        job_file = os.path.join(self.submission_dir, f"{job.job_id}.json")
        with open(job_file, 'w') as f:
            json.dump(asdict(job), f, default=str, indent=2)

    def _load_job_state(self, job_id: str) -> SubmissionJob | None:
        """Load job state from disk."""
        job_file = os.path.join(self.submission_dir, f"{job_id}.json")
        if not os.path.exists(job_file):
            return None

        with open(job_file) as f:
            data = json.load(f)

        # Convert string dates back to datetime
        for date_field in ['created_at', 'submitted_at', 'confirmed_at', 'deadline']:
            if data.get(date_field):
                data[date_field] = datetime.fromisoformat(data[date_field])

        data['status'] = SubmissionStatus(data['status'])
        return SubmissionJob(**data)

    def _log_audit_event(
        self,
        job_id: str,
        event_type: str,
        success: bool,
        details: dict | None = None
    ):
        """Log audit event."""
        audit_log = {
            "job_id": job_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "success": success,
            "details": details or {}
        }

        audit_file = os.path.join(self.audit_dir, f"{job_id}_audit.jsonl")
        with open(audit_file, 'a') as f:
            f.write(json.dumps(audit_log) + '\n')
