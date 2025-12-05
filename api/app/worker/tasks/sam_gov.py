"""
SAM.gov periodic sync tasks for Celery.

Handles:
- Periodic opportunity synchronization from SAM.gov
- Update checking for tracked opportunities
- Cleanup of expired opportunities
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from celery import shared_task

# Add project paths
project_root = str(Path(__file__).parents[5])
if project_root not in sys.path:
    sys.path.insert(0, project_root)

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=300, name="api.app.worker.tasks.sam_gov.sync_sam_gov_opportunities")
def sync_sam_gov_opportunities(self, days_back: int = 7, limit: int = 100):
    """
    Periodic task to sync opportunities from SAM.gov.

    Runs every 15 minutes during business hours.

    Args:
        days_back: Number of days back to search for opportunities
        limit: Maximum number of opportunities to fetch

    Returns:
        Dict with sync results including counts and status
    """
    logger.info(f"Starting SAM.gov sync: days_back={days_back}, limit={limit}")

    from api.app.core.database import SessionLocal
    from api.app.services.sam_gov_sync import get_sync_service

    with SessionLocal() as db:
        try:
            sync_service = get_sync_service()

            # Run the async sync in a new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    sync_service.sync_opportunities(days_back=days_back, limit=limit, db=db)
                )
                logger.info(f"SAM.gov sync complete: {result}")
                return result
            finally:
                loop.close()

        except Exception as exc:
            logger.error(f"SAM.gov sync failed: {exc}")
            raise self.retry(exc=exc)


@shared_task(bind=True, name="api.app.worker.tasks.sam_gov.check_opportunity_updates")
def check_opportunity_updates(self, opportunity_ids: list[str]):
    """
    Check specific opportunities for updates/amendments.

    Args:
        opportunity_ids: List of opportunity IDs to check

    Returns:
        Dict with update check results
    """
    logger.info(f"Checking {len(opportunity_ids)} opportunities for updates")

    from api.app.core.database import SessionLocal
    from api.app.services.sam_gov_sync import get_sync_service

    with SessionLocal() as db:
        try:
            sync_service = get_sync_service()

            # Run the async check in a new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    sync_service.check_for_updates(opportunity_ids=opportunity_ids, db=db)
                )
                logger.info(f"Update check complete: {result}")
                return result
            finally:
                loop.close()

        except Exception as exc:
            logger.error(f"Update check failed: {exc}")
            raise


@shared_task(name="api.app.worker.tasks.sam_gov.cleanup_expired_opportunities")
def cleanup_expired_opportunities():
    """
    Remove expired opportunities from tracking.

    Cleans up opportunities that are past their response deadline
    by more than 30 days.

    Returns:
        Dict with cleanup results
    """
    logger.info("Cleaning up expired opportunities")

    from api.app.core.database import SessionLocal
    from api.app.models.database import RFPOpportunity

    with SessionLocal() as db:
        try:
            # Calculate cutoff date (30 days after deadline)
            cutoff = datetime.now(timezone.utc) - timedelta(days=30)

            # Find expired opportunities
            expired = (
                db.query(RFPOpportunity)
                .filter(
                    RFPOpportunity.response_deadline < cutoff,
                    RFPOpportunity.response_deadline.isnot(None)
                )
                .all()
            )

            deleted_count = len(expired)

            # Delete expired opportunities
            for opp in expired:
                db.delete(opp)

            db.commit()

            logger.info(f"Cleaned up {deleted_count} expired opportunities")
            return {
                "status": "completed",
                "deleted_count": deleted_count,
                "cutoff_date": cutoff.isoformat(),
            }

        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            db.rollback()
            return {
                "status": "error",
                "error": str(e),
            }
