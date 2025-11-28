from abc import ABC, abstractmethod
from typing import List, Dict, Any
import pandas as pd

class DataSourcePlugin(ABC):
    """Abstract base class for RFP data source plugins."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the unique name of this data source."""
        pass

    @abstractmethod
    def search(self, days_back: int = 30, limit: int = 50, **kwargs) -> List[Dict[str, Any]]:
        """
        Search for opportunities from this source.
        
        Args:
            days_back: Number of days to look back for opportunities.
            limit: Maximum number of results to return.
            **kwargs: Additional source-specific arguments.
            
        Returns:
            List of dictionaries representing opportunities.
        """
        pass

    def normalize(self, raw_data: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Normalize raw data into a standard DataFrame format.
        Can be overridden by plugins if specific normalization is needed beyond standard mapping.
        """
        if not raw_data:
            return pd.DataFrame()
        return pd.DataFrame(raw_data)
