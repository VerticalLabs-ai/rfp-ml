"""
Predictions API with timeout handling and background processing.

Provides:
- Fast initial response with cached/statistical predictions
- Background AI enhancement via Celery
- Proper timeout handling (max 60 seconds)
- Redis caching for performance
"""

import asyncio
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel

from src.config.paths import PathConfig

logger = logging.getLogger(__name__)
router = APIRouter()

# Cache configuration
_cached_predictions: list[dict] | None = None
_cache_timestamp: float = 0
_CACHE_TTL = 3600  # 1 hour cache
_generation_in_progress = False
_last_error: str | None = None

# Redis cache keys
REDIS_PREDICTIONS_KEY = "rfp:predictions:latest"
REDIS_PREDICTIONS_META_KEY = "rfp:predictions:meta"

# File-based cache (persists across container restarts)
CACHE_FILE = PathConfig.DATA_DIR / "cache" / "predictions_cache.json"


def get_cached_predictions_from_file() -> tuple[list[dict] | None, dict | None]:
    """Get cached predictions from file."""
    try:
        if CACHE_FILE.exists():
            with open(CACHE_FILE, 'r') as f:
                data = json.load(f)
                return data.get('predictions'), data.get('meta')
    except Exception as e:
        logger.warning(f"File cache read failed: {e}")
    return None, None


def cache_predictions_to_file(predictions: list[dict], meta: dict):
    """Cache predictions to file."""
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, 'w') as f:
            json.dump({'predictions': predictions, 'meta': meta}, f)
        logger.info(f"Cached {len(predictions)} predictions to file")
    except Exception as e:
        logger.warning(f"File cache write failed: {e}")


class PredictionStatus(BaseModel):
    """Status response for prediction generation."""
    status: str
    predictions_count: int = 0
    ai_enhanced_count: int = 0
    cached: bool = False
    cache_age_seconds: int | None = None
    generating: bool = False
    error: str | None = None


def get_redis_client():
    """Get Redis client for caching."""
    try:
        import redis
        import os
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        return redis.from_url(redis_url, decode_responses=True)
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}")
        return None


def get_cached_predictions_from_redis() -> tuple[list[dict] | None, dict | None]:
    """Get cached predictions from Redis."""
    client = get_redis_client()
    if not client:
        return None, None

    try:
        predictions_json = client.get(REDIS_PREDICTIONS_KEY)
        meta_json = client.get(REDIS_PREDICTIONS_META_KEY)

        if predictions_json:
            predictions = json.loads(predictions_json)
            meta = json.loads(meta_json) if meta_json else {}
            return predictions, meta
    except Exception as e:
        logger.warning(f"Redis read failed: {e}")

    return None, None


def cache_predictions_to_redis(predictions: list[dict], meta: dict):
    """Cache predictions to Redis."""
    client = get_redis_client()
    if not client:
        return

    try:
        client.setex(REDIS_PREDICTIONS_KEY, _CACHE_TTL, json.dumps(predictions))
        client.setex(REDIS_PREDICTIONS_META_KEY, _CACHE_TTL, json.dumps(meta))
    except Exception as e:
        logger.warning(f"Redis write failed: {e}")


def get_forecasting_service():
    """Lazy load forecasting service."""
    from src.agents.forecasting_service import ForecastingService
    return ForecastingService()


def find_data_file() -> Path | None:
    """Find available historical data file."""
    data_file = PathConfig.DATA_DIR / "raw" / "FY2025_archived_opportunities.csv"
    if data_file.exists():
        return data_file

    data_file = PathConfig.DATA_DIR / "raw" / "FY2023_archived_opportunities.csv"
    if data_file.exists():
        return data_file

    return None


