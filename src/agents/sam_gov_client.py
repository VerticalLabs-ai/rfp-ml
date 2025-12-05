import logging
import os
from datetime import datetime, timedelta

import requests

logger = logging.getLogger(__name__)

class SAMGovClient:
    """Client for interacting with the SAM.gov APIs (Opportunities and Entity Management)."""

    OPP_BASE_URL = "https://api.sam.gov/opportunities/v2/search"
    ENTITY_BASE_URL = "https://api.sam.gov/entity-information/v3/entities"

    @property
    def opportunities_base_url(self):
        """Base URL for opportunities API."""
        return "https://api.sam.gov/opportunities/v2"

    @property
    def entity_base_url(self):
        """Base URL for entity management API."""
        return self.ENTITY_BASE_URL

    def __init__(self, api_key: str | None = None):
        """
        Initialize the SAM.gov client.

        Args:
            api_key: SAM.gov API key. If not provided, tries to read from SAM_GOV_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("SAM_GOV_API_KEY")
        if not self.api_key:
            logger.warning("SAM.gov API key not provided. API calls will fail.")

    def search_entities(self, naics_code: str | None = None, keywords: str | None = None, limit: int = 10) -> list[dict]:
        """
        Search for entities in SAM.gov using the Entity Management API.

        Args:
            naics_code: 6-digit NAICS code to filter by.
            keywords: Keywords to search in legal business name or other fields (if supported).
            limit: Maximum number of results to return.

        Returns:
            List of entity dictionaries.
        """
        if not self.api_key:
            logger.error("Cannot search entities: No API key.")
            return []

        # Construct parameters
        # Note: The actual SAM.gov Entity API parameters might vary (e.g. 'q', 'legalBusinessName', 'naicsCode')
        # Based on documentation, we use 'naicsCode' and 'q' (for general search) or specific fields.
        # We'll attempt to use 'naicsCode' as a primary filter.

        params = {
            "api_key": self.api_key,
            "limit": limit,
            "samExtractCode": 1, # 1 for Active, 2 for Inactive, 3 for All (usually) - verifying exact param needed
            "registrationStatus": "A" # Active
        }

        if naics_code:
            params["naicsCode"] = naics_code

        if keywords:
            params["q"] = keywords # General query parameter if supported, else we filter client-side

        try:
            logger.info(f"Searching SAM.gov entities (NAICS={naics_code}, Keywords={keywords})...")
            response = requests.get(self.ENTITY_BASE_URL, params=params, timeout=30)

            if response.status_code == 404:
                 logger.warning("SAM.gov Entity API endpoint not found (404). Check URL version.")
                 return []
            if response.status_code == 403:
                 logger.error("SAM.gov Entity API access denied (403). Check API Key permissions.")
                 return []

            response.raise_for_status()
            data = response.json()

            entities = data.get("entityData", [])
            logger.info(f"Found {len(entities)} entities.")
            return self._map_entity_results(entities)

        except Exception as e:
            logger.error(f"Error searching SAM.gov entities: {e}")
            return []

    def _map_entity_results(self, entities: list[dict]) -> list[dict]:
        """Map SAM.gov Entity API response to internal TeamingPartner schema."""
        mapped = []
        for ent in entities:
            try:
                core_data = ent.get("coreData", {})
                assertions = ent.get("assertions", {})
                _reps_certs = ent.get("repsAndCerts", {})

                # Extract fields
                uei = core_data.get("ueiSAM", "")
                legal_name = core_data.get("legalBusinessName", "Unknown")

                # Business Types (Certs)
                biz_types = core_data.get("businessTypes", {})
                certs = []
                if biz_types:
                    # Flatten the complexity of business types structure
                    # This is a simplification; actual structure is complex
                    if isinstance(biz_types, list):
                        certs = [bt.get("businessTypeDescription") for bt in biz_types if bt.get("businessTypeDescription")]

                # NAICS
                naics_list = []
                goods_services = assertions.get("goodsAndServices", {})
                if goods_services:
                    naics_data = goods_services.get("naicsList", [])
                    for n in naics_data:
                         naics_list.append(n.get("naicsCode"))

                mapped.append({
                    "uei": uei,
                    "name": legal_name,
                    "business_types": certs,
                    "capabilities": f"NAICS: {', '.join(naics_list[:5])}...", # Narrative often not in basic response
                    "poc_email": "", # Often restricted in public API
                    "website": "", # Often not provided directly in summary
                    "source": "sam.gov_live"
                })
            except Exception as e:
                logger.warning(f"Error mapping entity: {e}")
                continue
        return mapped

    def search_opportunities(self, days_back: int = 30, limit: int = 10) -> list[dict]:
        """
        Search for active opportunities posted in the last N days.
        """
        if not self.api_key:
            logger.error("Cannot search opportunities: No API key.")
            return []

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        # Format dates as MM/DD/YYYY
        posted_from = start_date.strftime("%m/%d/%Y")
        posted_to = end_date.strftime("%m/%d/%Y")

        params = {
            "api_key": self.api_key,
            "postedFrom": posted_from,
            "postedTo": posted_to,
            "limit": limit,
            "active": "yes",
            "ptype": "o,k" # o=Solicitation, k=Combined Synopsis/Solicitation
        }

        try:
            logger.info(f"Fetching opportunities from SAM.gov (last {days_back} days)...")
            response = requests.get(self.OPP_BASE_URL, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            opportunities = data.get("opportunitiesData", [])

            logger.info(f"Found {len(opportunities)} opportunities.")
            return self._map_results(opportunities)

        except requests.exceptions.RequestException as e:
            logger.error(f"SAM.gov API request failed: {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response content: {e.response.text}")
            return []
        except Exception as e:
            logger.error(f"Error processing SAM.gov response: {e}")
            return []

    def _map_results(self, opportunities: list[dict]) -> list[dict]:
        """Map SAM.gov API response format to internal schema."""
        mapped_results = []

        for opp in opportunities:
            try:
                # Extract fields safely
                solicitation_number = opp.get("solicitationNumber", "")
                title = opp.get("title", "Untitled")
                agency = opp.get("department", {}).get("name", "Unknown Agency")
                office = opp.get("office", {}).get("name", "")
                posted_date = opp.get("postedDate", "")
                response_deadline = opp.get("responseDeadLine", "")
                description = opp.get("description", "")

                # Try to find award amount (often not in search results, but maybe in description or extra fields)
                # For now, default to 0.0 as it's often not structured in search results
                award_amount = 0.0

                # Construct URL
                opp_id = opp.get("noticeId", "")
                url = f"https://sam.gov/opp/{opp_id}/view" if opp_id else ""

                mapped_opp = {
                    "rfp_id": solicitation_number or f"SAM-{opp_id}",
                    "solicitation_number": solicitation_number,
                    "title": title,
                    "agency": agency,
                    "office": office,
                    "posted_date": posted_date,
                    "response_deadline": response_deadline,
                    "description": description,
                    "award_amount": award_amount,
                    "url": url,
                    "source": "sam.gov_api"
                }
                mapped_results.append(mapped_opp)

            except Exception as e:
                logger.warning(f"Error mapping opportunity: {e}")
                continue

        return mapped_results

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
