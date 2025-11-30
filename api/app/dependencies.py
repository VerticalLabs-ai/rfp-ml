"""
Shared FastAPI dependencies for RFP routes.

Provides reusable dependency injection functions to eliminate code duplication
across route handlers.
"""
from typing import Annotated, Any

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.database import RFPOpportunity
from app.services.rfp_service import RFPService


def get_rfp_service(db: Session = Depends(get_db)) -> RFPService:
    """Dependency to get RFP service instance."""
    return RFPService(db)


def get_rfp_or_404(
    rfp_id: str,
    db: Session = Depends(get_db)
) -> RFPOpportunity:
    """
    Dependency that fetches an RFP by ID or raises 404.

    Usage:
        @router.get("/{rfp_id}")
        async def get_rfp(rfp: RFPOpportunity = Depends(get_rfp_or_404)):
            return rfp_to_dict(rfp)
    """
    service = RFPService(db)
    rfp = service.get_rfp_by_id(rfp_id)
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")
    return rfp


# Type alias for cleaner route signatures
RFPDep = Annotated[RFPOpportunity, Depends(get_rfp_or_404)]
DBDep = Annotated[Session, Depends(get_db)]
RFPServiceDep = Annotated[RFPService, Depends(get_rfp_service)]


def rfp_to_dict(rfp: RFPOpportunity) -> dict[str, Any]:
    """
    Convert RFP model to dictionary for API responses.

    Centralizes the RFP-to-dict conversion logic that was duplicated
    across multiple route handlers.
    """
    return {
        "rfp_id": rfp.rfp_id,
        "id": rfp.id,
        "title": rfp.title,
        "agency": rfp.agency,
        "solicitation_number": rfp.solicitation_number,
        "description": rfp.description,
        "category": rfp.category,
        "naics_code": rfp.naics_code,
        "current_stage": rfp.current_stage.value if hasattr(rfp.current_stage, 'value') else str(rfp.current_stage),
        "triage_score": rfp.triage_score,
        "overall_score": rfp.overall_score,
        "decision_recommendation": rfp.decision_recommendation,
        "response_deadline": rfp.response_deadline.isoformat() if rfp.response_deadline else None,
        "discovered_at": rfp.discovered_at.isoformat() if rfp.discovered_at else None,
        "updated_at": rfp.updated_at.isoformat() if rfp.updated_at else None,
    }


def rfp_to_processing_dict(rfp: RFPOpportunity) -> dict[str, Any]:
    """
    Convert RFP model to dictionary for ML processing.

    Subset of fields needed for RAG, pricing, and document generation.
    """
    return {
        "rfp_id": rfp.rfp_id,
        "title": rfp.title,
        "agency": rfp.agency,
        "solicitation_number": rfp.solicitation_number,
        "description": rfp.description,
        "category": rfp.category,
        "naics_code": rfp.naics_code,
        "response_deadline": rfp.response_deadline.isoformat() if rfp.response_deadline else None,
    }
