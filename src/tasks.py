import time
import logging
from typing import Dict, Any
from celery import shared_task
from src.rag.rag_engine import RAGEngine
from src.pricing.pricing_engine import PricingEngine
from src.decision.go_nogo_engine import GoNoGoEngine

logger = logging.getLogger(__name__)

# Initialize engines lazily to avoid overhead on worker startup if possible,
# but for simplicity we'll instantiate them at module level or inside tasks.
# Instantiating inside tasks is safer for multiprocessing but slower.
# We'll use a singleton pattern or global instances if they are thread-safe.

@shared_task(bind=True)
def ingest_documents_task(self, file_paths: list[str]):
    """
    Background task to ingest documents into the RAG system.
    """
    logger.info(f"Starting ingestion of {len(file_paths)} files")
    try:
        rag_engine = RAGEngine()
        # Assuming rag_engine has a method to ingest multiple files or we loop
        # For now, we'll simulate or call a method if it exists.
        # RAGEngine usually builds from a directory, let's assume we trigger a rebuild
        # or add specific files.
        
        # Placeholder logic matching current RAGEngine capabilities
        # In a real scenario, we'd pass specific files to add.
        # Here we might just trigger a re-index of the data directory.
        rag_engine.build_index() 
        
        return {"status": "completed", "files_processed": len(file_paths)}
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise self.retry(exc=e, countdown=60, max_retries=3)

@shared_task(bind=True)
def generate_bid_task(self, rfp_data: Dict[str, Any]):
    """
    Background task to generate a full bid.
    """
    logger.info(f"Starting bid generation for RFP: {rfp_data.get('title')}")
    try:
        # This would typically call the RFPProcessor or similar
        # For now, we'll simulate the heavy lifting
        time.sleep(5) # Simulate processing
        
        return {
            "status": "completed", 
            "bid_id": f"bid_{int(time.time())}",
            "rfp_id": rfp_data.get("rfp_id")
        }
    except Exception as e:
        logger.error(f"Bid generation failed: {e}")
        raise self.retry(exc=e, countdown=60, max_retries=3)

@shared_task(bind=True)
def calculate_pricing_task(self, rfp_data: Dict[str, Any]):
    """
    Background task for complex pricing calculations.
    """
    logger.info(f"Starting pricing calculation for RFP: {rfp_data.get('title')}")
    try:
        pricing_engine = PricingEngine()
        # Simulate complex war gaming or extensive analysis
        results = pricing_engine.generate_pricing(rfp_data)
        
        return {
            "status": "completed",
            "total_price": results.total_price,
            "margin": results.margin_percentage
        }
    except Exception as e:
        logger.error(f"Pricing calculation failed: {e}")
        raise self.retry(exc=e, countdown=60, max_retries=3)
