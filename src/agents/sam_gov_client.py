import os
import requests
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class SAMGovClient:
    """Client for interacting with the SAM.gov APIs (Opportunities and Entity Management)."""

    OPP_BASE_URL = "https://api.sam.gov/opportunities/v2/search"
    ENTITY_BASE_URL = "https://api.sam.gov/entity-information/v3/entities"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the SAM.gov client.
        
        Args:
            api_key: SAM.gov API key. If not provided, tries to read from SAM_GOV_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("SAM_GOV_API_KEY")
        if not self.api_key:
            logger.warning("SAM.gov API key not provided. API calls will fail.")

    def search_entities(self, naics_code: Optional[str] = None, keywords: Optional[str] = None, limit: int = 10) -> List[Dict]:
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

    def _map_entity_results(self, entities: List[Dict]) -> List[Dict]:
        """Map SAM.gov Entity API response to internal TeamingPartner schema."""
        mapped = []
        for ent in entities:
            try:
                core_data = ent.get("coreData", {})
                assertions = ent.get("assertions", {})
                reps_certs = ent.get("repsAndCerts", {})
                
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

    def search_opportunities(self, days_back: int = 30, limit: int = 10) -> List[Dict]:
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

    def _map_results(self, opportunities: List[Dict]) -> List[Dict]:
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
