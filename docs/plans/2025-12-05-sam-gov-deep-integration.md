# SAM.gov Deep Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement deep integration with SAM.gov for real-time opportunity sync, entity registration verification, and streamlined submission workflows.

**Architecture:** Extend existing `SAMGovClient` with comprehensive API coverage. Add background sync service using Celery tasks. Create entity verification service for company profile sync. Frontend gets sync status dashboard with real-time WebSocket updates.

**Tech Stack:** Python/FastAPI backend, React/TypeScript frontend, Celery for background tasks, SQLAlchemy models, WebSocket for real-time updates, SAM.gov Opportunities v2 and Entity Management v3 APIs.

---

## Prerequisites

Before starting:
1. Ensure `SAM_GOV_API_KEY` is configured in `.env`
2. Backend is running: `docker-compose up -d`
3. Celery worker is available for background tasks

---

## Task 1: Extend SAMGovClient with Opportunity Details API

**Files:**
- Modify: `src/agents/sam_gov_client.py:1-213`
- Test: `tests/test_sam_gov_client.py` (create)

**Step 1: Write the failing test**

Create `tests/test_sam_gov_client.py`:

```python
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
```

**Step 2: Run test to verify it fails**

```bash
PYTHONPATH=. python -m pytest tests/test_sam_gov_client.py::TestSAMGovClientOpportunityDetails::test_get_opportunity_details_success -v
```

Expected: FAIL with `AttributeError: 'SAMGovClient' object has no attribute 'get_opportunity_details'`

**Step 3: Implement get_opportunity_details method**

Add to `src/agents/sam_gov_client.py` after the existing `search_opportunities` method (around line 120):

```python
    def get_opportunity_details(self, opportunity_id: str) -> dict | None:
        """
        Fetch full details for a specific opportunity.

        The search API returns limited data (no award amounts in many cases).
        This method fetches the complete opportunity record including:
        - Full description
        - Award information
        - All attachments/resource links
        - Amendment history

        Args:
            opportunity_id: The SAM.gov opportunity ID (noticeId)

        Returns:
            Normalized opportunity dict or None if not found
        """
        url = f"{self.opportunities_base_url}/{opportunity_id}"
        params = {"api_key": self.api_key}

        try:
            response = requests.get(url, params=params, timeout=30)

            if response.status_code == 404:
                logger.warning(f"Opportunity {opportunity_id} not found")
                return None

            response.raise_for_status()
            data = response.json()

            # Handle nested response structure
            opp_data = data.get("data", data)

            # Extract description from array format
            description = ""
            if isinstance(opp_data.get("description"), list):
                description = " ".join(
                    d.get("body", "") for d in opp_data["description"]
                )
            else:
                description = opp_data.get("description", "")

            # Extract attachments from resourceLinks
            attachments = []
            for link in opp_data.get("resourceLinks", []):
                attachments.append({
                    "url": link.get("url", ""),
                    "name": link.get("name", ""),
                    "type": link.get("type", "document"),
                })

            # Parse award info
            award = opp_data.get("award", {})
            award_amount = award.get("amount", 0) if award else 0
            award_date = award.get("date") if award else None

            return {
                "opportunity_id": opportunity_id,
                "title": opp_data.get("title", ""),
                "solicitation_number": opp_data.get("solicitationNumber", ""),
                "agency": opp_data.get("fullParentPathName", "").split(".")[0] if opp_data.get("fullParentPathName") else "",
                "office": opp_data.get("fullParentPathName", ""),
                "posted_date": opp_data.get("postedDate"),
                "response_deadline": opp_data.get("responseDeadLine"),
                "archive_date": opp_data.get("archiveDate"),
                "type": opp_data.get("type", ""),
                "base_type": opp_data.get("baseType", ""),
                "naics_code": opp_data.get("naicsCode", ""),
                "classification_code": opp_data.get("classificationCode", ""),
                "set_aside": opp_data.get("typeOfSetAside", ""),
                "set_aside_description": opp_data.get("typeOfSetAsideDescription", ""),
                "description": description,
                "award_amount": award_amount,
                "award_date": award_date,
                "attachments": attachments,
                "place_of_performance": {
                    "city": opp_data.get("placeOfPerformance", {}).get("city", ""),
                    "state": opp_data.get("placeOfPerformance", {}).get("state", {}).get("code", ""),
                    "zip": opp_data.get("placeOfPerformance", {}).get("zip", ""),
                    "country": opp_data.get("placeOfPerformance", {}).get("country", {}).get("code", "USA"),
                },
                "point_of_contact": opp_data.get("pointOfContact", []),
                "ui_link": opp_data.get("uiLink", f"https://sam.gov/opp/{opportunity_id}/view"),
                "active": opp_data.get("active", "Yes") == "Yes",
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch opportunity {opportunity_id}: {e}")
            return None
```

**Step 4: Run test to verify it passes**

```bash
PYTHONPATH=. python -m pytest tests/test_sam_gov_client.py::TestSAMGovClientOpportunityDetails::test_get_opportunity_details_success -v
```

Expected: PASS

**Step 5: Run all new tests**

```bash
PYTHONPATH=. python -m pytest tests/test_sam_gov_client.py -v
```

Expected: All tests PASS

**Step 6: Commit**

```bash
git add src/agents/sam_gov_client.py tests/test_sam_gov_client.py
git commit -m "feat(sam-gov): add get_opportunity_details method for full opportunity data"
```

---

## Task 2: Add Entity Registration Verification to SAMGovClient

**Files:**
- Modify: `src/agents/sam_gov_client.py`
- Test: `tests/test_sam_gov_client.py`

**Step 1: Write the failing test**

Add to `tests/test_sam_gov_client.py`:

```python
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
```

**Step 2: Run test to verify it fails**

```bash
PYTHONPATH=. python -m pytest tests/test_sam_gov_client.py::TestSAMGovClientEntityVerification::test_verify_entity_registration_active -v
```

Expected: FAIL with `AttributeError: 'SAMGovClient' object has no attribute 'verify_entity_registration'`

**Step 3: Implement entity verification methods**

Add to `src/agents/sam_gov_client.py` (after `get_opportunity_details`):

