"""
Background tasks for RFP processing - replaces Celery with FastAPI BackgroundTasks.
"""
import logging
from datetime import datetime
from typing import Any, Dict

logger = logging.getLogger(__name__)

# Task status tracking
task_status: Dict[str, Dict[str, Any]] = {}


async def ingest_documents_task(task_id: str, file_paths: list[str]):
    """
    Background task to ingest documents into the RAG system.
    """
    logger.info(f"[Task {task_id}] Starting ingestion of {len(file_paths)} files")
    task_status[task_id] = {
        "status": "running",
        "started_at": datetime.now().isoformat(),
        "task_type": "ingest_documents",
        "files_processed": 0,
        "total_files": len(file_paths)
    }

    try:
        from src.rag.chroma_rag_engine import get_rag_engine

        rag_engine = get_rag_engine()
        rag_engine.build_index(force_rebuild=True)

        task_status[task_id].update({
            "status": "completed",
            "completed_at": datetime.now().isoformat(),
            "files_processed": len(file_paths),
            "result": {"files_processed": len(file_paths)}
        })
        logger.info(f"[Task {task_id}] Ingestion completed successfully")

    except Exception as e:
        logger.error(f"[Task {task_id}] Ingestion failed: {e}")
        task_status[task_id].update({
            "status": "failed",
            "error": str(e),
            "completed_at": datetime.now().isoformat()
        })


async def generate_bid_task(task_id: str, rfp_data: Dict[str, Any]):
    """
    Background task to generate a full bid.
    """
    logger.info(f"[Task {task_id}] Starting bid generation for RFP: {rfp_data.get('title')}")
    task_status[task_id] = {
        "status": "running",
        "started_at": datetime.now().isoformat(),
        "task_type": "generate_bid",
        "rfp_id": rfp_data.get("rfp_id")
    }

    try:
        from app.services.rfp_processor import processor

        bid_document = await processor.generate_bid_document(rfp_data)

        if "error" in bid_document:
            raise Exception(bid_document["error"])

        task_status[task_id].update({
            "status": "completed",
            "completed_at": datetime.now().isoformat(),
            "result": {
                "bid_id": bid_document.get("bid_id"),
                "rfp_id": rfp_data.get("rfp_id")
            }
        })
        logger.info(f"[Task {task_id}] Bid generation completed: {bid_document.get('bid_id')}")

    except Exception as e:
        logger.error(f"[Task {task_id}] Bid generation failed: {e}")
        task_status[task_id].update({
            "status": "failed",
            "error": str(e),
            "completed_at": datetime.now().isoformat()
        })


async def calculate_pricing_task(task_id: str, rfp_data: Dict[str, Any]):
    """
    Background task for complex pricing calculations.
    """
    logger.info(f"[Task {task_id}] Starting pricing calculation for RFP: {rfp_data.get('title')}")
    task_status[task_id] = {
        "status": "running",
        "started_at": datetime.now().isoformat(),
        "task_type": "calculate_pricing",
        "rfp_id": rfp_data.get("rfp_id")
    }

    try:
        from src.pricing.pricing_engine import PricingEngine

        pricing_engine = PricingEngine()
        results = pricing_engine.generate_pricing(rfp_data)

        task_status[task_id].update({
            "status": "completed",
            "completed_at": datetime.now().isoformat(),
            "result": {
                "total_price": results.total_price,
                "margin": results.margin_percentage
            }
        })
        logger.info(f"[Task {task_id}] Pricing calculation completed")

    except Exception as e:
        logger.error(f"[Task {task_id}] Pricing calculation failed: {e}")
        task_status[task_id].update({
            "status": "failed",
            "error": str(e),
            "completed_at": datetime.now().isoformat()
        })


def get_task_status(task_id: str) -> Dict[str, Any] | None:
    """Get status of a background task."""
    return task_status.get(task_id)
