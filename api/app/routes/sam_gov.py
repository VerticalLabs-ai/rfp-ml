"""SAM.gov integration API routes."""
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.app.core.database import get_db
from api.app.services.sam_gov_sync import get_sync_service, SAMGovSyncService, SyncStatus
from api.app.websockets.websocket_router import manager

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response Models

class SyncRequest(BaseModel):
    """Request to trigger sync."""
    days_back: int = Field(default=7, ge=1, le=365)
    limit: int = Field(default=100, ge=1, le=1000)
    keywords: list[str] | None = None
    agencies: list[str] | None = None
    naics_codes: list[str] | None = None


class SyncStatusResponse(BaseModel):
    """Sync status response."""
    status: str
    last_sync: str | None
    last_error: str | None
    opportunities_synced: int
    is_connected: bool
    api_key_configured: bool


class EntityVerificationResponse(BaseModel):
    """Entity verification response."""
    is_registered: bool
    registration_status: str | None = None
    uei: str | None = None
    cage_code: str | None = None
    legal_name: str | None = None
    expiration_date: str | None = None
    naics_codes: list[str] = []
    error: str | None = None


class CheckUpdatesRequest(BaseModel):
    """Request to check for updates."""
    opportunity_ids: list[str]


# Routes

@router.get("/status", response_model=SyncStatusResponse)
async def get_sync_status(
    sync_service: SAMGovSyncService = Depends(get_sync_service)
) -> SyncStatusResponse:
    """
    Get current SAM.gov sync status.

    Returns connection status, last sync time, and sync statistics.
    """
    status = sync_service.get_sync_status()
    return SyncStatusResponse(**status)


@router.post("/sync")
async def trigger_sync(
    request: SyncRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    sync_service: SAMGovSyncService = Depends(get_sync_service)
) -> dict[str, Any]:
    """
    Trigger manual sync with SAM.gov.

    Syncs new opportunities posted within the specified date range.
    """
    # Check if already syncing
    current_status = sync_service.get_sync_status()
    if current_status["status"] == SyncStatus.SYNCING:
        raise HTTPException(
            status_code=409,
            detail="Sync already in progress"
        )

    # Run sync in background
    async def run_sync():
        result = await sync_service.sync_opportunities(
            days_back=request.days_back,
            limit=request.limit,
            db=db
        )
        # Broadcast update via WebSocket
        await manager.broadcast({
            "type": "sam_gov_sync_complete",
            "data": result
        })

    background_tasks.add_task(run_sync)

    return {
        "status": "started",
        "message": f"Sync started for last {request.days_back} days"
    }


@router.post("/check-updates")
async def check_for_updates(
    request: CheckUpdatesRequest,
    db: Session = Depends(get_db),
    sync_service: SAMGovSyncService = Depends(get_sync_service)
) -> dict[str, Any]:
    """
    Check tracked opportunities for updates.

    Checks for amendments, deadline changes, and other modifications.
    """
    result = await sync_service.check_for_updates(
        opportunity_ids=request.opportunity_ids,
        db=db
    )
    return result


@router.get("/entity/verify", response_model=EntityVerificationResponse)
async def verify_entity_registration(
    uei: str | None = Query(None, min_length=12, max_length=12),
    cage_code: str | None = Query(None, min_length=5, max_length=5),
    legal_name: str | None = Query(None, min_length=2),
    sync_service: SAMGovSyncService = Depends(get_sync_service)
) -> EntityVerificationResponse:
    """
    Verify entity registration status in SAM.gov.

    Provide at least one of: UEI, CAGE code, or legal business name.
    """
    if not any([uei, cage_code, legal_name]):
        raise HTTPException(
            status_code=422,
            detail="At least one of uei, cage_code, or legal_name is required"
        )

    result = await sync_service.verify_entity(uei=uei) if uei else \
             sync_service.client.verify_entity_registration(
                 cage_code=cage_code, legal_name=legal_name
             ) if sync_service.client else {"is_registered": False, "error": "API not configured"}

    return EntityVerificationResponse(**result)


@router.get("/entity/{uei}/profile")
async def get_entity_profile(
    uei: str,
    sync_service: SAMGovSyncService = Depends(get_sync_service)
) -> dict[str, Any]:
    """
    Get full entity profile from SAM.gov.

    Returns complete registration data including:
    - Business types and set-aside eligibility
    - NAICS and PSC codes
    - Address and contact information
    - Registration status and expiration
    """
    profile = await sync_service.get_entity_profile(uei)

    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"Entity {uei} not found in SAM.gov"
        )

    return profile


@router.get("/opportunity/{notice_id}")
async def get_opportunity_details(
    notice_id: str,
    sync_service: SAMGovSyncService = Depends(get_sync_service)
) -> dict[str, Any]:
    """
    Get full opportunity details from SAM.gov.

    Fetches complete opportunity data including award info and attachments.
    """
    if not sync_service.client:
        raise HTTPException(
            status_code=503,
            detail="SAM.gov API not configured"
        )

    details = sync_service.client.get_opportunity_details(notice_id)

    if not details:
        raise HTTPException(
            status_code=404,
            detail=f"Opportunity {notice_id} not found"
        )

    return details


@router.get("/opportunity/{notice_id}/amendments")
async def get_opportunity_amendments(
    notice_id: str,
    days_back: int = Query(default=365, ge=1, le=365),
    sync_service: SAMGovSyncService = Depends(get_sync_service)
) -> dict[str, Any]:
    """
    Get amendment history for an opportunity.

    Returns all amendments/modifications for the solicitation.
    """
    if not sync_service.client:
        raise HTTPException(
            status_code=503,
            detail="SAM.gov API not configured"
        )

    amendments = sync_service.client.get_amendments(
        parent_notice_id=notice_id,
        days_back=days_back
    )

    return {
        "opportunity_id": notice_id,
        "amendment_count": len(amendments),
        "amendments": amendments
    }


@router.post("/company-profile/sync")
async def sync_company_from_sam(
    uei: str = Query(..., min_length=12, max_length=12),
    sync_service: SAMGovSyncService = Depends(get_sync_service)
) -> dict[str, Any]:
    """
    Sync company profile from SAM.gov registration.

    Fetches entity data and formats it for company profile auto-population.
    """
    profile = await sync_service.get_entity_profile(uei)

    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Entity not found"
        )

    # Format for company profile compatibility
    return {
        "company_name": profile.get("legal_name"),
        "dba_name": profile.get("dba_name"),
        "uei": profile.get("uei"),
        "cage_code": profile.get("cage_code"),
        "address": profile.get("address"),
        "website": profile.get("website"),
        "primary_naics": profile.get("primary_naics"),
        "naics_codes": [n["code"] for n in profile.get("naics_codes", [])],
        "psc_codes": [p["code"] for p in profile.get("psc_codes", [])],
        "business_types": [bt["description"] for bt in profile.get("business_types", [])],
        "set_aside_eligibility": profile.get("set_aside_eligibility", {}),
        "registration_status": profile.get("registration_status"),
        "registration_expiration": profile.get("registration_expiration"),
    }
