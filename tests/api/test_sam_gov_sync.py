"""Tests for SAM.gov sync service."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta

from api.app.services.sam_gov_sync import SAMGovSyncService, SyncStatus


class TestSAMGovSyncService:
    """Test SAM.gov sync service."""

    @pytest.fixture
    def sync_service(self):
        return SAMGovSyncService()

    def test_sync_status_initial(self, sync_service):
        """Test initial sync status."""
        status = sync_service.get_sync_status()

        assert status["status"] == SyncStatus.IDLE
        assert status["last_sync"] is None
        assert status["opportunities_synced"] == 0

    @patch("api.app.services.sam_gov_sync.SAMGovClient")
    @pytest.mark.asyncio
    async def test_sync_new_opportunities(self, mock_client_class, sync_service):
        """Test syncing new opportunities from SAM.gov."""
        mock_client = MagicMock()
        mock_client.search_opportunities.return_value = [
            {
                "notice_id": "opp1",
                "title": "New Opportunity",
                "solicitation_number": "SOL-001",
                "posted_date": datetime.now().isoformat(),
            }
        ]
        mock_client_class.return_value = mock_client
        sync_service.client = mock_client

        result = await sync_service.sync_opportunities(days_back=7)

        assert result["new_count"] >= 0
        assert result["status"] == "completed"

    @patch("api.app.services.sam_gov_sync.SAMGovClient")
    @pytest.mark.asyncio
    async def test_check_tracked_opportunities_updates(self, mock_client_class, sync_service):
        """Test checking tracked opportunities for updates."""
        mock_client = MagicMock()
        mock_client.get_opportunity_details.return_value = {
            "opportunity_id": "opp1",
            "title": "Updated Title",
            "response_deadline": "2025-03-01",
        }
        mock_client.get_amendments.return_value = []
        mock_client_class.return_value = mock_client
        sync_service.client = mock_client

        # Mock tracked opportunities
        tracked_ids = ["opp1", "opp2"]

        result = await sync_service.check_for_updates(tracked_ids)

        assert "updates" in result
        assert result["status"] == "completed"

    @patch("api.app.services.sam_gov_sync.SAMGovClient")
    @pytest.mark.asyncio
    async def test_verify_entity(self, mock_client_class, sync_service):
        """Test entity verification."""
        mock_client = MagicMock()
        mock_client.verify_entity_registration.return_value = {
            "is_registered": True,
            "registration_status": "Active",
            "uei": "ZQGGHJH74DW7",
            "legal_name": "ACME Corporation",
        }
        mock_client_class.return_value = mock_client
        sync_service.client = mock_client

        result = await sync_service.verify_entity(uei="ZQGGHJH74DW7")

        assert result["is_registered"] is True
        assert result["registration_status"] == "Active"

    @patch("api.app.services.sam_gov_sync.SAMGovClient")
    @pytest.mark.asyncio
    async def test_get_entity_profile(self, mock_client_class, sync_service):
        """Test getting entity profile."""
        mock_client = MagicMock()
        mock_client.get_entity_profile.return_value = {
            "uei": "ZQGGHJH74DW7",
            "legal_name": "ACME Corporation",
            "cage_code": "1ABC2",
            "set_aside_eligibility": {
                "small_business": True,
                "8a_certified": False,
            },
        }
        mock_client_class.return_value = mock_client
        sync_service.client = mock_client

        result = await sync_service.get_entity_profile(uei="ZQGGHJH74DW7")

        assert result is not None
        assert result["legal_name"] == "ACME Corporation"
        assert result["set_aside_eligibility"]["small_business"] is True
