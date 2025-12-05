"""SAM.gov synchronization service for real-time opportunity tracking."""
import asyncio
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from sqlalchemy.orm import Session

from api.app.core.config import settings
from api.app.models.database import RFPOpportunity
from src.agents.sam_gov_client import SAMGovClient

logger = logging.getLogger(__name__)


class SyncStatus(str, Enum):
    """Sync operation status."""
    IDLE = "idle"
    SYNCING = "syncing"
    COMPLETED = "completed"
    ERROR = "error"


class SAMGovSyncService:
    """
    Service for synchronizing opportunities with SAM.gov.

    Features:
    - Periodic sync of new opportunities
    - Update tracking for watched opportunities
    - Amendment detection
    - Connection status monitoring
    """

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.SAM_GOV_API_KEY
        self.client = SAMGovClient(api_key=self.api_key) if self.api_key else None
        self._status = SyncStatus.IDLE
        self._last_sync: datetime | None = None
        self._last_error: str | None = None
        self._opportunities_synced = 0
        self._sync_lock = asyncio.Lock()

    def get_sync_status(self) -> dict[str, Any]:
        """Get current sync status."""
        return {
            "status": self._status,
            "last_sync": self._last_sync.isoformat() if self._last_sync else None,
            "last_error": self._last_error,
            "opportunities_synced": self._opportunities_synced,
            "is_connected": self.client is not None,
            "api_key_configured": bool(self.api_key),
        }

    async def sync_opportunities(
        self,
        days_back: int = 7,
        limit: int = 100,
        db: Session | None = None
    ) -> dict[str, Any]:
        """
        Sync new opportunities from SAM.gov.

        Args:
            days_back: How many days back to search
            limit: Maximum opportunities to fetch
            db: Database session (optional)

        Returns:
            Sync result summary
        """
        if not self.client:
            return {
                "status": "error",
                "error": "SAM.gov API key not configured",
            }

        async with self._sync_lock:
            self._status = SyncStatus.SYNCING

            try:
                # Fetch opportunities from SAM.gov
                opportunities = self.client.search_opportunities(
                    days_back=days_back,
                    limit=limit
                )

                new_count = 0
                updated_count = 0

                if db:
                    for opp in opportunities:
                        # Check if already exists
                        notice_id = opp.get("notice_id", opp.get("rfp_id", ""))
                        existing = db.query(RFPOpportunity).filter(
                            RFPOpportunity.source_url.contains(notice_id)
                        ).first() if notice_id else None

                        if existing:
                            # Check for updates
                            if self._has_changes(existing, opp):
                                self._update_opportunity(existing, opp)
                                updated_count += 1
                        else:
                            # Create new opportunity
                            self._create_opportunity(db, opp)
                            new_count += 1

                    db.commit()

                self._status = SyncStatus.COMPLETED
                self._last_sync = datetime.utcnow()
                self._opportunities_synced += len(opportunities)
                self._last_error = None

                return {
                    "status": "completed",
                    "total_fetched": len(opportunities),
                    "new_count": new_count,
                    "updated_count": updated_count,
                    "sync_time": self._last_sync.isoformat(),
                }

            except Exception as e:
                self._status = SyncStatus.ERROR
                self._last_error = str(e)
                logger.error(f"Sync failed: {e}")
                return {
                    "status": "error",
                    "error": str(e),
                }

    async def check_for_updates(
        self,
        opportunity_ids: list[str],
        db: Session | None = None
    ) -> dict[str, Any]:
        """
        Check tracked opportunities for updates (amendments, deadline changes).

        Args:
            opportunity_ids: List of opportunity IDs to check
            db: Database session

        Returns:
            Update summary with changed opportunities
        """
        if not self.client:
            return {"status": "error", "error": "API not configured"}

        updates = []

        for opp_id in opportunity_ids:
            try:
                current = self.client.get_opportunity_details(opp_id)
                if not current:
                    continue

                # Check for amendments
                amendments = self.client.get_amendments(
                    parent_notice_id=opp_id,
                    days_back=30
                )

                if amendments:
                    updates.append({
                        "opportunity_id": opp_id,
                        "type": "amendment",
                        "amendment_count": len(amendments),
                        "latest_amendment": amendments[0] if amendments else None,
                    })

                # If we have DB access, check for field changes
                if db:
                    existing = db.query(RFPOpportunity).filter(
                        RFPOpportunity.source_url.contains(opp_id)
                    ).first()

                    if existing and self._has_changes(existing, current):
                        updates.append({
                            "opportunity_id": opp_id,
                            "type": "field_update",
                            "changes": self._get_changes(existing, current),
                        })

            except Exception as e:
                logger.warning(f"Failed to check {opp_id}: {e}")

        return {
            "status": "completed",
            "checked_count": len(opportunity_ids),
            "updates": updates,
        }

    async def verify_entity(self, uei: str) -> dict[str, Any]:
        """Verify entity registration status."""
        if not self.client:
            return {"status": "error", "error": "API not configured"}

        return self.client.verify_entity_registration(uei=uei)

    async def get_entity_profile(self, uei: str) -> dict[str, Any] | None:
        """Get full entity profile for company auto-population."""
        if not self.client:
            return None

        return self.client.get_entity_profile(uei=uei)

    def _has_changes(self, existing: RFPOpportunity, new_data: dict) -> bool:
        """Check if opportunity data has changed."""
        checks = [
            (existing.title, new_data.get("title")),
            (existing.response_deadline, new_data.get("response_deadline")),
            (existing.award_amount, new_data.get("award_amount")),
        ]
        return any(old != new for old, new in checks if new is not None)

    def _get_changes(self, existing: RFPOpportunity, new_data: dict) -> list[dict]:
        """Get list of changed fields."""
        changes = []
        field_map = {
            "title": "title",
            "response_deadline": "response_deadline",
            "award_amount": "award_amount",
            "description": "description",
        }

        for db_field, api_field in field_map.items():
            old_val = getattr(existing, db_field, None)
            new_val = new_data.get(api_field)
            if new_val is not None and old_val != new_val:
                changes.append({
                    "field": db_field,
                    "old_value": str(old_val),
                    "new_value": str(new_val),
                })

        return changes

    def _update_opportunity(self, existing: RFPOpportunity, new_data: dict) -> None:
        """Update existing opportunity with new data."""
        if new_data.get("title"):
            existing.title = new_data["title"]
        if new_data.get("response_deadline"):
            # Handle both string and datetime
            deadline = new_data["response_deadline"]
            if isinstance(deadline, str):
                try:
                    existing.response_deadline = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    pass
            elif isinstance(deadline, datetime):
                existing.response_deadline = deadline
        if new_data.get("award_amount"):
            existing.award_amount = new_data["award_amount"]
        existing.last_scraped_at = datetime.utcnow()

    def _create_opportunity(self, db: Session, data: dict) -> RFPOpportunity:
        """Create new opportunity from SAM.gov data."""
        # Parse dates
        posted_date = None
        response_deadline = None

        if data.get("posted_date"):
            try:
                posted_date = datetime.fromisoformat(data["posted_date"].replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass

        if data.get("response_deadline"):
            try:
                response_deadline = datetime.fromisoformat(data["response_deadline"].replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass

        # Generate unique RFP ID
        notice_id = data.get("notice_id", data.get("rfp_id", ""))
        rfp_id = data.get("solicitation_number", f"SAM-{notice_id}")

        # Build metadata with additional fields
        metadata = {
            "set_aside": data.get("set_aside"),
            "set_aside_description": data.get("set_aside_description"),
            "notice_id": notice_id,
        }

        opp = RFPOpportunity(
            rfp_id=rfp_id,
            title=data.get("title", ""),
            solicitation_number=data.get("solicitation_number"),
            agency=data.get("agency"),
            office=data.get("office"),
            description=data.get("description", ""),
            posted_date=posted_date,
            response_deadline=response_deadline,
            naics_code=data.get("naics_code"),
            award_amount=data.get("award_amount"),
            source_url=data.get("url") or f"https://sam.gov/opp/{notice_id}/view",
            source_platform="SAM.gov",
            last_scraped_at=datetime.utcnow(),
            rfp_metadata=metadata,
        )
        db.add(opp)
        return opp


# Singleton instance
_sync_service: SAMGovSyncService | None = None


def get_sync_service() -> SAMGovSyncService:
    """Get or create sync service singleton."""
    global _sync_service
    if _sync_service is None:
        _sync_service = SAMGovSyncService()
    return _sync_service
