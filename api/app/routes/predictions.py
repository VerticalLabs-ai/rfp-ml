from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import sys
import os
from pathlib import Path

# Add project root to path to import src
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.append(str(PROJECT_ROOT))

from src.agents.forecasting_service import ForecastingService
from src.config.paths import PathConfig

router = APIRouter()

# Global service instance (lazy loaded)
_forecasting_service = None
_cached_predictions = None

def get_forecasting_service():
    global _forecasting_service
    if _forecasting_service is None:
        _forecasting_service = ForecastingService()
    return _forecasting_service

@router.get("/upcoming", response_model=List[Dict[str, Any]])
async def get_upcoming_predictions(confidence: float = 0.7):
    """
    Get predicted upcoming RFP opportunities based on historical analysis.
    """
    global _cached_predictions
    
    # Return cache if available (simple in-memory cache for MVP)
    if _cached_predictions:
        return [p for p in _cached_predictions if p['confidence'] >= confidence]

    service = get_forecasting_service()
    
    # Path to historical data
    # In Docker, this is /app/.../data/raw/...
    # PathConfig handles the base DATA_DIR
    data_file = PathConfig.DATA_DIR / "raw" / "FY2025_archived_opportunities.csv"
    
    if not data_file.exists():
        # Fallback for testing or if 2025 file missing
        data_file = PathConfig.DATA_DIR / "raw" / "FY2023_archived_opportunities.csv"
        
    if not data_file.exists():
        raise HTTPException(status_code=404, detail="Historical data not found for forecasting")
        
    try:
        print(f"Training forecasting model on {data_file}...")
        df = service.train_on_file(str(data_file))
        
        if df.empty:
             raise HTTPException(status_code=500, detail="Failed to load historical data")
             
        predictions = service.predict_upcoming_opportunities(df, confidence_threshold=0.0) # Get all, filter later
        
        # Cache results
        _cached_predictions = predictions
        
        # Return filtered
        return [p for p in predictions if p['confidence'] >= confidence]
        
    except Exception as e:
        print(f"Forecasting error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
