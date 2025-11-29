import json
from typing import Any

from sqlalchemy.orm import Session

from api.app.models.database import RFPOpportunity
from src.agents.sam_gov_client import SAMGovClient
from src.config.llm_config import get_llm_client


class TeamingPartnerService:
    """
    Service to identify potential teaming partners using live SAM.gov API data.
    """

    def __init__(self, db: Session):
        self.db = db
        self.sam_client = SAMGovClient()
        self.llm_client = get_llm_client("teaming_analysis")

    def find_partners(self, rfp_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """
        Find matches based on NAICS codes and keywords using live API.
        """
        rfp = self.db.query(RFPOpportunity).filter(RFPOpportunity.rfp_id == rfp_id).first()
        if not rfp:
            return []

        # Extract NAICS
        # RFP might have multiple or just one. We'll try the primary one.
        rfp_naics = rfp.naics_code
        if rfp_naics and len(rfp_naics) > 6:
             # If it's a list or long string, take the first 6 digits
             rfp_naics = rfp_naics[:6]

        # Extract keywords for secondary scoring
        keywords = self._extract_keywords(rfp.description or "")
        keyword_query = " ".join(keywords[:3]) # Pass top 3 keywords to API if supported

        # Live API Search
        # Note: searching by NAICS is the most reliable filter on SAM.gov
        api_results = self.sam_client.search_entities(
            naics_code=rfp_naics,
            keywords=keyword_query,
            limit=limit * 2 # Fetch more to filter/score
        )

        matches = []
        for entity in api_results:
            score = 50 # Base score for being returned by API
            match_reasons = ["Live SAM.gov Result"]

            # Bonus scoring
            if rfp_naics and rfp_naics in entity.get("capabilities", ""):
                score += 20
                match_reasons.append(f"Matched NAICS {rfp_naics}")

            # Simple keyword check in name (since API result is brief)
            ent_name = entity.get("name", "").lower()
            for kw in keywords:
                if kw in ent_name:
                    score += 5

            matches.append({
                "uei": entity.get("uei"),
                "name": entity.get("name"),
                "score": min(score, 100),
                "match_reason": ", ".join(match_reasons),
                "business_types": json.dumps(entity.get("business_types", [])),
                "capabilities": entity.get("capabilities", ""),
                "poc_email": entity.get("poc_email"),
                "website": entity.get("website")
            })

        # Sort by score
        matches.sort(key=lambda x: x["score"], reverse=True)

        return matches[:limit]

    def _extract_keywords(self, text: str) -> list[str]:
        """Simple keyword extractor (mock)."""
        # In reality, use NLP or LLM
        common_stops = {"the", "and", "of", "for", "in", "to", "a", "services", "support", "contract", "requirements"}
        words = text.lower().replace(".", "").replace(",", "").split()
        keywords = [w for w in words if len(w) > 4 and w not in common_stops]
        return list(set(keywords))[:10] # Top 10 unique long words

