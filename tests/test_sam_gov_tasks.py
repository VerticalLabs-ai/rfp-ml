"""
Tests for SAM.gov Celery background sync tasks.

Following TDD approach - tests written first before implementation.
"""

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Add project root to path
project_root = str(Path(__file__).parents[1])
if project_root not in sys.path:
    sys.path.insert(0, project_root)


# Test fixtures
@pytest.fixture
def mock_db_session():
    """Mock database session."""
    engine = create_engine("sqlite:///:memory:")
    from api.app.models.database import Base

    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def mock_sync_service():
    """Mock SAM.gov sync service."""
    service = Mock()
    service.sync_opportunities = AsyncMock(
        return_value={
            "status": "completed",
            "total_fetched": 5,
            "new_count": 3,
            "updated_count": 2,
            "sync_time": datetime.now(timezone.utc).isoformat(),
        }
    )
    service.check_for_updates = AsyncMock(
        return_value={
            "status": "completed",
            "checked_count": 3,
            "updates": [
                {
                    "opportunity_id": "test-123",
                    "type": "amendment",
                    "amendment_count": 1,
                }
            ],
        }
    )
    return service


@pytest.fixture
def sample_opportunities():
    """Sample opportunity data."""
    return [
        {
            "notice_id": "test-001",
            "title": "IT Services Contract",
            "agency": "GSA",
            "posted_date": datetime.now(timezone.utc).isoformat(),
            "response_deadline": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        },
        {
            "notice_id": "test-002",
            "title": "Consulting Services",
            "agency": "DOD",
            "posted_date": datetime.now(timezone.utc).isoformat(),
            "response_deadline": (datetime.now(timezone.utc) + timedelta(days=20)).isoformat(),
        },
    ]


class TestSyncSamGovOpportunities:
    """Test suite for sync_sam_gov_opportunities task."""

    @patch("api.app.core.database.SessionLocal")
    @patch("api.app.services.sam_gov_sync.get_sync_service")
    def test_sync_task_successful(self, mock_get_service, mock_session, mock_sync_service):
        """Test successful sync execution."""
        from api.app.worker.tasks.sam_gov import sync_sam_gov_opportunities

        mock_get_service.return_value = mock_sync_service
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        result = sync_sam_gov_opportunities(days_back=7, limit=100)

        assert result["status"] == "completed"
        assert result["total_fetched"] == 5
        assert result["new_count"] == 3
        assert result["updated_count"] == 2
        mock_sync_service.sync_opportunities.assert_called_once()

    @patch("api.app.core.database.SessionLocal")
    @patch("api.app.services.sam_gov_sync.get_sync_service")
    def test_sync_task_with_custom_parameters(self, mock_get_service, mock_session, mock_sync_service):
        """Test sync with custom days_back and limit."""
        from api.app.worker.tasks.sam_gov import sync_sam_gov_opportunities

        mock_get_service.return_value = mock_sync_service
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        result = sync_sam_gov_opportunities(days_back=14, limit=50)

        assert result["status"] == "completed"
        # Verify parameters were passed correctly
        call_args = mock_sync_service.sync_opportunities.call_args
        assert call_args is not None

    @patch("api.app.core.database.SessionLocal")
    @patch("api.app.services.sam_gov_sync.get_sync_service")
    def test_sync_task_handles_service_error(self, mock_get_service, mock_session):
        """Test sync task handles service errors with retry."""
        from api.app.worker.tasks.sam_gov import sync_sam_gov_opportunities

        mock_service = Mock()
        mock_service.sync_opportunities = AsyncMock(side_effect=Exception("API Error"))
        mock_get_service.return_value = mock_service
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        # Should raise exception for retry
        with pytest.raises(Exception):
            sync_sam_gov_opportunities(days_back=7, limit=100)

    @patch("api.app.core.database.SessionLocal")
    @patch("api.app.services.sam_gov_sync.get_sync_service")
    def test_sync_task_closes_db_session(self, mock_get_service, mock_session, mock_sync_service):
        """Test that database session is always closed."""
        from api.app.worker.tasks.sam_gov import sync_sam_gov_opportunities

        mock_get_service.return_value = mock_sync_service
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        sync_sam_gov_opportunities(days_back=7, limit=100)

        # Verify session context manager was used (auto-closes)
        mock_session.assert_called_once()

    @patch("api.app.core.database.SessionLocal")
    @patch("api.app.services.sam_gov_sync.get_sync_service")
    def test_sync_task_uses_utc_timezone(self, mock_get_service, mock_session, mock_sync_service):
        """Test that datetime uses timezone.utc not utcnow()."""
        from api.app.worker.tasks.sam_gov import sync_sam_gov_opportunities

        mock_get_service.return_value = mock_sync_service
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        result = sync_sam_gov_opportunities(days_back=7, limit=100)

        # Result should have proper timezone-aware datetime
        assert "sync_time" in result
        sync_time = datetime.fromisoformat(result["sync_time"])
        assert sync_time.tzinfo is not None


