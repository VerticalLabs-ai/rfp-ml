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


class TestSAMGovClientEntityVerification:
    """Test entity registration verification."""

    @pytest.fixture
    def client(self):
        return SAMGovClient(api_key="test_api_key")

    @pytest.fixture
    def mock_entity_response(self):
        return {
            "totalRecords": 1,
            "entityData": [{
                "entityRegistration": {
                    "ueiSAM": "ZQGGHJH74DW7",
                    "cageCode": "1ABC2",
                    "legalBusinessName": "ACME Corporation",
                    "registrationStatus": "Active",
                    "registrationExpirationDate": "2026-01-15",
                    "samRegistered": "Yes",
                    "purposeOfRegistrationDesc": "All Awards"
                },
                "coreData": {
                    "entityInformation": {
                        "entityURL": "https://acme.com",
                        "entityDivisionName": "Main Division"
                    },
                    "physicalAddress": {
                        "addressLine1": "123 Main St",
                        "city": "Washington",
                        "stateOrProvinceCode": "DC",
                        "zipCode": "20001",
                        "countryCode": "USA"
                    },
                    "businessTypes": {
                        "businessTypeList": [
                            {"businessTypeCode": "2X", "businessTypeDesc": "For Profit Organization"},
                            {"businessTypeCode": "27", "businessTypeDesc": "Self Certified Small Disadvantaged Business"}
                        ],
                        "sbaBusinessTypeList": [
                            {"sbaBusinessTypeCode": "XX", "sbaBusinessTypeDesc": "8(a) Certified"}
                        ]
                    }
                },
                "assertions": {
                    "goodsAndServices": {
                        "primaryNaics": "541512",
                        "naicsList": [
                            {"naicsCode": "541512", "naicsDescription": "Computer Systems Design Services", "sbaSmallBusiness": "Y"},
                            {"naicsCode": "541511", "naicsDescription": "Custom Computer Programming", "sbaSmallBusiness": "Y"}
                        ],
                        "pscList": [
                            {"pscCode": "D399", "pscDescription": "IT and Telecom"}
                        ]
                    }
                }
            }]
        }

    @patch("src.agents.sam_gov_client.requests.get")
    def test_verify_entity_registration_active(self, mock_get, client, mock_entity_response):
        """Test verifying an active SAM.gov registration by UEI."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_entity_response

        result = client.verify_entity_registration(uei="ZQGGHJH74DW7")

        assert result is not None
        assert result["is_registered"] is True
        assert result["registration_status"] == "Active"
        assert result["uei"] == "ZQGGHJH74DW7"
        assert result["legal_name"] == "ACME Corporation"
        assert "541512" in result["naics_codes"]

    @patch("src.agents.sam_gov_client.requests.get")
    def test_verify_entity_registration_not_found(self, mock_get, client):
        """Test handling of non-registered entity."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"totalRecords": 0, "entityData": []}

        result = client.verify_entity_registration(uei="NONEXISTENT123")

        assert result is not None
        assert result["is_registered"] is False

    @patch("src.agents.sam_gov_client.requests.get")
    def test_get_entity_profile_full(self, mock_get, client, mock_entity_response):
        """Test fetching complete entity profile for auto-population."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_entity_response

        result = client.get_entity_profile(uei="ZQGGHJH74DW7")

        assert result["legal_name"] == "ACME Corporation"
        assert result["cage_code"] == "1ABC2"
        assert result["address"]["city"] == "Washington"
        assert result["address"]["state"] == "DC"
        assert len(result["business_types"]) >= 1
        assert result["set_aside_eligibility"]["small_business"] is True


class TestSAMGovClientAmendments:
    """Test amendment tracking functionality."""

    @pytest.fixture
    def client(self):
        return SAMGovClient(api_key="test_api_key")

    @pytest.fixture
    def mock_amendments_response(self):
        return {
            "opportunitiesData": [
                {
                    "noticeId": "abc123-amd-003",
                    "title": "Amendment 3 - Extended Deadline",
                    "postedDate": "2025-01-20",
                    "type": "Amendment",
                    "parentNoticeId": "abc123",
                },
                {
                    "noticeId": "abc123-amd-002",
                    "title": "Amendment 2 - Revised SOW",
                    "postedDate": "2025-01-15",
                    "type": "Amendment",
                    "parentNoticeId": "abc123",
                },
                {
                    "noticeId": "abc123-amd-001",
                    "title": "Amendment 1 - Q&A Response",
                    "postedDate": "2025-01-10",
                    "type": "Amendment",
                    "parentNoticeId": "abc123",
                },
            ],
            "totalRecords": 3
        }

    @patch("src.agents.sam_gov_client.requests.get")
    def test_get_amendments_for_opportunity(self, mock_get, client, mock_amendments_response):
        """Test fetching amendment history for an opportunity."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_amendments_response

        result = client.get_amendments(solicitation_number="SOL-2025-001")

        assert len(result) == 3
        assert result[0]["type"] == "Amendment"
        assert "abc123-amd-003" in result[0]["notice_id"]
