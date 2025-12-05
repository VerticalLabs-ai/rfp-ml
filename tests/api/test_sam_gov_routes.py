"""Tests for SAM.gov API routes."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from api.app.main import app

client = TestClient(app)


class TestSAMGovRoutes:
    """Test SAM.gov integration routes."""

    @pytest.fixture(autouse=True)
    def reset_sync_service(self):
        """Reset the singleton sync service before each test."""
        import api.app.services.sam_gov_sync as sync_module
        sync_module._sync_service = None
        yield
        sync_module._sync_service = None

    def test_get_sync_status(self):
        """Test getting sync status."""
        response = client.get("/api/v1/sam-gov/status")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "is_connected" in data

    @patch("api.app.routes.sam_gov.get_sync_service")
    def test_trigger_sync(self, mock_get_service):
        """Test triggering manual sync."""
        mock_service = MagicMock()
        mock_service.get_sync_status.return_value = {
            "status": "idle",
            "last_sync": None,
            "last_error": None,
            "opportunities_synced": 0,
            "is_connected": True,
            "api_key_configured": True,
        }
        # Make sync_opportunities return a coroutine
        async_result = AsyncMock(
            return_value={
                "status": "completed",
                "new_count": 5,
            }
        )
        mock_service.sync_opportunities = async_result
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/sam-gov/sync", json={"days_back": 7, "limit": 50}
        )

        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    def test_verify_entity_missing_params(self):
        """Test entity verification without required params."""
        response = client.get("/api/v1/sam-gov/entity/verify")

        assert response.status_code == 422  # Validation error

    @patch("api.app.services.sam_gov_sync.SAMGovClient")
    def test_verify_entity_by_uei(self, mock_client_class):
        """Test entity verification by UEI."""
        # Mock the client
        mock_client = MagicMock()
        # Mock the verify_entity_registration method (synchronous)
        mock_client.verify_entity_registration.return_value = {
            "is_registered": True,
            "registration_status": "Active",
            "uei": "ZQGGHJH74DW7",
            "cage_code": None,
            "legal_name": "Test Company",
            "expiration_date": None,
            "naics_codes": [],
        }
        mock_client_class.return_value = mock_client

        response = client.get("/api/v1/sam-gov/entity/verify?uei=ZQGGHJH74DW7")

        assert response.status_code == 200
        data = response.json()
        assert data["is_registered"] is True

    @patch("api.app.services.sam_gov_sync.SAMGovClient")
    def test_get_entity_profile(self, mock_client_class):
        """Test getting full entity profile."""
        # Mock the client
        mock_client = MagicMock()
        # Mock the get_entity_profile method (synchronous)
        mock_client.get_entity_profile.return_value = {
            "uei": "ZQGGHJH74DW7",
            "legal_name": "ACME Corp",
            "set_aside_eligibility": {"small_business": True},
        }
        mock_client_class.return_value = mock_client

        response = client.get("/api/v1/sam-gov/entity/ZQGGHJH74DW7/profile")

        assert response.status_code == 200
        data = response.json()
        assert data["legal_name"] == "ACME Corp"

    @patch("api.app.routes.sam_gov.get_sync_service")
    def test_check_for_updates(self, mock_get_service):
        """Test checking for opportunity updates."""
        mock_service = MagicMock()
        async_result = AsyncMock(
            return_value={
                "status": "completed",
                "checked_count": 2,
                "updates": [],
            }
        )
        mock_service.check_for_updates = async_result
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/sam-gov/check-updates", json={"opportunity_ids": ["opp1", "opp2"]}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"

    @patch("api.app.services.sam_gov_sync.SAMGovClient")
    def test_get_opportunity_details(self, mock_client_class):
        """Test getting opportunity details."""
        # Mock the client
        mock_client = MagicMock()
        # This is a synchronous method, so just return the dict
        mock_client.get_opportunity_details.return_value = {
            "opportunity_id": "abc123",
            "title": "Test Opportunity",
        }
        mock_client_class.return_value = mock_client

        response = client.get("/api/v1/sam-gov/opportunity/abc123")

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Opportunity"

    @patch("api.app.services.sam_gov_sync.SAMGovClient")
    def test_get_opportunity_amendments(self, mock_client_class):
        """Test getting opportunity amendments."""
        # Mock the client
        mock_client = MagicMock()
        # This is a synchronous method, so just return the list
        mock_client.get_amendments.return_value = [
            {"notice_id": "amd1", "title": "Amendment 1"},
        ]
        mock_client_class.return_value = mock_client

        response = client.get("/api/v1/sam-gov/opportunity/abc123/amendments")

        assert response.status_code == 200
        data = response.json()
        assert "amendments" in data
        assert len(data["amendments"]) == 1

    @patch("api.app.services.sam_gov_sync.SAMGovClient")
    def test_sync_company_from_sam(self, mock_client_class):
        """Test syncing company profile from SAM.gov."""
        # Mock the client
        mock_client = MagicMock()
        # Mock the get_entity_profile method (synchronous)
        mock_client.get_entity_profile.return_value = {
            "uei": "ZQGGHJH74DW7",
            "legal_name": "ACME Corp",
            "cage_code": "1ABC2",
            "address": {"city": "Washington"},
            "naics_codes": [{"code": "541512"}],
            "psc_codes": [{"code": "D399"}],
            "business_types": [{"description": "Small Business"}],
            "set_aside_eligibility": {"small_business": True},
            "primary_naics": "541512",
            "dba_name": None,
            "website": None,
            "registration_status": "Active",
            "registration_expiration": "2026-01-01",
        }
        mock_client_class.return_value = mock_client

        response = client.post("/api/v1/sam-gov/company-profile/sync?uei=ZQGGHJH74DW7")

        assert response.status_code == 200
        data = response.json()
        assert data["company_name"] == "ACME Corp"
