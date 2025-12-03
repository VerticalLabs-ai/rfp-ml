"""Saved RFPs API routes."""
import logging
from collections import Counter

from app.core.database import get_db
from app.models.database import RFPOpportunity, SavedRfp
from app.schemas.saved_rfps import (
    BulkDeleteRequest,
    BulkSaveRequest,
    SavedRfpCreate,
    SavedRfpList,
    SavedRfpResponse,
    SavedRfpUpdate,
    SavedRfpWithRfp,
    TagsList,
)
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/saved-rfps", tags=["saved-rfps"])

# Default user ID (will be replaced with auth later)
DEFAULT_USER_ID = "default"


def get_saved_rfp_or_404(saved_id: int, db: Session, user_id: str = DEFAULT_USER_ID) -> SavedRfp:
    """Get saved RFP by ID or raise 404."""
    saved = (
        db.query(SavedRfp)
        .filter(SavedRfp.id == saved_id, SavedRfp.user_id == user_id)
        .first()
    )
    if not saved:
        raise HTTPException(status_code=404, detail=f"Saved RFP {saved_id} not found")
    return saved


def get_rfp_or_404(rfp_id: int, db: Session) -> RFPOpportunity:
    """Get RFP by ID or raise 404."""
    rfp = db.query(RFPOpportunity).filter(RFPOpportunity.id == rfp_id).first()
    if not rfp:
        raise HTTPException(status_code=404, detail=f"RFP {rfp_id} not found")
    return rfp


