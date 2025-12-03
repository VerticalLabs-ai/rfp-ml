"""Compliance matrix API routes."""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.models.database import (
    RFPOpportunity,
    ComplianceRequirement,
    RequirementStatus,
    RequirementType,
)
from app.schemas.compliance import (
    ComplianceRequirementCreate,
    ComplianceRequirementUpdate,
    ComplianceRequirementResponse,
    ComplianceRequirementList,
    BulkStatusUpdate,
    ReorderRequirements,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/compliance", tags=["compliance"])


def get_rfp_or_404(rfp_id: int, db: Session) -> RFPOpportunity:
    """Get RFP by ID or raise 404."""
    rfp = db.query(RFPOpportunity).filter(RFPOpportunity.id == rfp_id).first()
    if not rfp:
        raise HTTPException(status_code=404, detail=f"RFP with id {rfp_id} not found")
    return rfp


def get_requirement_or_404(requirement_id: int, db: Session) -> ComplianceRequirement:
    """Get requirement by ID or raise 404."""
    req = (
        db.query(ComplianceRequirement)
        .filter(ComplianceRequirement.id == requirement_id)
        .first()
    )
    if not req:
        raise HTTPException(
            status_code=404, detail=f"Requirement with id {requirement_id} not found"
        )
    return req


@router.get("/rfps/{rfp_id}/requirements", response_model=ComplianceRequirementList)
async def list_requirements(
    rfp_id: int,
    status_filter: Optional[RequirementStatus] = None,
    type_filter: Optional[RequirementType] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List all requirements for an RFP with optional filtering."""
    get_rfp_or_404(rfp_id, db)

    query = db.query(ComplianceRequirement).filter(
        ComplianceRequirement.rfp_id == rfp_id
    )

    if status_filter:
        query = query.filter(ComplianceRequirement.status == status_filter)
    if type_filter:
        query = query.filter(ComplianceRequirement.requirement_type == type_filter)
    if search:
        query = query.filter(ComplianceRequirement.requirement_text.ilike(f"%{search}%"))

    requirements = query.order_by(ComplianceRequirement.order_index).all()

    # Calculate summary stats
    total = len(requirements)
    completed = sum(1 for r in requirements if r.status == RequirementStatus.COMPLETE)
    in_progress = sum(
        1 for r in requirements if r.status == RequirementStatus.IN_PROGRESS
    )
    not_started = sum(
        1 for r in requirements if r.status == RequirementStatus.NOT_STARTED
    )
    compliance_rate = (completed / total * 100) if total > 0 else 0.0

    return ComplianceRequirementList(
        requirements=requirements,
        total=total,
        completed=completed,
        in_progress=in_progress,
        not_started=not_started,
        compliance_rate=compliance_rate,
    )


@router.post(
    "/rfps/{rfp_id}/requirements",
    response_model=ComplianceRequirementResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_requirement(
    rfp_id: int,
    requirement: ComplianceRequirementCreate,
    db: Session = Depends(get_db),
):
    """Manually add a requirement to an RFP."""
    get_rfp_or_404(rfp_id, db)

    # Get next order index
    max_order = (
        db.query(func.max(ComplianceRequirement.order_index))
        .filter(ComplianceRequirement.rfp_id == rfp_id)
        .scalar()
        or -1
    )

    db_requirement = ComplianceRequirement(
        rfp_id=rfp_id,
        requirement_id=requirement.requirement_id,
        requirement_text=requirement.requirement_text,
        source_document=requirement.source_document,
        source_section=requirement.source_section,
        source_page=requirement.source_page,
        requirement_type=requirement.requirement_type,
        is_mandatory=requirement.is_mandatory,
        status=RequirementStatus.NOT_STARTED,
        order_index=max_order + 1,
    )

    db.add(db_requirement)
    db.commit()
    db.refresh(db_requirement)

    logger.info(f"Created requirement {db_requirement.requirement_id} for RFP {rfp_id}")
    return db_requirement


@router.put(
    "/requirements/{requirement_id}", response_model=ComplianceRequirementResponse
)
async def update_requirement(
    requirement_id: int,
    update: ComplianceRequirementUpdate,
    db: Session = Depends(get_db),
):
    """Update a requirement's status, response, or other fields."""
    requirement = get_requirement_or_404(requirement_id, db)

    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(requirement, field, value)

    db.commit()
    db.refresh(requirement)

    logger.info(f"Updated requirement {requirement_id}: {list(update_data.keys())}")
    return requirement


@router.delete("/requirements/{requirement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_requirement(
    requirement_id: int,
    db: Session = Depends(get_db),
):
    """Delete a requirement."""
    requirement = get_requirement_or_404(requirement_id, db)
    db.delete(requirement)
    db.commit()
    logger.info(f"Deleted requirement {requirement_id}")


@router.put("/rfps/{rfp_id}/requirements/bulk-status")
async def bulk_update_status(
    rfp_id: int,
    update: BulkStatusUpdate,
    db: Session = Depends(get_db),
):
    """Bulk update status for multiple requirements."""
    get_rfp_or_404(rfp_id, db)

    updated = (
        db.query(ComplianceRequirement)
        .filter(
            ComplianceRequirement.id.in_(update.requirement_ids),
            ComplianceRequirement.rfp_id == rfp_id,
        )
        .update({"status": update.status}, synchronize_session=False)
    )

    db.commit()

    logger.info(f"Bulk updated {updated} requirements to status {update.status}")
    return {"updated_count": updated}


@router.put("/rfps/{rfp_id}/requirements/reorder")
async def reorder_requirements(
    rfp_id: int,
    reorder: ReorderRequirements,
    db: Session = Depends(get_db),
):
    """Reorder requirements (for drag-and-drop)."""
    get_rfp_or_404(rfp_id, db)

    for index, req_id in enumerate(reorder.requirement_ids):
        db.query(ComplianceRequirement).filter(
            ComplianceRequirement.id == req_id, ComplianceRequirement.rfp_id == rfp_id
        ).update({"order_index": index}, synchronize_session=False)

    db.commit()

    logger.info(
        f"Reordered {len(reorder.requirement_ids)} requirements for RFP {rfp_id}"
    )
    return {"reordered_count": len(reorder.requirement_ids)}