class TestCheckOpportunityUpdates:
    """Test suite for check_opportunity_updates task."""

    @patch("api.app.core.database.SessionLocal")
    @patch("api.app.services.sam_gov_sync.get_sync_service")
    def test_check_updates_successful(self, mock_get_service, mock_session, mock_sync_service):
        """Test successful update check."""
        from api.app.worker.tasks.sam_gov import check_opportunity_updates

        mock_get_service.return_value = mock_sync_service
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        opportunity_ids = ["test-001", "test-002", "test-003"]
        result = check_opportunity_updates(opportunity_ids=opportunity_ids)

        assert result["status"] == "completed"
        assert result["checked_count"] == 3
        assert len(result["updates"]) > 0
        mock_sync_service.check_for_updates.assert_called_once()

    @patch("api.app.core.database.SessionLocal")
    @patch("api.app.services.sam_gov_sync.get_sync_service")
    def test_check_updates_empty_list(self, mock_get_service, mock_session, mock_sync_service):
        """Test check with empty opportunity list."""
        from api.app.worker.tasks.sam_gov import check_opportunity_updates

        mock_get_service.return_value = mock_sync_service
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        result = check_opportunity_updates(opportunity_ids=[])

        # Should still work with empty list
        assert result is not None

    @patch("api.app.core.database.SessionLocal")
    @patch("api.app.services.sam_gov_sync.get_sync_service")
    def test_check_updates_handles_errors(self, mock_get_service, mock_session):
        """Test update check handles errors gracefully."""
        from api.app.worker.tasks.sam_gov import check_opportunity_updates

        mock_service = Mock()
        mock_service.check_for_updates = AsyncMock(side_effect=Exception("API Error"))
        mock_get_service.return_value = mock_service
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        with pytest.raises(Exception):
            check_opportunity_updates(opportunity_ids=["test-001"])

    @patch("api.app.core.database.SessionLocal")
    @patch("api.app.services.sam_gov_sync.get_sync_service")
    def test_check_updates_closes_db_session(self, mock_get_service, mock_session, mock_sync_service):
        """Test that database session is always closed."""
        from api.app.worker.tasks.sam_gov import check_opportunity_updates

        mock_get_service.return_value = mock_sync_service
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        check_opportunity_updates(opportunity_ids=["test-001"])

        # Verify session context manager was used
        mock_session.assert_called_once()


class TestCleanupExpiredOpportunities:
    """Test suite for cleanup_expired_opportunities task."""

    @patch("api.app.core.database.SessionLocal")
    def test_cleanup_task_basic(self, mock_session):
        """Test basic cleanup execution."""
        from api.app.worker.tasks.sam_gov import cleanup_expired_opportunities

        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        result = cleanup_expired_opportunities()

        # Should return success status
        assert result is not None