async def generate_predictions_with_timeout(
    confidence_threshold: float,
    use_ai: bool,
    timeout_seconds: float = 55.0
) -> tuple[list[dict], dict]:
    """
    Generate predictions with timeout protection.

    Returns (predictions, metadata) tuple.
    """
    global _generation_in_progress, _cached_predictions, _cache_timestamp, _last_error

    data_file = find_data_file()
    if not data_file:
        raise HTTPException(status_code=404, detail="Historical data not found for forecasting")

    _generation_in_progress = True
    _last_error = None
    start_time = time.time()

    try:
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()

        service = get_forecasting_service()

        # Phase 1: Load data (should be fast)
        df = await asyncio.wait_for(
            loop.run_in_executor(None, service.train_on_file, str(data_file)),
            timeout=10.0
        )

        if df.empty:
            raise HTTPException(status_code=500, detail="Failed to load historical data")

        # Phase 2: Statistical predictions (typically 5-15 seconds)
        elapsed = time.time() - start_time
        remaining = timeout_seconds - elapsed - 5  # Reserve 5s for cleanup

        predictions = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: service.predict_upcoming_opportunities(
                    df,
                    confidence_threshold=0.15,  # Get more, filter later
                    use_ai_insights=False  # Statistical only first
                )
            ),
            timeout=min(remaining, 30.0)
        )

        # Phase 3: AI insights if requested and time permits
        ai_enhanced_count = 0
        elapsed = time.time() - start_time
        remaining = timeout_seconds - elapsed - 2

        if use_ai and predictions and remaining > 10:
            try:
                enhanced = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        service._generate_ai_insight,
                        predictions[:15]  # Only top 15 to save time
                    ),
                    timeout=min(remaining, 25.0)
                )
                predictions = enhanced
                ai_enhanced_count = sum(1 for p in predictions if p.get('ai_enhanced'))
            except asyncio.TimeoutError:
                logger.warning("AI insight generation timed out, returning statistical predictions")
            except Exception as e:
                logger.warning(f"AI insight generation failed: {e}")

        # Update in-memory cache
        _cached_predictions = predictions
        _cache_timestamp = time.time()

        meta = {
            "count": len(predictions),
            "ai_enhanced_count": ai_enhanced_count,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": round(time.time() - start_time, 2),
        }

        # Cache to file (persistent) and Redis (if available)
        cache_predictions_to_file(predictions, meta)
        cache_predictions_to_redis(predictions, meta)

        return predictions, meta

    except asyncio.TimeoutError:
        _last_error = "Prediction generation timed out"
        logger.error("Prediction generation timed out")
        raise HTTPException(status_code=504, detail="Prediction generation timed out")
    except HTTPException:
        raise
    except Exception as e:
        _last_error = str(e)
        logger.exception("Prediction generation failed")
        raise HTTPException(status_code=500, detail=str(e)) from e
    finally:
        _generation_in_progress = False


@router.get("/upcoming", response_model=list[dict[str, Any]])
async def get_upcoming_predictions(
    confidence: float = Query(default=0.3, ge=0.0, le=1.0),
    refresh: bool = Query(default=False, description="Force refresh cache"),
    use_ai: bool = Query(default=True, description="Generate AI insights"),
    timeout: float = Query(default=55.0, ge=5.0, le=60.0, description="Request timeout in seconds")
):
    """
    Get predicted upcoming RFP opportunities using AI-powered analysis.

    Features:
    - 60-second timeout protection
    - Cached results for fast subsequent loads
    - Statistical predictions with optional AI enhancement
    - Graceful fallback to cached data on timeout

    Returns predictions with:
    - Statistical confidence based on historical variance
    - Cycle detection (quarterly, biannual, annual, etc.)
    - AI-generated insights for top predictions (if use_ai=true)
    """
    global _cached_predictions, _cache_timestamp

    # Check memory cache first
    cache_age = time.time() - _cache_timestamp if _cache_timestamp else None
    cache_valid = (
        _cached_predictions is not None
        and not refresh
        and cache_age is not None
        and cache_age < _CACHE_TTL
    )

    if cache_valid:
        filtered = [p for p in _cached_predictions if p["confidence"] >= confidence]
        logger.info(f"Returning {len(filtered)} cached predictions (age: {int(cache_age)}s)")
        return filtered

    # Check file cache first (most reliable), then Redis
    if not refresh:
        # Try file cache first (persists across restarts)
        file_predictions, file_meta = get_cached_predictions_from_file()
        if file_predictions:
            _cached_predictions = file_predictions
            _cache_timestamp = time.time()
            filtered = [p for p in file_predictions if p["confidence"] >= confidence]
            logger.info(f"Returning {len(filtered)} file-cached predictions")
            return filtered

        # Fallback to Redis cache
        redis_predictions, redis_meta = get_cached_predictions_from_redis()
        if redis_predictions:
            _cached_predictions = redis_predictions
            _cache_timestamp = time.time()
            filtered = [p for p in redis_predictions if p["confidence"] >= confidence]
            logger.info(f"Returning {len(filtered)} Redis-cached predictions")
            return filtered

    # Generate new predictions with timeout
    try:
        predictions, meta = await generate_predictions_with_timeout(
            confidence_threshold=confidence,
            use_ai=use_ai,
            timeout_seconds=timeout
        )

        filtered = [p for p in predictions if p["confidence"] >= confidence]
        logger.info(f"Generated {len(filtered)} predictions ({meta.get('ai_enhanced_count', 0)} AI-enhanced)")
        return filtered

    except HTTPException as e:
        # On timeout/error, try to return cached data if available
        if _cached_predictions:
            logger.warning(f"Generation failed ({e.detail}), returning stale cache")
            filtered = [p for p in _cached_predictions if p["confidence"] >= confidence]
            return filtered

        # Check Redis as last resort
        redis_predictions, _ = get_cached_predictions_from_redis()
        if redis_predictions:
            logger.warning(f"Generation failed ({e.detail}), returning Redis cache")
            filtered = [p for p in redis_predictions if p["confidence"] >= confidence]
            return filtered

        raise


