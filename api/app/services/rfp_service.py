"""
RFP business logic service.
"""

import logging
from datetime import datetime
from typing import Any

from app.models.database import (
    PipelineEvent,
    PipelineStage,
    PostAwardChecklist,
    RFPOpportunity,
)
from app.services.rfp_processor import processor
from sqlalchemy.orm import Session

from src.compliance.compliance_checklist import compliance_checklist_generator

logger = logging.getLogger(__name__)


class RFPService:
    """Service for RFP management operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_discovered_rfps(
        self,
        skip: int = 0,
        limit: int = 100,
        category: str | None = None,
        min_score: float | None = None,
        search: str | None = None,
        sort_by: str = "score",
    ) -> list[RFPOpportunity]:
        """Get list of discovered RFPs with filtering and search.

        Args:
            skip: Number of records to skip (pagination)
            limit: Max records to return
            category: Filter by category
            min_score: Filter by minimum triage score
            search: Search term to match against title, description, agency, naics_code
            sort_by: Sort order - 'score', 'deadline', or 'recent'
        """
        from sqlalchemy import or_

        query = self.db.query(RFPOpportunity)

        # Search filter - search across multiple fields
        if search and search.strip():
            search_term = f"%{search.strip().lower()}%"
            query = query.filter(
                or_(
                    RFPOpportunity.title.ilike(search_term),
                    RFPOpportunity.description.ilike(search_term),
                    RFPOpportunity.agency.ilike(search_term),
                    RFPOpportunity.naics_code.ilike(search_term),
                    RFPOpportunity.category.ilike(search_term),
                    RFPOpportunity.office.ilike(search_term),
                    RFPOpportunity.solicitation_number.ilike(search_term),
                )
            )

        if category and category != "all":
            query = query.filter(RFPOpportunity.category == category)

        if min_score is not None:
            query = query.filter(RFPOpportunity.triage_score >= min_score)

        # Apply sorting
        if sort_by == "deadline":
            query = query.order_by(RFPOpportunity.response_deadline.asc().nullslast())
        elif sort_by == "recent":
            query = query.order_by(RFPOpportunity.created_at.desc().nullslast())
        else:  # Default to score
            query = query.order_by(RFPOpportunity.triage_score.desc().nullslast())

        return query.offset(skip).limit(limit).all()

    def get_rfp_by_id(self, rfp_id: str) -> RFPOpportunity | None:
        """Get RFP by ID."""
        return (
            self.db.query(RFPOpportunity)
            .filter(RFPOpportunity.rfp_id == rfp_id)
            .first()
        )

    def create_rfp(self, rfp_data: dict[str, Any]) -> RFPOpportunity:
        """Create a new RFP entry."""
        rfp = RFPOpportunity(**rfp_data)
        self.db.add(rfp)
        self.db.commit()
        self.db.refresh(rfp)

        # Create pipeline event
        self._create_pipeline_event(
            rfp.id, None, PipelineStage.DISCOVERED, automated=True
        )

        return rfp

    def update_rfp(
        self, rfp_id: str, update_data: dict[str, Any]
    ) -> RFPOpportunity | None:
        """Update RFP details."""
        rfp = self.get_rfp_by_id(rfp_id)
        if not rfp:
            return None

        for key, value in update_data.items():
            setattr(rfp, key, value)

        rfp.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(rfp)

        return rfp

    def update_triage_decision(
        self, rfp_id: str, decision: str, notes: str | None = None
    ) -> RFPOpportunity | None:
        """Update triage decision and advance stage."""
        rfp = self.get_rfp_by_id(rfp_id)
        if not rfp:
            return None

        old_stage = rfp.current_stage

        if decision == "approve":
            rfp.current_stage = PipelineStage.ANALYZING
        elif decision == "reject":
            rfp.current_stage = PipelineStage.REJECTED
        elif decision == "flag":
            rfp.current_stage = PipelineStage.REVIEW

        rfp.updated_at = datetime.utcnow()
        self.db.commit()

        # Create pipeline event
        self._create_pipeline_event(
            rfp.id, old_stage, rfp.current_stage, automated=False, notes=notes
        )

        self.db.refresh(rfp)
        return rfp

    def advance_stage(
        self, rfp_id: str, notes: str | None = None
    ) -> RFPOpportunity | None:
        """Advance RFP to next pipeline stage."""
        rfp = self.get_rfp_by_id(rfp_id)
        if not rfp:
            return None

        old_stage = rfp.current_stage

        # Define stage progression
        stage_progression = {
            PipelineStage.DISCOVERED: PipelineStage.TRIAGED,
            PipelineStage.TRIAGED: PipelineStage.ANALYZING,
            PipelineStage.ANALYZING: PipelineStage.PRICING,
            PipelineStage.PRICING: PipelineStage.DECISION_PENDING,
            PipelineStage.DECISION_PENDING: PipelineStage.APPROVED,
            PipelineStage.APPROVED: PipelineStage.DOCUMENT_GENERATION,
            PipelineStage.DOCUMENT_GENERATION: PipelineStage.REVIEW,
            PipelineStage.REVIEW: PipelineStage.SUBMISSION_READY,
            PipelineStage.SUBMISSION_READY: PipelineStage.SUBMITTED,
            PipelineStage.SUBMITTED: PipelineStage.AWARDED,  # Added for post-award
        }

        next_stage = stage_progression.get(rfp.current_stage)
        if not next_stage:
            return rfp  # Already at final stage or no clear next step

        rfp.current_stage = next_stage
        rfp.updated_at = datetime.utcnow()
        self.db.commit()

        # If RFP is awarded, generate post-award compliance checklist
        if next_stage == PipelineStage.AWARDED:
            logger.info(
                "RFP %s moved to AWARDED stage. Generating post-award checklist.",
                rfp_id,
            )
            # Retrieve bid document content
            bid_document_id = rfp.bid_document.document_id if rfp.bid_document else None
            if bid_document_id:
                bid_content = processor.get_bid_document(bid_document_id)
                if bid_content:
                    checklist_obj = (
                        compliance_checklist_generator.generate_from_bid_document(
                            rfp.to_dict(), bid_content
                        )
                    )

                    # Save to database
                    post_award_checklist_db = PostAwardChecklist(
                        rfp_id=rfp.id,
                        bid_document_id=bid_document_id,
                        generated_at=checklist_obj.generated_at,
                        status=checklist_obj.status,
                        items=[item.to_dict() for item in checklist_obj.items],
                        summary=checklist_obj.summary,
                    )
                    self.db.add(post_award_checklist_db)
                    self.db.commit()
                    self.db.refresh(post_award_checklist_db)

                    logger.info(
                        "Post-award checklist generated and saved to DB for RFP %s.",
                        rfp_id,
                    )
                else:
                    logger.warning(
                        "Bid document content not found for RFP %s. Cannot generate checklist.",
                        rfp_id,
                    )
            else:
                logger.warning(
                    "No bid document associated with RFP %s. Cannot generate checklist.",
                    rfp_id,
                )

        self._create_pipeline_event(
            rfp.id, old_stage, next_stage, automated=True, notes=notes
        )

        self.db.refresh(rfp)
        return rfp

    def get_statistics(self) -> dict[str, Any]:
        """Get RFP statistics using optimized GROUP BY query."""
        from sqlalchemy import func

        # Single query with GROUP BY instead of 6 separate COUNT queries
        stage_counts = dict(
            self.db.query(
                RFPOpportunity.current_stage,
                func.count(RFPOpportunity.id)
            )
            .group_by(RFPOpportunity.current_stage)
            .all()
        )

        # Calculate derived statistics from the grouped counts
        total = sum(stage_counts.values())

        approved = stage_counts.get(PipelineStage.APPROVED, 0)
        rejected = stage_counts.get(PipelineStage.REJECTED, 0)
        submitted = stage_counts.get(PipelineStage.SUBMITTED, 0)

        pending_review = (
            stage_counts.get(PipelineStage.REVIEW, 0)
            + stage_counts.get(PipelineStage.DECISION_PENDING, 0)
        )

        in_pipeline = total - rejected - submitted

        return {
            "total_discovered": total,
            "in_pipeline": in_pipeline,
            "approved_count": approved,
            "rejected_count": rejected,
            "submitted_count": submitted,
            "pending_reviews": pending_review,
        }

    def _create_pipeline_event(
        self,
        rfp_id: int,
        from_stage: PipelineStage | None,
        to_stage: PipelineStage,
        automated: bool = True,
        user: str | None = None,
        notes: str | None = None,
    ):
        """Create a pipeline event record."""
        event = PipelineEvent(
            rfp_id=rfp_id,
            from_stage=from_stage,
            to_stage=to_stage,
            automated=automated,
            user=user,
            notes=notes,
        )
        self.db.add(event)
        self.db.commit()