```python
    def verify_entity_registration(
        self,
        uei: str | None = None,
        cage_code: str | None = None,
        legal_name: str | None = None
    ) -> dict:
        """
        Verify if an entity is registered in SAM.gov.

        Args:
            uei: Unique Entity Identifier (12-character)
            cage_code: CAGE/NCAGE code (5-character)
            legal_name: Legal business name (partial match supported)

        Returns:
            Dict with registration status and basic info
        """
        if not any([uei, cage_code, legal_name]):
            raise ValueError("At least one of uei, cage_code, or legal_name required")

        params = {
            "api_key": self.api_key,
            "registrationStatus": "A",  # Active only
            "includeSections": "entityRegistration",
        }

        if uei:
            params["ueiSAM"] = uei
        elif cage_code:
            params["cageCode"] = cage_code
        elif legal_name:
            params["legalBusinessName"] = legal_name

        try:
            response = requests.get(
                self.entity_base_url,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            if data.get("totalRecords", 0) == 0:
                return {
                    "is_registered": False,
                    "registration_status": None,
                    "uei": uei,
                    "legal_name": None,
                    "expiration_date": None,
                }

            entity = data["entityData"][0]
            reg = entity.get("entityRegistration", {})

            return {
                "is_registered": reg.get("samRegistered") == "Yes",
                "registration_status": reg.get("registrationStatus"),
                "uei": reg.get("ueiSAM"),
                "cage_code": reg.get("cageCode"),
                "legal_name": reg.get("legalBusinessName"),
                "expiration_date": reg.get("registrationExpirationDate"),
                "purpose": reg.get("purposeOfRegistrationDesc"),
                "naics_codes": self._extract_naics_from_entity(entity),
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Entity verification failed: {e}")
            return {
                "is_registered": False,
                "error": str(e),
            }

    def get_entity_profile(self, uei: str) -> dict | None:
        """
        Fetch complete entity profile for auto-populating company data.

        Args:
            uei: Unique Entity Identifier

        Returns:
            Complete entity profile dict or None if not found
        """
        params = {
            "api_key": self.api_key,
            "ueiSAM": uei,
            "includeSections": "entityRegistration,coreData,assertions",
        }

        try:
            response = requests.get(
                self.entity_base_url,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            if data.get("totalRecords", 0) == 0:
                return None

            entity = data["entityData"][0]
            reg = entity.get("entityRegistration", {})
            core = entity.get("coreData", {})
            assertions = entity.get("assertions", {})

            # Extract address
            phys_addr = core.get("physicalAddress", {})
            address = {
                "street": phys_addr.get("addressLine1", ""),
                "street2": phys_addr.get("addressLine2", ""),
                "city": phys_addr.get("city", ""),
                "state": phys_addr.get("stateOrProvinceCode", ""),
                "zip": phys_addr.get("zipCode", ""),
                "country": phys_addr.get("countryCode", "USA"),
            }

            # Extract business types
            business_types = []
            bt_data = core.get("businessTypes", {})
            for bt in bt_data.get("businessTypeList", []):
                business_types.append({
                    "code": bt.get("businessTypeCode"),
                    "description": bt.get("businessTypeDesc"),
                })

            # Extract NAICS codes
            naics_codes = []
            goods = assertions.get("goodsAndServices", {})
            for naics in goods.get("naicsList", []):
                naics_codes.append({
                    "code": naics.get("naicsCode"),
                    "description": naics.get("naicsDescription"),
                    "small_business": naics.get("sbaSmallBusiness") == "Y",
                })

            # Extract PSC codes
            psc_codes = []
            for psc in goods.get("pscList", []):
                psc_codes.append({
                    "code": psc.get("pscCode"),
                    "description": psc.get("pscDescription"),
                })

            # Determine set-aside eligibility
            sba_types = bt_data.get("sbaBusinessTypeList", [])
            set_aside_eligibility = {
                "small_business": any(
                    n.get("small_business") for n in naics_codes
                ),
                "8a_certified": any(
                    "8(a)" in t.get("sbaBusinessTypeDesc", "") for t in sba_types
                ),
                "hubzone": any(
                    "HUBZone" in t.get("sbaBusinessTypeDesc", "") for t in sba_types
                ),
                "woman_owned": any(
                    "Woman" in t.get("businessTypeDesc", "") for t in bt_data.get("businessTypeList", [])
                ),
                "veteran_owned": any(
                    "Veteran" in t.get("businessTypeDesc", "") for t in bt_data.get("businessTypeList", [])
                ),
                "sdvosb": any(
                    "Service-Disabled" in t.get("businessTypeDesc", "") for t in bt_data.get("businessTypeList", [])
                ),
            }

            return {
                "uei": reg.get("ueiSAM"),
                "cage_code": reg.get("cageCode"),
                "legal_name": reg.get("legalBusinessName"),
                "dba_name": core.get("entityInformation", {}).get("entityDBAName"),
                "registration_status": reg.get("registrationStatus"),
                "registration_expiration": reg.get("registrationExpirationDate"),
                "address": address,
                "website": core.get("entityInformation", {}).get("entityURL"),
                "business_types": business_types,
                "naics_codes": naics_codes,
                "primary_naics": goods.get("primaryNaics"),
                "psc_codes": psc_codes,
                "set_aside_eligibility": set_aside_eligibility,
                "purpose": reg.get("purposeOfRegistrationDesc"),
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch entity profile: {e}")
            return None

    def _extract_naics_from_entity(self, entity: dict) -> list[str]:
        """Extract NAICS codes from entity data."""
        naics = []
        assertions = entity.get("assertions", {})
        goods = assertions.get("goodsAndServices", {})
        for n in goods.get("naicsList", []):
            if n.get("naicsCode"):
                naics.append(n["naicsCode"])
        return naics
```

**Step 4: Run tests to verify they pass**

```bash
PYTHONPATH=. python -m pytest tests/test_sam_gov_client.py::TestSAMGovClientEntityVerification -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/agents/sam_gov_client.py tests/test_sam_gov_client.py
git commit -m "feat(sam-gov): add entity registration verification and profile fetching"
```

---

## Task 3: Add Opportunity Amendments Tracking to SAMGovClient

**Files:**
- Modify: `src/agents/sam_gov_client.py`
- Test: `tests/test_sam_gov_client.py`

**Step 1: Write the failing test**

