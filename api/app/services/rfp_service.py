"""
RFP business logic service.
"""
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.models.database import RFPOpportunity, PipelineStage, PipelineEvent, PostAwardChecklist
from src.compliance.compliance_checklist import compliance_checklist_generator
from app.services.rfp_processor import processor


class RFPService:
    """Service for RFP management operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_discovered_rfps(
        self,
        skip: int = 0,
        limit: int = 100,
        category: Optional[str] = None,
        min_score: Optional[float] = None
    ) -> List[RFPOpportunity]:
        """Get list of discovered RFPs with filtering."""
        query = self.db.query(RFPOpportunity)

        if category:
            query = query.filter(RFPOpportunity.category == category)

        if min_score is not None:
            query = query.filter(RFPOpportunity.triage_score >= min_score)

        query = query.order_by(RFPOpportunity.triage_score.desc())

        return query.offset(skip).limit(limit).all()

    def get_rfp_by_id(self, rfp_id: str) -> Optional[RFPOpportunity]:
        """Get RFP by ID."""
        return self.db.query(RFPOpportunity).filter(
            RFPOpportunity.rfp_id == rfp_id
        ).first()

    def create_rfp(self, rfp_data: Dict[str, Any]) -> RFPOpportunity:
        """Create a new RFP entry."""
        rfp = RFPOpportunity(**rfp_data)
        self.db.add(rfp)
        self.db.commit()
        self.db.refresh(rfp)

        # Create pipeline event
        self._create_pipeline_event(
            rfp.id,
            None,
            PipelineStage.DISCOVERED,
            automated=True
        )

        return rfp

    def update_rfp(
        self,
        rfp_id: str,
        update_data: Dict[str, Any]
    ) -> Optional[RFPOpportunity]:
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
        self,
        rfp_id: str,
        decision: str,
        notes: Optional[str] = None
    ) -> Optional[RFPOpportunity]:
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
            rfp.id,
            old_stage,
            rfp.current_stage,
            automated=False,
            notes=notes
        )

        self.db.refresh(rfp)
        return rfp

    def advance_stage(
        self,
        rfp_id: str,
        notes: Optional[str] = None
    ) -> Optional[RFPOpportunity]:
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
            PipelineStage.SUBMITTED: PipelineStage.AWARDED, # Added for post-award
        }

        next_stage = stage_progression.get(rfp.current_stage)
        if not next_stage:
            return rfp  # Already at final stage or no clear next step

        rfp.current_stage = next_stage
        rfp.updated_at = datetime.utcnow()
        self.db.commit()

        # If RFP is awarded, generate post-award compliance checklist
        if next_stage == PipelineStage.AWARDED:
            print(f"RFP {rfp_id} moved to AWARDED stage. Generating post-award checklist.")
            # Retrieve bid document content
            bid_document_id = rfp.bid_document.document_id if rfp.bid_document else None
            if bid_document_id:
                bid_content = processor.get_bid_document(bid_document_id)
                if bid_content:
                    checklist_obj = compliance_checklist_generator.generate_from_bid_document(rfp.to_dict(), bid_content)
                    
                    # Save to database
                    post_award_checklist_db = PostAwardChecklist(
                        rfp_id=rfp.id,
                        bid_document_id=bid_document_id,
                        generated_at=checklist_obj.generated_at,
                        status=checklist_obj.status,
                        items=[item.to_dict() for item in checklist_obj.items], # Assuming ChecklistItem has a to_dict method
                        summary=checklist_obj.summary
                    )
                    self.db.add(post_award_checklist_db)
                    self.db.commit()
                    self.db.refresh(post_award_checklist_db)

                    print(f"Post-award checklist generated and saved to DB for RFP {rfp_id}.")
                else:
                    print(f"Warning: Bid document content not found for RFP {rfp_id}. Cannot generate checklist.")
            else:
                print(f"Warning: No bid document associated with RFP {rfp_id}. Cannot generate checklist.")

        self._create_pipeline_event(
            rfp.id,
            old_stage,
            next_stage,
            automated=True,
            notes=notes
        )

        self.db.refresh(rfp)
        return rfp

    def get_statistics(self) -> Dict[str, Any]:
        """Get RFP statistics."""
        total = self.db.query(RFPOpportunity).count()
        in_pipeline = self.db.query(RFPOpportunity).filter(
            RFPOpportunity.current_stage.notin_([
                PipelineStage.REJECTED,
                PipelineStage.SUBMITTED
            ])
        ).count()

        approved = self.db.query(RFPOpportunity).filter(
            RFPOpportunity.current_stage == PipelineStage.APPROVED
        ).count()

        rejected = self.db.query(RFPOpportunity).filter(
            RFPOpportunity.current_stage == PipelineStage.REJECTED
        ).count()

        submitted = self.db.query(RFPOpportunity).filter(
            RFPOpportunity.current_stage == PipelineStage.SUBMITTED
        ).count()

        pending_review = self.db.query(RFPOpportunity).filter(
            RFPOpportunity.current_stage.in_([
                PipelineStage.REVIEW,
                PipelineStage.DECISION_PENDING
            ])
        ).count()

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
        from_stage: Optional[PipelineStage],
        to_stage: PipelineStage,
        automated: bool = True,
        user: Optional[str] = None,
        notes: Optional[str] = None
    ):
        """Create a pipeline event record."""
        event = PipelineEvent(
            rfp_id=rfp_id,
            from_stage=from_stage,
            to_stage=to_stage,
            automated=automated,
            user=user,
            notes=notes
        )
        self.db.add(event)
        self.db.commit()
