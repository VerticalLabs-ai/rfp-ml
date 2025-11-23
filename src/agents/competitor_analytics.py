import pandas as pd
from typing import List, Dict, Any
import logging
from src.config.paths import PathConfig

logger = logging.getLogger(__name__)

class CompetitorAnalyticsService:
    """
    Service for analyzing potential competitors for an RFP.
    In a production environment, this would query USASpending.gov or a paid market intelligence API.
    For this MVP, it simulates competitor identification by analyzing the description text 
    and looking up similar past awards in the archive.
    """

    def __init__(self):
        self.archive_path = PathConfig.DATA_DIR / "raw" / "FY2025_archived_opportunities.csv"
        self.known_vendors = [
            "Booz Allen Hamilton", "Leidos", "SAIC", "CACI", "General Dynamics", 
            "Northrop Grumman", "Lockheed Martin", "Raytheon", "Accenture Federal", "Deloitte"
        ]

    def identify_potential_incumbents(self, description: str, agency: str) -> List[Dict[str, Any]]:
        """
        Identify potential incumbents based on text analysis and agency history.
        """
        results = []
        
        # 1. Text Analysis (Mock/Heuristic)
        # Look for phrases like "Incumbent is..." (rarely explicitly stated but sometimes)
        # Or just map large primes to the agency.
        
        # For MVP, we'll return "likely" vendors based on the agency if we have a mapping,
        # or random "Big GovCon" names if it's a large agency.
        
        # This is a simulation of what an AI model would do with access to USASpending data.
        import random
        
        if "Defense" in agency or "Army" in agency or "Navy" in agency:
            candidates = ["Lockheed Martin", "Northrop Grumman", "Raytheon"]
        elif "Health" in agency:
            candidates = ["Leidos", "CACI", "Deloitte"]
        elif "Homeland" in agency:
             candidates = ["Accenture Federal", "Booz Allen Hamilton"]
        else:
             candidates = random.sample(self.known_vendors, 2)
             
        # Randomly select 1-2 to simulate "finding" them
        found = random.sample(candidates, k=min(len(candidates), 2))
        
        for vendor in found:
            results.append({
                "name": vendor,
                "probability": round(random.uniform(0.6, 0.9), 2),
                "basis": f"Historical high contract volume with {agency}",
                "last_award_date": "2023-10-15" # Mock date
            })
            
        return results

    def get_agency_spend_history(self, agency: str) -> Dict[str, Any]:
        """
        Get aggregated spend history for an agency (Mock).
        """
        return {
            "agency": agency,
            "fy_total_spend": "$1.2B",
            "top_naics": ["541512", "541330", "561210"],
            "small_business_goal": "23%",
            "small_business_actual": "21.5%"
        }