Add to `tests/test_sam_gov_client.py`:

```python
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
```

**Step 2: Run test to verify it fails**

```bash
PYTHONPATH=. python -m pytest tests/test_sam_gov_client.py::TestSAMGovClientAmendments::test_get_amendments_for_opportunity -v
```

Expected: FAIL with `AttributeError`

**Step 3: Implement get_amendments method**

Add to `src/agents/sam_gov_client.py`:

```python
    def get_amendments(
        self,
        solicitation_number: str | None = None,
        parent_notice_id: str | None = None,
        days_back: int = 365
    ) -> list[dict]:
        """
        Fetch amendment history for a solicitation.

        Args:
            solicitation_number: The solicitation number to search
            parent_notice_id: Parent opportunity ID
            days_back: How far back to search

        Returns:
            List of amendments sorted by date (newest first)
        """
        from_date = (datetime.now() - timedelta(days=days_back)).strftime("%m/%d/%Y")
        to_date = datetime.now().strftime("%m/%d/%Y")

        params = {
            "api_key": self.api_key,
            "postedFrom": from_date,
            "postedTo": to_date,
            "ptype": "a",  # Amendments only
            "limit": 100,
        }

        if solicitation_number:
            params["solnum"] = solicitation_number

        try:
            response = requests.get(
                f"{self.opportunities_base_url}/search",
                params=params,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            amendments = []
            for opp in data.get("opportunitiesData", []):
                amendments.append({
                    "notice_id": opp.get("noticeId"),
                    "title": opp.get("title"),
                    "posted_date": opp.get("postedDate"),
                    "type": opp.get("type"),
                    "parent_notice_id": opp.get("parentNoticeId"),
                    "description": opp.get("description", {}).get("body", "") if isinstance(opp.get("description"), dict) else "",
                    "ui_link": opp.get("uiLink"),
                })

            # Sort by posted date descending
            amendments.sort(
                key=lambda x: datetime.strptime(x["posted_date"], "%Y-%m-%d") if x.get("posted_date") else datetime.min,
                reverse=True
            )

            return amendments

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch amendments: {e}")
            return []
```

**Step 4: Run test to verify it passes**

```bash
PYTHONPATH=. python -m pytest tests/test_sam_gov_client.py::TestSAMGovClientAmendments -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/agents/sam_gov_client.py tests/test_sam_gov_client.py
git commit -m "feat(sam-gov): add amendment history tracking"
```

---

## Task 4: Create SAM.gov Sync Service

**Files:**
- Create: `api/app/services/sam_gov_sync.py`
- Test: `tests/api/test_sam_gov_sync.py` (create)

**Step 1: Write the failing test**

Create `tests/api/test_sam_gov_sync.py`:

```python
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

        result = await sync_service.sync_opportunities(days_back=7)

        assert result["new_count"] >= 0
        assert result["status"] == "completed"

    @patch("api.app.services.sam_gov_sync.SAMGovClient")
    async def test_check_tracked_opportunities_updates(self, mock_client_class, sync_service):
        """Test checking tracked opportunities for updates."""
        mock_client = MagicMock()
        mock_client.get_opportunity_details.return_value = {
            "opportunity_id": "opp1",
            "title": "Updated Title",
            "response_deadline": "2025-03-01",
        }
        mock_client_class.return_value = mock_client

        # Mock tracked opportunities
        tracked_ids = ["opp1", "opp2"]

        result = await sync_service.check_for_updates(tracked_ids)

        assert "updates" in result
```

**Step 2: Run test to verify it fails**

```bash
PYTHONPATH=. python -m pytest tests/api/test_sam_gov_sync.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'api.app.services.sam_gov_sync'`

**Step 3: Implement SAMGovSyncService**

Create `api/app/services/sam_gov_sync.py`:

```python
"""SAM.gov synchronization service for real-time opportunity tracking."""
import asyncio
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from sqlalchemy.orm import Session

from api.app.core.config import settings
from api.app.models.database import RFPOpportunity, get_db
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
                        existing = db.query(RFPOpportunity).filter(
                            RFPOpportunity.source_url.contains(opp.get("notice_id", ""))
                        ).first()

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
            existing.response_deadline = new_data["response_deadline"]
        if new_data.get("award_amount"):
            existing.award_amount = new_data["award_amount"]
        existing.last_scraped_at = datetime.utcnow()

    def _create_opportunity(self, db: Session, data: dict) -> RFPOpportunity:
        """Create new opportunity from SAM.gov data."""
        opp = RFPOpportunity(
            title=data.get("title", ""),
            solicitation_number=data.get("solicitation_number"),
            agency=data.get("agency"),
            office=data.get("office"),
            description=data.get("description", ""),
            posted_date=data.get("posted_date"),
            response_deadline=data.get("response_deadline"),
            naics_code=data.get("naics_code"),
            set_aside_type=data.get("set_aside"),
            award_amount=data.get("award_amount"),
            source_url=data.get("url") or f"https://sam.gov/opp/{data.get('notice_id')}/view",
            source_platform="SAM.gov",
            last_scraped_at=datetime.utcnow(),
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
```

**Step 4: Run tests to verify they pass**

```bash
PYTHONPATH=. python -m pytest tests/api/test_sam_gov_sync.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add api/app/services/sam_gov_sync.py tests/api/test_sam_gov_sync.py
git commit -m "feat(sam-gov): add sync service for real-time opportunity tracking"
```

---

## Task 5: Create SAM.gov Sync API Routes

**Files:**
- Create: `api/app/routes/sam_gov.py`
- Modify: `api/app/main.py`
- Test: `tests/api/test_sam_gov_routes.py` (create)

**Step 1: Write the failing test**

Create `tests/api/test_sam_gov_routes.py`:

