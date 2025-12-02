import logging
import sys
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from src.agents.forecasting_service import ForecastingService
from src.config.paths import PathConfig

# Add project root to path to import src
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.append(str(PROJECT_ROOT))

logger = logging.getLogger(__name__)
router = APIRouter()

# Global service instance (lazy loaded)
_forecasting_service = None
_cached_predictions = None
_cache_timestamp = 0
_CACHE_TTL = 3600  # 1 hour cache


def get_forecasting_service():
    global _forecasting_service
    if _forecasting_service is None:
        _forecasting_service = ForecastingService()
    return _forecasting_service


@router.get("/upcoming", response_model=list[dict[str, Any]])
async def get_upcoming_predictions(
    confidence: float = Query(default=0.3, ge=0.0, le=1.0),
    refresh: bool = Query(default=False, description="Force refresh cache"),
    use_ai: bool = Query(default=True, description="Generate AI insights")
):
    """
    Get predicted upcoming RFP opportunities using AI-powered analysis.

    Returns predictions with:
    - Statistical confidence based on historical variance
    - Cycle detection (quarterly, biannual, annual, etc.)
    - AI-generated insights for top predictions
    """
    global _cached_predictions, _cache_timestamp

    # Check cache validity
    cache_valid = (
        _cached_predictions is not None
        and not refresh
        and (time.time() - _cache_timestamp) < _CACHE_TTL
    )

    if cache_valid:
        filtered = [p for p in _cached_predictions if p["confidence"] >= confidence]
        logger.info(f"Returning {len(filtered)} cached predictions (confidence >= {confidence})")
        return filtered

    service = get_forecasting_service()

    # Path to historical data
    data_file = PathConfig.DATA_DIR / "raw" / "FY2025_archived_opportunities.csv"

    if not data_file.exists():
        data_file = PathConfig.DATA_DIR / "raw" / "FY2023_archived_opportunities.csv"

    if not data_file.exists():
        raise HTTPException(
            status_code=404, detail="Historical data not found for forecasting"
        )

    try:
        logger.info("Running AI-powered forecasting on %s...", data_file)
        df = service.train_on_file(str(data_file))

        if df.empty:
            raise HTTPException(
                status_code=500, detail="Failed to load historical data"
            )

        # Run prediction with AI insights
        predictions = service.predict_upcoming_opportunities(
            df,
            confidence_threshold=0.15,  # Get more predictions, filter later
            use_ai_insights=use_ai
        )

        # Cache results
        _cached_predictions = predictions
        _cache_timestamp = time.time()

        # Log stats
        ai_enhanced = sum(1 for p in predictions if p.get('ai_enhanced'))
        logger.info(
            f"Generated {len(predictions)} predictions "
            f"({ai_enhanced} with AI insights)"
        )

        # Return filtered
        return [p for p in predictions if p["confidence"] >= confidence]

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Forecasting error")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cache")
async def clear_predictions_cache():
    """Clear the predictions cache to force a refresh."""
    global _cached_predictions, _cache_timestamp
    _cached_predictions = None
    _cache_timestamp = 0
    return {"status": "cache_cleared"}