@router.get("/status")
async def get_prediction_status() -> PredictionStatus:
    """Get the current status of prediction generation and cache."""
    cache_age = int(time.time() - _cache_timestamp) if _cache_timestamp else None

    # Check for cached predictions
    if _cached_predictions:
        ai_count = sum(1 for p in _cached_predictions if p.get('ai_enhanced'))
        return PredictionStatus(
            status="ready",
            predictions_count=len(_cached_predictions),
            ai_enhanced_count=ai_count,
            cached=True,
            cache_age_seconds=cache_age,
            generating=_generation_in_progress,
        )

    # Check Redis
    redis_predictions, redis_meta = get_cached_predictions_from_redis()
    if redis_predictions:
        return PredictionStatus(
            status="ready",
            predictions_count=len(redis_predictions),
            ai_enhanced_count=redis_meta.get("ai_enhanced_count", 0) if redis_meta else 0,
            cached=True,
            cache_age_seconds=None,  # Unknown for Redis
            generating=_generation_in_progress,
        )

    # No cache available
    return PredictionStatus(
        status="no_cache",
        generating=_generation_in_progress,
        error=_last_error,
    )


@router.post("/generate")
async def trigger_prediction_generation(
    background_tasks: BackgroundTasks,
    use_ai: bool = Query(default=True),
):
    """
    Trigger background prediction generation.

    Returns immediately with job info, predictions generated asynchronously.
    """
    global _generation_in_progress

    if _generation_in_progress:
        return {
            "status": "already_running",
            "message": "Prediction generation is already in progress"
        }

    # Check if Celery is available
    try:
        from api.app.worker.tasks.predictions import generate_predictions

        # Dispatch to Celery
        task = generate_predictions.delay(
            confidence_threshold=0.15,
            use_ai=use_ai,
        )

        return {
            "status": "started",
            "job_id": task.id,
            "message": "Prediction generation started in background"
        }
    except Exception as e:
        logger.warning(f"Celery dispatch failed, running inline: {e}")

        # Fallback: run in background task
        async def run_generation():
            try:
                await generate_predictions_with_timeout(0.15, use_ai, 55.0)
            except Exception as ex:
                logger.error(f"Background generation failed: {ex}")

        background_tasks.add_task(run_generation)

        return {
            "status": "started_inline",
            "message": "Prediction generation started (inline mode)"
        }


@router.delete("/cache")
async def clear_predictions_cache():
    """Clear all prediction caches to force a refresh."""
    global _cached_predictions, _cache_timestamp

    _cached_predictions = None
    _cache_timestamp = 0

    # Clear file cache
    try:
        if CACHE_FILE.exists():
            CACHE_FILE.unlink()
            logger.info("File cache cleared")
    except Exception as e:
        logger.warning(f"Failed to clear file cache: {e}")

    # Clear Redis cache too
    client = get_redis_client()
    if client:
        try:
            client.delete(REDIS_PREDICTIONS_KEY)
            client.delete(REDIS_PREDICTIONS_META_KEY)
        except Exception:
            pass

    return {"status": "cache_cleared"}


@router.get("/fallback")
async def get_fallback_predictions(
    confidence: float = Query(default=0.3, ge=0.0, le=1.0),
):
    """
    Get fallback/cached predictions without triggering new generation.

    Useful when main endpoint times out - returns whatever is cached.
    """
    # Check memory cache
    if _cached_predictions:
        filtered = [p for p in _cached_predictions if p["confidence"] >= confidence]
        return {
            "status": "cached",
            "predictions": filtered,
            "count": len(filtered),
            "cache_age_seconds": int(time.time() - _cache_timestamp) if _cache_timestamp else None,
        }

    # Check file cache
    file_predictions, file_meta = get_cached_predictions_from_file()
    if file_predictions:
        filtered = [p for p in file_predictions if p["confidence"] >= confidence]
        return {
            "status": "file_cached",
            "predictions": filtered,
            "count": len(filtered),
            "generated_at": file_meta.get("generated_at") if file_meta else None,
        }

    # Check Redis
    redis_predictions, redis_meta = get_cached_predictions_from_redis()
    if redis_predictions:
        filtered = [p for p in redis_predictions if p["confidence"] >= confidence]
        return {
            "status": "redis_cached",
            "predictions": filtered,
            "count": len(filtered),
            "generated_at": redis_meta.get("generated_at") if redis_meta else None,
        }

    # No cached data
    return {
        "status": "no_data",
        "predictions": [],
        "count": 0,
        "message": "No cached predictions available. Trigger generation with POST /generate endpoint.",
    }