```python
"""Tests for SAM.gov API routes."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from api.app.main import app


client = TestClient(app)


class TestSAMGovRoutes:
    """Test SAM.gov integration routes."""

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
        mock_service.sync_opportunities.return_value = {
            "status": "completed",
            "new_count": 5,
        }
        mock_get_service.return_value = mock_service

        response = client.post("/api/v1/sam-gov/sync", json={
            "days_back": 7,
            "limit": 50
        })

        assert response.status_code == 200

    def test_verify_entity_missing_params(self):
        """Test entity verification without required params."""
        response = client.get("/api/v1/sam-gov/entity/verify")

        assert response.status_code == 422  # Validation error

    @patch("api.app.routes.sam_gov.get_sync_service")
    def test_verify_entity_by_uei(self, mock_get_service):
        """Test entity verification by UEI."""
        mock_service = MagicMock()
        mock_service.verify_entity.return_value = {
            "is_registered": True,
            "registration_status": "Active",
            "uei": "ZQGGHJH74DW7",
        }
        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/sam-gov/entity/verify?uei=ZQGGHJH74DW7")

        assert response.status_code == 200
        data = response.json()
        assert data["is_registered"] is True

    @patch("api.app.routes.sam_gov.get_sync_service")
    def test_get_entity_profile(self, mock_get_service):
        """Test getting full entity profile."""
        mock_service = MagicMock()
        mock_service.get_entity_profile.return_value = {
            "uei": "ZQGGHJH74DW7",
            "legal_name": "ACME Corp",
            "set_aside_eligibility": {"small_business": True},
        }
        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/sam-gov/entity/ZQGGHJH74DW7/profile")

        assert response.status_code == 200
        data = response.json()
        assert data["legal_name"] == "ACME Corp"
```

**Step 2: Run test to verify it fails**

```bash
PYTHONPATH=. python -m pytest tests/api/test_sam_gov_routes.py -v
```

Expected: FAIL (route not found)

**Step 3: Create SAM.gov routes**

Create `api/app/routes/sam_gov.py`:

```python
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
    registration_status: str | None
    uei: str | None
    cage_code: str | None
    legal_name: str | None
    expiration_date: str | None
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
```

**Step 4: Register routes in main.py**

Add to `api/app/main.py` in the imports section:

```python
from app.routes import sam_gov
```

Add in the router registration section:

```python
app.include_router(
    sam_gov.router,
    prefix=f"{settings.API_V1_STR}/sam-gov",
    tags=["sam-gov"],
)
```

**Step 5: Run tests to verify they pass**

```bash
PYTHONPATH=. python -m pytest tests/api/test_sam_gov_routes.py -v
```

Expected: All tests PASS

**Step 6: Commit**

```bash
git add api/app/routes/sam_gov.py api/app/main.py tests/api/test_sam_gov_routes.py
git commit -m "feat(sam-gov): add API routes for sync, entity verification, and amendments"
```

---

## Task 6: Add Celery Background Sync Task

**Files:**
- Modify: `src/celery_app.py` (or create if not exists)
- Modify: `src/tasks.py` (or create if not exists)
- Test: `tests/test_celery_tasks.py`

**Step 1: Write the failing test**

Create or update `tests/test_celery_tasks.py`:

```python
"""Tests for Celery background tasks."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from src.tasks import sync_sam_gov_opportunities, check_tracked_opportunities


class TestSAMGovCeleryTasks:
    """Test SAM.gov Celery tasks."""

    @patch("src.tasks.SAMGovSyncService")
    def test_sync_sam_gov_opportunities_task(self, mock_service_class):
        """Test periodic sync task."""
        mock_service = MagicMock()
        mock_service.sync_opportunities = AsyncMock(return_value={
            "status": "completed",
            "new_count": 3
        })
        mock_service_class.return_value = mock_service

        result = sync_sam_gov_opportunities.apply(args=[7, 100]).get()

        assert result["status"] == "completed"

    @patch("src.tasks.SAMGovSyncService")
    def test_check_tracked_opportunities_task(self, mock_service_class):
        """Test update check task."""
        mock_service = MagicMock()
        mock_service.check_for_updates = AsyncMock(return_value={
            "status": "completed",
            "updates": []
        })
        mock_service_class.return_value = mock_service

        result = check_tracked_opportunities.apply(args=[["opp1", "opp2"]]).get()

        assert result["status"] == "completed"
```

**Step 2: Run test to verify it fails**

```bash
PYTHONPATH=. python -m pytest tests/test_celery_tasks.py::TestSAMGovCeleryTasks -v
```

Expected: FAIL (tasks not defined)

**Step 3: Add Celery tasks**

Add to `src/tasks.py`:

```python
"""Celery background tasks for SAM.gov sync."""
import asyncio
import logging
from datetime import datetime

from celery import shared_task

from api.app.services.sam_gov_sync import SAMGovSyncService
from api.app.core.database import SessionLocal
from api.app.websockets.websocket_router import manager

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def sync_sam_gov_opportunities(self, days_back: int = 7, limit: int = 100):
    """
    Background task to sync opportunities from SAM.gov.

    Runs periodically (configured in celery beat schedule).
    Retries up to 3 times on failure with 5 minute delay.
    """
    logger.info(f"Starting SAM.gov sync: days_back={days_back}, limit={limit}")

    try:
        service = SAMGovSyncService()
        db = SessionLocal()

        try:
            # Run async sync in event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            result = loop.run_until_complete(
                service.sync_opportunities(days_back=days_back, limit=limit, db=db)
            )

            # Broadcast completion
            loop.run_until_complete(
                manager.broadcast({
                    "type": "sam_gov_sync_complete",
                    "data": result,
                    "timestamp": datetime.utcnow().isoformat()
                })
            )

            loop.close()

            logger.info(f"SAM.gov sync completed: {result}")
            return result

        finally:
            db.close()

    except Exception as e:
        logger.error(f"SAM.gov sync failed: {e}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=2)
def check_tracked_opportunities(self, opportunity_ids: list[str]):
    """
    Background task to check tracked opportunities for updates.

    Checks for amendments, deadline extensions, and other changes.
    """
    logger.info(f"Checking {len(opportunity_ids)} tracked opportunities for updates")

    try:
        service = SAMGovSyncService()
        db = SessionLocal()

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            result = loop.run_until_complete(
                service.check_for_updates(opportunity_ids=opportunity_ids, db=db)
            )

            # If updates found, broadcast notification
            if result.get("updates"):
                loop.run_until_complete(
                    manager.broadcast({
                        "type": "opportunity_updates_found",
                        "data": result,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                )

            loop.close()

            logger.info(f"Update check completed: {len(result.get('updates', []))} updates found")
            return result

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Update check failed: {e}")
        raise self.retry(exc=e)


@shared_task
def verify_entity_registration(uei: str):
    """
    Background task to verify entity registration.

    Used for async entity verification without blocking API.
    """
    service = SAMGovSyncService()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    result = loop.run_until_complete(service.verify_entity(uei))
    loop.close()

    return result
```

