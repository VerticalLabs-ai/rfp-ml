"""Tests for SAMGovClient with extended SAM.gov API coverage."""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from src.agents.sam_gov_client import SAMGovClient


class TestSAMGovClientOpportunityDetails:
    """Test opportunity details fetching."""

    @pytest.fixture
    def client(self):
        return SAMGovClient(api_key="test_api_key")

    @pytest.fixture
    def mock_opportunity_response(self):
        return {
            "opportunityId": "abc123",
            "data": {
                "title": "Test Opportunity",
                "solicitationNumber": "SOL-2025-001",
                "fullParentPathName": "DEPT OF DEFENSE.ARMY",
                "postedDate": "2025-01-15",
                "responseDeadLine": "2025-02-15",
                "type": "Solicitation",
                "naicsCode": "541512",
                "classificationCode": "D399",
                "award": {
                    "amount": 500000,
                    "date": "2025-03-01"
                },
                "description": [{"body": "Full description text here"}],
                "resourceLinks": [
                    {"url": "https://sam.gov/doc1.pdf", "name": "SOW.pdf"}
                ]
            }
        }

    @patch("src.agents.sam_gov_client.requests.get")
    def test_get_opportunity_details_success(self, mock_get, client, mock_opportunity_response):
        """Test fetching full opportunity details by ID."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_opportunity_response

        result = client.get_opportunity_details("abc123")

        assert result is not None
        assert result["title"] == "Test Opportunity"
        assert result["solicitation_number"] == "SOL-2025-001"
        assert result["award_amount"] == 500000
        assert len(result["attachments"]) == 1

    @patch("src.agents.sam_gov_client.requests.get")
    def test_get_opportunity_details_not_found(self, mock_get, client):
        """Test handling of non-existent opportunity."""
        mock_get.return_value.status_code = 404
        mock_get.return_value.json.return_value = {"error": "Not found"}

        result = client.get_opportunity_details("nonexistent")

        assert result is None