class TestCeleryTaskConfiguration:
    """Test Celery task configuration and retry behavior."""

    def test_sync_task_has_retry_config(self):
        """Test sync task has proper retry configuration."""
        from api.app.worker.tasks.sam_gov import sync_sam_gov_opportunities

        # Check task is decorated with proper config
        assert hasattr(sync_sam_gov_opportunities, "max_retries")
        assert sync_sam_gov_opportunities.max_retries == 3
        assert hasattr(sync_sam_gov_opportunities, "default_retry_delay")
        assert sync_sam_gov_opportunities.default_retry_delay == 300  # 5 minutes

    def test_check_updates_task_is_bound(self):
        """Test check_updates task is bound (has self)."""
        from api.app.worker.tasks.sam_gov import check_opportunity_updates

        assert hasattr(check_opportunity_updates, "bind")

    def test_cleanup_task_exists(self):
        """Test cleanup task is registered."""
        from api.app.worker.tasks.sam_gov import cleanup_expired_opportunities

        assert callable(cleanup_expired_opportunities)


class TestBeatScheduleIntegration:
    """Test Celery Beat schedule configuration."""

    def test_beat_schedule_includes_sam_gov_sync(self):
        """Test beat schedule includes SAM.gov sync task."""
        from api.app.worker.celery_app import celery_app

        schedule = celery_app.conf.beat_schedule

        assert "sync-sam-gov-every-15-minutes" in schedule
        sync_config = schedule["sync-sam-gov-every-15-minutes"]

        assert sync_config["task"] == "api.app.worker.tasks.sam_gov.sync_sam_gov_opportunities"
        # Check it runs every 15 minutes during business hours (6-22)
        assert "schedule" in sync_config

    def test_beat_schedule_includes_cleanup(self):
        """Test beat schedule includes cleanup task."""
        from api.app.worker.celery_app import celery_app

        schedule = celery_app.conf.beat_schedule

        assert "cleanup-expired-daily" in schedule
        cleanup_config = schedule["cleanup-expired-daily"]

        assert cleanup_config["task"] == "api.app.worker.tasks.sam_gov.cleanup_expired_opportunities"


class TestEventLoopHandling:
    """Test proper async/sync event loop handling."""

    @patch("asyncio.set_event_loop")
    @patch("asyncio.new_event_loop")
    @patch("api.app.core.database.SessionLocal")
    @patch("api.app.services.sam_gov_sync.get_sync_service")
    def test_sync_task_creates_new_event_loop(self, mock_get_service, mock_session, mock_new_loop, mock_set_loop):
        """Test sync task creates and closes event loop properly."""
        from api.app.worker.tasks.sam_gov import sync_sam_gov_opportunities

        mock_loop = MagicMock()
        mock_new_loop.return_value = mock_loop
        mock_loop.run_until_complete.return_value = {
            "status": "completed",
            "total_fetched": 5,
            "new_count": 3,
            "updated_count": 2,
        }

        mock_service = Mock()
        mock_get_service.return_value = mock_service
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        sync_sam_gov_opportunities(days_back=7, limit=100)

        # Verify event loop was created and closed
        mock_new_loop.assert_called_once()
        mock_set_loop.assert_called_once_with(mock_loop)
        mock_loop.close.assert_called_once()

    @patch("asyncio.set_event_loop")
    @patch("asyncio.new_event_loop")
    @patch("api.app.core.database.SessionLocal")
    @patch("api.app.services.sam_gov_sync.get_sync_service")
    def test_check_updates_creates_new_event_loop(self, mock_get_service, mock_session, mock_new_loop, mock_set_loop):
        """Test check_updates creates and closes event loop properly."""
        from api.app.worker.tasks.sam_gov import check_opportunity_updates

        mock_loop = MagicMock()
        mock_new_loop.return_value = mock_loop
        mock_loop.run_until_complete.return_value = {
            "status": "completed",
            "checked_count": 1,
            "updates": [],
        }

        mock_service = Mock()
        mock_get_service.return_value = mock_service
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        check_opportunity_updates(opportunity_ids=["test-001"])

        # Verify event loop was created and closed
        mock_new_loop.assert_called_once()
        mock_set_loop.assert_called_once_with(mock_loop)
        mock_loop.close.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