**Step 4: Add Celery Beat schedule for periodic sync**

Update `src/celery_app.py` to include beat schedule:

```python
# Add to celery_app.py configuration

from celery.schedules import crontab

app.conf.beat_schedule = {
    # Sync SAM.gov every 15 minutes during business hours
    'sync-sam-gov-opportunities': {
        'task': 'src.tasks.sync_sam_gov_opportunities',
        'schedule': crontab(minute='*/15', hour='8-18', day_of_week='mon-fri'),
        'args': (7, 100),  # days_back, limit
    },
    # Check tracked opportunities every hour
    'check-tracked-opportunities': {
        'task': 'src.tasks.check_tracked_opportunities_periodic',
        'schedule': crontab(minute=0),  # Every hour at :00
    },
}
```

**Step 5: Run tests**

```bash
PYTHONPATH=. python -m pytest tests/test_celery_tasks.py::TestSAMGovCeleryTasks -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add src/tasks.py src/celery_app.py tests/test_celery_tasks.py
git commit -m "feat(sam-gov): add Celery tasks for periodic sync and update checks"
```

---

## Task 7: Create Frontend SAM.gov Sync Status Component

**Files:**
- Create: `frontend/src/components/sam-gov/SyncStatus.tsx`
- Create: `frontend/src/components/sam-gov/index.ts`
- Test: Manual browser testing

**Step 1: Create SyncStatus component**

Create `frontend/src/components/sam-gov/SyncStatus.tsx`:

```typescript
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  RefreshCw,
  CheckCircle2,
  XCircle,
  Clock,
  AlertCircle,
  Wifi,
  WifiOff,
} from 'lucide-react';
import { api } from '@/services/api';
import { toast } from 'sonner';
import { formatDistanceToNow } from 'date-fns';

interface SyncStatusData {
  status: 'idle' | 'syncing' | 'completed' | 'error';
  last_sync: string | null;
  last_error: string | null;
  opportunities_synced: number;
  is_connected: boolean;
  api_key_configured: boolean;
}

export function SyncStatus() {
  const queryClient = useQueryClient();
  const [daysBack, setDaysBack] = useState(7);

  const { data: status, isLoading } = useQuery({
    queryKey: ['sam-gov-status'],
    queryFn: () => api.getSAMGovSyncStatus(),
    refetchInterval: 10000, // Poll every 10 seconds
  });

  const syncMutation = useMutation({
    mutationFn: () => api.triggerSAMGovSync({ days_back: daysBack, limit: 100 }),
    onSuccess: () => {
      toast.success('SAM.gov sync started');
      queryClient.invalidateQueries({ queryKey: ['sam-gov-status'] });
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Sync failed');
    },
  });

  const getStatusIcon = () => {
    if (!status?.is_connected) return <WifiOff className="h-5 w-5 text-red-500" />;
    switch (status?.status) {
      case 'syncing':
        return <RefreshCw className="h-5 w-5 text-blue-500 animate-spin" />;
      case 'completed':
        return <CheckCircle2 className="h-5 w-5 text-green-500" />;
      case 'error':
        return <XCircle className="h-5 w-5 text-red-500" />;
      default:
        return <Clock className="h-5 w-5 text-gray-500" />;
    }
  };

  const getStatusBadge = () => {
    if (!status?.api_key_configured) {
      return <Badge variant="destructive">Not Configured</Badge>;
    }
    if (!status?.is_connected) {
      return <Badge variant="destructive">Disconnected</Badge>;
    }
    switch (status?.status) {
      case 'syncing':
        return <Badge variant="secondary" className="bg-blue-100 text-blue-800">Syncing</Badge>;
      case 'completed':
        return <Badge variant="secondary" className="bg-green-100 text-green-800">Connected</Badge>;
      case 'error':
        return <Badge variant="destructive">Error</Badge>;
      default:
        return <Badge variant="secondary">Idle</Badge>;
    }
  };

  if (isLoading) {
    return (
      <Card className="w-full">
        <CardContent className="py-4">
          <div className="animate-pulse flex items-center gap-4">
            <div className="h-10 w-10 bg-gray-200 rounded-full" />
            <div className="flex-1 space-y-2">
              <div className="h-4 bg-gray-200 rounded w-1/4" />
              <div className="h-3 bg-gray-200 rounded w-1/3" />
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="w-full">
      <CardHeader className="py-4 flex flex-row items-center justify-between">
        <CardTitle className="text-lg flex items-center gap-2">
          {status?.is_connected ? (
            <Wifi className="h-5 w-5 text-green-500" />
          ) : (
            <WifiOff className="h-5 w-5 text-red-500" />
          )}
          SAM.gov Integration
        </CardTitle>
        {getStatusBadge()}
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {getStatusIcon()}
            <div>
              <p className="font-medium">
                {status?.status === 'syncing' ? 'Syncing...' : 'Last Sync'}
              </p>
              <p className="text-sm text-muted-foreground">
                {status?.last_sync
                  ? formatDistanceToNow(new Date(status.last_sync), { addSuffix: true })
                  : 'Never'}
              </p>
            </div>
          </div>
          <div className="text-right">
            <p className="text-2xl font-bold">{status?.opportunities_synced || 0}</p>
            <p className="text-xs text-muted-foreground">Opportunities Synced</p>
          </div>
        </div>

        {status?.last_error && (
          <div className="flex items-start gap-2 p-3 bg-red-50 rounded-lg text-red-800">
            <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
            <p className="text-sm">{status.last_error}</p>
          </div>
        )}

        <div className="flex items-center gap-2">
          <select
            value={daysBack}
            onChange={(e) => setDaysBack(Number(e.target.value))}
            className="h-9 rounded-md border border-input bg-background px-3 text-sm"
          >
            <option value={1}>Last 24 hours</option>
            <option value={7}>Last 7 days</option>
            <option value={14}>Last 14 days</option>
            <option value={30}>Last 30 days</option>
          </select>
          <Button
            onClick={() => syncMutation.mutate()}
            disabled={syncMutation.isPending || status?.status === 'syncing'}
            className="flex-1"
          >
            {syncMutation.isPending || status?.status === 'syncing' ? (
              <>
                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                Syncing...
              </>
            ) : (
              <>
                <RefreshCw className="h-4 w-4 mr-2" />
                Sync Now
              </>
            )}
          </Button>
        </div>

        {!status?.api_key_configured && (
          <p className="text-sm text-muted-foreground text-center">
            Configure SAM_GOV_API_KEY in environment to enable sync
          </p>
        )}
      </CardContent>
    </Card>
  );
}
```

