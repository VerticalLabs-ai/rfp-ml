"""
Prediction generation tasks for Celery.

Handles long-running forecasting tasks:
- AI-powered opportunity predictions
- Historical data analysis
"""

import asyncio
import logging
import os
import sys
import time
from datetime import datetime, timezone

from celery import shared_task

# Add project paths
project_root = os.path.dirname(
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    )
)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

logger = logging.getLogger(__name__)


def broadcast_progress(job_id: str, progress: int, status: str, **kwargs):
    """Broadcast job progress via WebSocket (async wrapper)."""
    try:
        from api.app.websockets.channels import broadcast_job_progress

        asyncio.run(broadcast_job_progress(job_id, progress, status, **kwargs))
    except Exception as e:
        logger.warning(f"Failed to broadcast progress: {e}")


@shared_task(
    bind=True,
    name="api.app.worker.tasks.predictions.generate_predictions",
    soft_time_limit=55,  # 55 seconds soft limit
    time_limit=60,  # 60 seconds hard limit
)
def generate_predictions(
    self,
    confidence_threshold: float = 0.15,
    use_ai: bool = True,
    data_file_path: str | None = None
) -> dict:
    """
    Generate predictions using AI-powered forecasting.

    Args:
        confidence_threshold: Minimum confidence for predictions
        use_ai: Whether to use AI for insights (slower but richer)
        data_file_path: Path to historical data file

    Returns:
        Dict with predictions and metadata
    """
    job_id = self.request.id
    start_time = time.time()

    logger.info(f"Starting prediction generation - Job: {job_id}")

    try:
        self.update_state(state="PROGRESS", meta={"progress": 0, "status": "starting"})
        broadcast_progress(job_id, 0, "starting")

        from src.agents.forecasting_service import ForecastingService
        from src.config.paths import PathConfig

        # Find data file
        if data_file_path:
            from pathlib import Path
            data_file = Path(data_file_path)
        else:
            data_file = PathConfig.DATA_DIR / "raw" / "FY2025_archived_opportunities.csv"
            if not data_file.exists():
                data_file = PathConfig.DATA_DIR / "raw" / "FY2023_archived_opportunities.csv"

        if not data_file.exists():
            return {
                "status": "error",
                "error": "Historical data not found for forecasting",
                "predictions": [],
            }

        self.update_state(state="PROGRESS", meta={"progress": 10, "status": "loading_data"})
        broadcast_progress(job_id, 10, "loading_data")

        service = ForecastingService()

        # Load and prepare data (typically fast)
        df = service.train_on_file(str(data_file))

        if df.empty:
            return {
                "status": "error",
                "error": "Failed to load historical data",
                "predictions": [],
            }

        self.update_state(state="PROGRESS", meta={"progress": 30, "status": "analyzing_patterns"})
        broadcast_progress(job_id, 30, "analyzing_patterns")

        # Generate predictions - this is the main computation
        # First pass: statistical analysis only (fast)
        predictions = service.predict_upcoming_opportunities(
            df,
            confidence_threshold=confidence_threshold,
            use_ai_insights=False  # Do statistical first
        )

        self.update_state(state="PROGRESS", meta={"progress": 60, "status": "predictions_ready"})
        broadcast_progress(job_id, 60, "predictions_ready", count=len(predictions))

        # Second pass: Add AI insights if requested and we have time
        elapsed = time.time() - start_time
        remaining_time = 50 - elapsed  # Reserve time for completion

        if use_ai and predictions and remaining_time > 10:
            self.update_state(state="PROGRESS", meta={"progress": 70, "status": "generating_insights"})
            broadcast_progress(job_id, 70, "generating_insights")

            try:
                # Only enhance top predictions to save time
                predictions = service._generate_ai_insight(predictions[:15])
            except Exception as e:
                logger.warning(f"AI insight generation failed (continuing without): {e}")
                # Continue with predictions without AI insights

        self.update_state(state="PROGRESS", meta={"progress": 90, "status": "completing"})
        broadcast_progress(job_id, 90, "completing")

        ai_enhanced = sum(1 for p in predictions if p.get('ai_enhanced'))
        elapsed = time.time() - start_time

        self.update_state(state="PROGRESS", meta={"progress": 100, "status": "completed"})
        broadcast_progress(job_id, 100, "completed")

        return {
            "status": "success",
            "predictions": predictions,
            "count": len(predictions),
            "ai_enhanced_count": ai_enhanced,
            "elapsed_seconds": round(elapsed, 2),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Prediction generation failed: {e}")
        broadcast_progress(job_id, 0, "failed", error=str(e))
        return {
            "status": "error",
            "error": str(e),
            "predictions": [],
        }


@shared_task(
    bind=True,
    name="api.app.worker.tasks.predictions.generate_predictions_fast",
    soft_time_limit=25,
    time_limit=30,
)
def generate_predictions_fast(
    self,
    confidence_threshold: float = 0.15,
    data_file_path: str | None = None
) -> dict:
    """
    Generate predictions without AI insights (faster).

    Used for initial page load while full analysis runs in background.
    """
    job_id = self.request.id
    start_time = time.time()

    logger.info(f"Starting fast prediction generation - Job: {job_id}")

    try:
        from src.agents.forecasting_service import ForecastingService
        from src.config.paths import PathConfig

        # Find data file
        if data_file_path:
            from pathlib import Path
            data_file = Path(data_file_path)
        else:
            data_file = PathConfig.DATA_DIR / "raw" / "FY2025_archived_opportunities.csv"
            if not data_file.exists():
                data_file = PathConfig.DATA_DIR / "raw" / "FY2023_archived_opportunities.csv"

        if not data_file.exists():
            return {
                "status": "error",
                "error": "Historical data not found",
                "predictions": [],
            }

        service = ForecastingService()
        df = service.train_on_file(str(data_file))

        if df.empty:
            return {
                "status": "error",
                "error": "Failed to load data",
                "predictions": [],
            }

        # Statistical analysis only (no AI)
        predictions = service.predict_upcoming_opportunities(
            df,
            confidence_threshold=confidence_threshold,
            use_ai_insights=False
        )

        elapsed = time.time() - start_time

        return {
            "status": "success",
            "predictions": predictions,
            "count": len(predictions),
            "ai_enhanced_count": 0,
            "elapsed_seconds": round(elapsed, 2),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "is_partial": True,  # Indicates AI insights not included
        }

    except Exception as e:
        logger.error(f"Fast prediction generation failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "predictions": [],
        }