@router.get("", response_model=SavedRfpList)
async def list_saved_rfps(
    tag: str | None = Query(None, description="Filter by tag"),
    folder: str | None = Query(None, description="Filter by folder"),
    search: str | None = Query(None, description="Search in notes"),
    sort_by: str = Query("saved_at", description="Sort field: saved_at, deadline, title"),
    sort_order: str = Query("desc", description="Sort order: asc, desc"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List all saved RFPs for the current user with optional filtering."""
    user_id = DEFAULT_USER_ID

    # Base query with join to RFP
    query = (
        db.query(SavedRfp, RFPOpportunity)
        .join(RFPOpportunity, SavedRfp.rfp_id == RFPOpportunity.id)
        .filter(SavedRfp.user_id == user_id)
    )

    # Apply filters
    if tag:
        # JSON array contains (SQLite compatible)
        query = query.filter(SavedRfp.tags.contains(f'"{tag}"'))
    if folder:
        query = query.filter(SavedRfp.folder == folder)
    if search:
        query = query.filter(SavedRfp.notes.ilike(f"%{search}%"))

    # Get total before pagination
    total = query.count()

    # Apply sorting
    if sort_by == "deadline":
        sort_col = RFPOpportunity.response_deadline
    elif sort_by == "title":
        sort_col = RFPOpportunity.title
    else:
        sort_col = SavedRfp.saved_at

    if sort_order == "asc":
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())

    # Paginate
    results = query.offset(skip).limit(limit).all()

    # Build response with RFP details
    saved_rfps = []
    all_tags = []
    all_folders = []

    for saved, rfp in results:
        saved_rfps.append(SavedRfpWithRfp(
            id=saved.id,
            rfp_id=saved.rfp_id,
            user_id=saved.user_id,
            notes=saved.notes,
            tags=saved.tags or [],
            folder=saved.folder,
            saved_at=saved.saved_at,
            updated_at=saved.updated_at,
            rfp_title=rfp.title,
            rfp_agency=rfp.agency,
            rfp_deadline=rfp.response_deadline,
            rfp_stage=rfp.current_stage.value if rfp.current_stage else None,
            rfp_triage_score=rfp.triage_score,
        ))
        all_tags.extend(saved.tags or [])
        if saved.folder:
            all_folders.append(saved.folder)

    return SavedRfpList(
        saved_rfps=saved_rfps,
        total=total,
        tags_summary=dict(Counter(all_tags)),
        folders_summary=dict(Counter(all_folders)),
    )


@router.post("", response_model=SavedRfpResponse, status_code=status.HTTP_201_CREATED)
async def save_rfp(
    data: SavedRfpCreate,
    db: Session = Depends(get_db),
):
    """Save an RFP to the user's saved list."""
    user_id = DEFAULT_USER_ID

    # Verify RFP exists
    get_rfp_or_404(data.rfp_id, db)

    # Check if already saved
    existing = (
        db.query(SavedRfp)
        .filter(SavedRfp.rfp_id == data.rfp_id, SavedRfp.user_id == user_id)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail="RFP is already saved. Use PUT to update."
        )

    saved = SavedRfp(
        rfp_id=data.rfp_id,
        user_id=user_id,
        notes=data.notes,
        tags=data.tags,
        folder=data.folder,
    )

    db.add(saved)
    db.commit()
    db.refresh(saved)

    logger.info(f"User {user_id} saved RFP {data.rfp_id}")
    return saved


@router.get("/check/{rfp_id}")
async def check_if_saved(
    rfp_id: int,
    db: Session = Depends(get_db),
):
    """Check if an RFP is saved by the current user."""
    user_id = DEFAULT_USER_ID

    saved = (
        db.query(SavedRfp)
        .filter(SavedRfp.rfp_id == rfp_id, SavedRfp.user_id == user_id)
        .first()
    )

    return {
        "is_saved": saved is not None,
        "saved_rfp_id": saved.id if saved else None,
    }


@router.get("/tags", response_model=TagsList)
async def list_tags(
    db: Session = Depends(get_db),
):
    """List all tags used by the current user."""
    user_id = DEFAULT_USER_ID

    saved_rfps = db.query(SavedRfp).filter(SavedRfp.user_id == user_id).all()

    all_tags = []
    for saved in saved_rfps:
        all_tags.extend(saved.tags or [])

    tag_counts = dict(Counter(all_tags))
    unique_tags = sorted(tag_counts.keys())

    return TagsList(tags=unique_tags, counts=tag_counts)


@router.get("/{saved_id}", response_model=SavedRfpResponse)
async def get_saved_rfp(
    saved_id: int,
    db: Session = Depends(get_db),
):
    """Get a specific saved RFP."""
    return get_saved_rfp_or_404(saved_id, db)


@router.put("/{saved_id}", response_model=SavedRfpResponse)
async def update_saved_rfp(
    saved_id: int,
    data: SavedRfpUpdate,
    db: Session = Depends(get_db),
):
    """Update a saved RFP's notes, tags, or folder."""
    saved = get_saved_rfp_or_404(saved_id, db)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(saved, field, value)

    db.commit()
    db.refresh(saved)

    logger.info(f"Updated saved RFP {saved_id}: {list(update_data.keys())}")
    return saved


@router.delete("/{saved_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unsave_rfp(
    saved_id: int,
    db: Session = Depends(get_db),
):
    """Remove an RFP from saved list."""
    saved = get_saved_rfp_or_404(saved_id, db)
    db.delete(saved)
    db.commit()
    logger.info(f"Unsaved RFP {saved.rfp_id}")


@router.delete("/by-rfp/{rfp_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unsave_rfp_by_rfp_id(
    rfp_id: int,
    db: Session = Depends(get_db),
):
    """Remove an RFP from saved list by RFP ID (convenience endpoint)."""
    user_id = DEFAULT_USER_ID

    saved = (
        db.query(SavedRfp)
        .filter(SavedRfp.rfp_id == rfp_id, SavedRfp.user_id == user_id)
        .first()
    )
    if not saved:
        raise HTTPException(status_code=404, detail=f"RFP {rfp_id} is not saved")

    db.delete(saved)
    db.commit()
    logger.info(f"Unsaved RFP {rfp_id}")


@router.post("/bulk", status_code=status.HTTP_201_CREATED)
async def bulk_save_rfps(
    data: BulkSaveRequest,
    db: Session = Depends(get_db),
):
    """Save multiple RFPs at once."""
    user_id = DEFAULT_USER_ID

    saved_count = 0
    skipped_count = 0

    for rfp_id in data.rfp_ids:
        # Check if RFP exists
        rfp = db.query(RFPOpportunity).filter(RFPOpportunity.id == rfp_id).first()
        if not rfp:
            skipped_count += 1
            continue

        # Check if already saved
        existing = (
            db.query(SavedRfp)
            .filter(SavedRfp.rfp_id == rfp_id, SavedRfp.user_id == user_id)
            .first()
        )
        if existing:
            skipped_count += 1
            continue

        saved = SavedRfp(
            rfp_id=rfp_id,
            user_id=user_id,
            tags=data.tags,
            folder=data.folder,
        )
        db.add(saved)
        saved_count += 1

    db.commit()
    logger.info(f"Bulk saved {saved_count} RFPs, skipped {skipped_count}")

    return {"saved_count": saved_count, "skipped_count": skipped_count}


@router.delete("/bulk")
async def bulk_unsave_rfps(
    data: BulkDeleteRequest,
    db: Session = Depends(get_db),
):
    """Remove multiple saved RFPs at once."""
    user_id = DEFAULT_USER_ID

    deleted = (
        db.query(SavedRfp)
        .filter(
            SavedRfp.id.in_(data.saved_rfp_ids),
            SavedRfp.user_id == user_id,
        )
        .delete(synchronize_session=False)
    )

    db.commit()
    logger.info(f"Bulk unsaved {deleted} RFPs")

    return {"deleted_count": deleted}