**Step 2: Create barrel export**

Create `frontend/src/components/sam-gov/index.ts`:

```typescript
export { SyncStatus } from './SyncStatus';
```

**Step 3: Commit**

```bash
git add frontend/src/components/sam-gov/
git commit -m "feat(frontend): add SAM.gov sync status component"
```

---

## Task 8: Add SAM.gov API Methods to Frontend Service

**Files:**
- Modify: `frontend/src/services/api.ts`

**Step 1: Add API methods**

Add to `frontend/src/services/api.ts`:

```typescript
// SAM.gov Integration
getSAMGovSyncStatus: () =>
  apiClient.get('/sam-gov/status').then(res => res.data),

triggerSAMGovSync: (params: { days_back: number; limit: number }) =>
  apiClient.post('/sam-gov/sync', params).then(res => res.data),

checkSAMGovUpdates: (opportunityIds: string[]) =>
  apiClient.post('/sam-gov/check-updates', { opportunity_ids: opportunityIds }).then(res => res.data),

verifyEntityRegistration: (params: { uei?: string; cage_code?: string; legal_name?: string }) =>
  apiClient.get('/sam-gov/entity/verify', { params }).then(res => res.data),

getEntityProfile: (uei: string) =>
  apiClient.get(`/sam-gov/entity/${uei}/profile`).then(res => res.data),

getOpportunityFromSAM: (noticeId: string) =>
  apiClient.get(`/sam-gov/opportunity/${noticeId}`).then(res => res.data),

getOpportunityAmendments: (noticeId: string, daysBack?: number) =>
  apiClient.get(`/sam-gov/opportunity/${noticeId}/amendments`, {
    params: { days_back: daysBack }
  }).then(res => res.data),

syncCompanyFromSAM: (uei: string) =>
  apiClient.post('/sam-gov/company-profile/sync', null, { params: { uei } }).then(res => res.data),
```

**Step 2: Commit**

```bash
git add frontend/src/services/api.ts
git commit -m "feat(frontend): add SAM.gov API methods to frontend service"
```

---

## Task 9: Add Entity Verification Component

**Files:**
- Create: `frontend/src/components/sam-gov/EntityVerification.tsx`
- Modify: `frontend/src/components/sam-gov/index.ts`

**Step 1: Create EntityVerification component**

Create `frontend/src/components/sam-gov/EntityVerification.tsx`:

```typescript
import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  CheckCircle2,
  XCircle,
  Search,
  Building2,
  Calendar,
  FileText,
} from 'lucide-react';
import { api } from '@/services/api';
import { toast } from 'sonner';

interface EntityData {
  is_registered: boolean;
  registration_status: string | null;
  uei: string | null;
  cage_code: string | null;
  legal_name: string | null;
  expiration_date: string | null;
  naics_codes: string[];
  error?: string;
}

interface EntityProfileData {
  uei: string;
  cage_code: string;
  legal_name: string;
  dba_name?: string;
  registration_status: string;
  registration_expiration: string;
  address: {
    street: string;
    city: string;
    state: string;
    zip: string;
  };
  website?: string;
  primary_naics: string;
  naics_codes: Array<{ code: string; description: string; small_business: boolean }>;
  set_aside_eligibility: {
    small_business: boolean;
    '8a_certified': boolean;
    hubzone: boolean;
    woman_owned: boolean;
    veteran_owned: boolean;
    sdvosb: boolean;
  };
}

interface EntityVerificationProps {
  onProfileLoaded?: (profile: EntityProfileData) => void;
}

export function EntityVerification({ onProfileLoaded }: EntityVerificationProps) {
  const [uei, setUei] = useState('');
  const [entityData, setEntityData] = useState<EntityData | null>(null);
  const [profileData, setProfileData] = useState<EntityProfileData | null>(null);

  const verifyMutation = useMutation({
    mutationFn: () => api.verifyEntityRegistration({ uei }),
    onSuccess: (data) => {
      setEntityData(data);
      if (data.is_registered) {
        toast.success('Entity verified successfully');
      } else {
        toast.warning('Entity not found or not registered');
      }
    },
    onError: () => {
      toast.error('Verification failed');
    },
  });

  const profileMutation = useMutation({
    mutationFn: () => api.getEntityProfile(uei),
    onSuccess: (data) => {
      setProfileData(data);
      onProfileLoaded?.(data);
      toast.success('Profile loaded');
    },
    onError: () => {
      toast.error('Failed to load profile');
    },
  });

  const handleVerify = () => {
    if (uei.length !== 12) {
      toast.error('UEI must be 12 characters');
      return;
    }
    setEntityData(null);
    setProfileData(null);
    verifyMutation.mutate();
  };

  return (
    <Card>
      <CardHeader className="py-4">
        <CardTitle className="text-lg flex items-center gap-2">
          <Building2 className="h-5 w-5" />
          SAM.gov Entity Verification
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex gap-2">
          <Input
            placeholder="Enter 12-character UEI"
            value={uei}
            onChange={(e) => setUei(e.target.value.toUpperCase())}
            maxLength={12}
            className="font-mono"
          />
          <Button
            onClick={handleVerify}
            disabled={verifyMutation.isPending || uei.length !== 12}
          >
            <Search className="h-4 w-4 mr-2" />
            Verify
          </Button>
        </div>

        {entityData && (
          <div className="space-y-4">
            <div className="flex items-center gap-2 p-4 rounded-lg bg-muted">
              {entityData.is_registered ? (
                <CheckCircle2 className="h-6 w-6 text-green-500" />
              ) : (
                <XCircle className="h-6 w-6 text-red-500" />
              )}
              <div className="flex-1">
                <p className="font-medium">
                  {entityData.is_registered ? 'Registered' : 'Not Registered'}
                </p>
                {entityData.legal_name && (
                  <p className="text-sm text-muted-foreground">
                    {entityData.legal_name}
                  </p>
                )}
              </div>
              {entityData.registration_status && (
                <Badge
                  variant="secondary"
                  className={
                    entityData.registration_status === 'Active'
                      ? 'bg-green-100 text-green-800'
                      : 'bg-yellow-100 text-yellow-800'
                  }
                >
                  {entityData.registration_status}
                </Badge>
              )}
            </div>

            {entityData.is_registered && (
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-muted-foreground">UEI</p>
                  <p className="font-mono">{entityData.uei}</p>
                </div>
                {entityData.cage_code && (
                  <div>
                    <p className="text-muted-foreground">CAGE Code</p>
                    <p className="font-mono">{entityData.cage_code}</p>
                  </div>
                )}
                {entityData.expiration_date && (
                  <div>
                    <p className="text-muted-foreground">Expires</p>
                    <p className="flex items-center gap-1">
                      <Calendar className="h-3 w-3" />
                      {new Date(entityData.expiration_date).toLocaleDateString()}
                    </p>
                  </div>
                )}
                {entityData.naics_codes.length > 0 && (
                  <div className="col-span-2">
                    <p className="text-muted-foreground mb-1">NAICS Codes</p>
                    <div className="flex flex-wrap gap-1">
                      {entityData.naics_codes.slice(0, 5).map((code) => (
                        <Badge key={code} variant="outline" className="font-mono">
                          {code}
                        </Badge>
                      ))}
                      {entityData.naics_codes.length > 5 && (
                        <Badge variant="outline">
                          +{entityData.naics_codes.length - 5} more
                        </Badge>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}

            {entityData.is_registered && !profileData && (
              <Button
                variant="outline"
                className="w-full"
                onClick={() => profileMutation.mutate()}
                disabled={profileMutation.isPending}
              >
                <FileText className="h-4 w-4 mr-2" />
                Load Full Profile
              </Button>
            )}
          </div>
        )}

        {profileData && (
          <div className="space-y-4 pt-4 border-t">
            <h4 className="font-medium">Set-Aside Eligibility</h4>
            <div className="flex flex-wrap gap-2">
              {profileData.set_aside_eligibility.small_business && (
                <Badge className="bg-blue-100 text-blue-800">Small Business</Badge>
              )}
              {profileData.set_aside_eligibility['8a_certified'] && (
                <Badge className="bg-purple-100 text-purple-800">8(a) Certified</Badge>
              )}
              {profileData.set_aside_eligibility.hubzone && (
                <Badge className="bg-green-100 text-green-800">HUBZone</Badge>
              )}
              {profileData.set_aside_eligibility.woman_owned && (
                <Badge className="bg-pink-100 text-pink-800">Woman-Owned</Badge>
              )}
              {profileData.set_aside_eligibility.veteran_owned && (
                <Badge className="bg-orange-100 text-orange-800">Veteran-Owned</Badge>
              )}
              {profileData.set_aside_eligibility.sdvosb && (
                <Badge className="bg-red-100 text-red-800">SDVOSB</Badge>
              )}
            </div>

            {profileData.address && (
              <div>
                <p className="text-muted-foreground text-sm">Address</p>
                <p>
                  {profileData.address.street}, {profileData.address.city},{' '}
                  {profileData.address.state} {profileData.address.zip}
                </p>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
```

**Step 2: Update barrel export**

Update `frontend/src/components/sam-gov/index.ts`:

```typescript
export { SyncStatus } from './SyncStatus';
export { EntityVerification } from './EntityVerification';
```

**Step 3: Commit**

```bash
git add frontend/src/components/sam-gov/
git commit -m "feat(frontend): add entity verification component"
```

---

## Task 10: Integrate SAM.gov Components into Discovery Page

**Files:**
- Modify: `frontend/src/pages/RFPDiscovery.tsx`

**Step 1: Add SAM.gov sync status to Discovery page**

Add imports at top of `frontend/src/pages/RFPDiscovery.tsx`:

```typescript
import { SyncStatus } from '@/components/sam-gov/SyncStatus';
```

**Step 2: Add SyncStatus component to the page layout**

In the Discovery page, add the SyncStatus card in an appropriate location (e.g., sidebar or top of page):

```tsx
{/* Add near the top of the page content or in sidebar */}
<div className="mb-6">
  <SyncStatus />
</div>
```

**Step 3: Commit**

```bash
git add frontend/src/pages/RFPDiscovery.tsx
git commit -m "feat(frontend): integrate SAM.gov sync status into Discovery page"
```

---

## Task 11: Add Amendment History Component

**Files:**
- Create: `frontend/src/components/sam-gov/AmendmentHistory.tsx`
- Modify: `frontend/src/components/sam-gov/index.ts`

**Step 1: Create AmendmentHistory component**

Create `frontend/src/components/sam-gov/AmendmentHistory.tsx`:

```typescript
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  FileEdit,
  Calendar,
  ExternalLink,
  AlertCircle,
} from 'lucide-react';
import { api } from '@/services/api';
import { formatDistanceToNow } from 'date-fns';

interface Amendment {
  notice_id: string;
  title: string;
  posted_date: string;
  type: string;
  parent_notice_id: string;
  description: string;
  ui_link: string;
}

interface AmendmentHistoryProps {
  opportunityId: string;
  solicitationNumber?: string;
}

export function AmendmentHistory({ opportunityId, solicitationNumber }: AmendmentHistoryProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['amendments', opportunityId],
    queryFn: () => api.getOpportunityAmendments(opportunityId),
    enabled: !!opportunityId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  if (isLoading) {
    return (
      <Card>
        <CardHeader className="py-4">
          <Skeleton className="h-6 w-48" />
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-20 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="py-6">
          <div className="flex items-center gap-2 text-muted-foreground">
            <AlertCircle className="h-4 w-4" />
            <span>Failed to load amendment history</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  const amendments = data?.amendments || [];

  return (
    <Card>
      <CardHeader className="py-4 flex flex-row items-center justify-between">
        <CardTitle className="text-lg flex items-center gap-2">
          <FileEdit className="h-5 w-5" />
          Amendment History
        </CardTitle>
        <Badge variant="secondary">
          {amendments.length} Amendment{amendments.length !== 1 ? 's' : ''}
        </Badge>
      </CardHeader>
      <CardContent>
        {amendments.length === 0 ? (
          <p className="text-muted-foreground text-center py-4">
            No amendments found for this solicitation
          </p>
        ) : (
          <ScrollArea className="h-[300px] pr-4">
            <div className="space-y-3">
              {amendments.map((amendment: Amendment, index: number) => (
                <div
                  key={amendment.notice_id}
                  className="p-3 rounded-lg border bg-card hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <Badge
                          variant="outline"
                          className="shrink-0 text-xs"
                        >
                          #{amendments.length - index}
                        </Badge>
                        <span className="text-sm font-medium truncate">
                          {amendment.title}
                        </span>
                      </div>
                      {amendment.description && (
                        <p className="text-xs text-muted-foreground line-clamp-2 mb-2">
                          {amendment.description}
                        </p>
                      )}
                      <div className="flex items-center gap-3 text-xs text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <Calendar className="h-3 w-3" />
                          {amendment.posted_date
                            ? formatDistanceToNow(new Date(amendment.posted_date), { addSuffix: true })
                            : 'Unknown date'}
                        </span>
                      </div>
                    </div>
                    {amendment.ui_link && (
                      <a
                        href={amendment.ui_link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="shrink-0 p-1 hover:bg-muted rounded"
                      >
                        <ExternalLink className="h-4 w-4 text-muted-foreground" />
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </ScrollArea>
        )}
      </CardContent>
    </Card>
  );
}
```

**Step 2: Update barrel export**

Update `frontend/src/components/sam-gov/index.ts`:

```typescript
export { SyncStatus } from './SyncStatus';
export { EntityVerification } from './EntityVerification';
export { AmendmentHistory } from './AmendmentHistory';
```

**Step 3: Commit**

```bash
git add frontend/src/components/sam-gov/
git commit -m "feat(frontend): add amendment history component for opportunity tracking"
```

---

## Task 12: Add SAM_GOV_API_KEY to Configuration

**Files:**
- Modify: `api/app/core/config.py`
- Modify: `.env.example`

**Step 1: Add configuration**

Add to `api/app/core/config.py` in the Settings class:

```python
    # SAM.gov Integration
    SAM_GOV_API_KEY: str | None = None
    SAM_GOV_SYNC_INTERVAL_MINUTES: int = 15
    SAM_GOV_DEFAULT_DAYS_BACK: int = 7
```

**Step 2: Update .env.example**

Add to `.env.example`:

```bash
# SAM.gov Integration
SAM_GOV_API_KEY=your_sam_gov_api_key_here
SAM_GOV_SYNC_INTERVAL_MINUTES=15
SAM_GOV_DEFAULT_DAYS_BACK=7
```

**Step 3: Commit**

```bash
git add api/app/core/config.py .env.example
git commit -m "feat(config): add SAM.gov configuration settings"
```

---

## Task 13: Final Integration Test

**Files:**
- Create: `tests/integration/test_sam_gov_integration.py`

**Step 1: Create integration test**

Create `tests/integration/test_sam_gov_integration.py`:

```python
"""Integration tests for SAM.gov deep integration."""
import pytest
import os
from unittest.mock import patch, MagicMock

from src.agents.sam_gov_client import SAMGovClient
from api.app.services.sam_gov_sync import SAMGovSyncService


@pytest.mark.skipif(
    not os.environ.get("SAM_GOV_API_KEY"),
    reason="SAM_GOV_API_KEY not configured"
)
class TestSAMGovIntegration:
    """Integration tests requiring real SAM.gov API key."""

    @pytest.fixture
    def client(self):
        return SAMGovClient(api_key=os.environ["SAM_GOV_API_KEY"])

    def test_search_opportunities_live(self, client):
        """Test live search against SAM.gov."""
        results = client.search_opportunities(days_back=1, limit=5)

        assert isinstance(results, list)
        # May be empty if no recent opportunities
        if results:
            assert "title" in results[0]
            assert "solicitation_number" in results[0]

    def test_entity_verification_live(self, client):
        """Test live entity verification."""
        # Test with a known UEI (GSA's UEI)
        result = client.verify_entity_registration(
            legal_name="General Services Administration"
        )

        assert "is_registered" in result


class TestSAMGovMocked:
    """Unit tests with mocked API responses."""

    @patch("src.agents.sam_gov_client.requests.get")
    def test_full_workflow(self, mock_get):
        """Test complete sync workflow with mocked responses."""
        # Mock search response
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "opportunitiesData": [
                {
                    "noticeId": "test123",
                    "title": "Test Opportunity",
                    "solicitationNumber": "SOL-TEST-001",
                    "postedDate": "2025-01-15",
                }
            ],
            "totalRecords": 1
        }

        client = SAMGovClient(api_key="test_key")
        results = client.search_opportunities(days_back=7, limit=10)

        assert len(results) == 1
        assert results[0]["title"] == "Test Opportunity"
```

**Step 2: Run integration tests**

```bash
# Run mocked tests
PYTHONPATH=. python -m pytest tests/integration/test_sam_gov_integration.py::TestSAMGovMocked -v

# Run live tests (requires API key)
SAM_GOV_API_KEY=your_key PYTHONPATH=. python -m pytest tests/integration/test_sam_gov_integration.py::TestSAMGovIntegration -v
```

**Step 3: Commit**

```bash
git add tests/integration/test_sam_gov_integration.py
git commit -m "test(sam-gov): add integration tests for SAM.gov deep integration"
```

---

## Summary

This plan implements comprehensive SAM.gov integration with:

1. **Extended SAMGovClient** - Full opportunity details, entity verification, amendment tracking
2. **SAMGovSyncService** - Background sync with update detection
3. **API Routes** - Complete REST API for SAM.gov operations
4. **Celery Tasks** - Periodic sync (every 15 minutes) and update checks
5. **Frontend Components** - Sync status, entity verification, amendment history
6. **Configuration** - Environment variables for API keys and sync settings

**Total Tasks:** 13
**Estimated Implementation Time:** Follow TDD for each task

---

## Execution Choice

Plan complete and saved to `docs/plans/2025-12-05-sam-gov-deep-integration.md`. Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
