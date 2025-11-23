import os
from typing import List, Dict, Any
from src.agents.plugins.base_plugin import DataSourcePlugin
from src.agents.sam_gov_client import SAMGovClient

class SAMGovPlugin(DataSourcePlugin):
    """Plugin for fetching opportunities from SAM.gov."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("SAM_GOV_API_KEY")
        self.client = SAMGovClient(api_key=self.api_key)

    @property
    def name(self) -> str:
        return "SAM.gov"

    def search(self, days_back: int = 30, limit: int = 50, **kwargs) -> List[Dict[str, Any]]:
        if not self.api_key:
            print("SAM.gov Plugin: No API key found.")
            return []
        
        return self.client.search_opportunities(days_back=days_back, limit=limit)
