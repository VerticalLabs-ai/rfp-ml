"""
Celery application configuration for background task processing.

Handles:
- Proposal generation tasks
- Alert evaluation and email delivery
- Document processing
- Scraping operations
"""
import os
import sys

from celery import Celery
from celery.schedules import crontab

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Get Redis URL from environment or settings
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create Celery app
celery_app = Celery(
    "rfp_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "api.app.worker.tasks.generation",
        "api.app.worker.tasks.alerts",
    ]
)

# Celery configuration
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Task tracking
    task_track_started=True,
    task_acks_late=True,  # Acknowledge after completion (more reliable)

    # Limits
    task_time_limit=600,  # 10 minutes max per task
    task_soft_time_limit=540,  # Soft limit at 9 minutes (raises exception)

    # Worker configuration
    worker_prefetch_multiplier=1,  # Fetch one task at a time (fairer distribution)
    worker_concurrency=4,  # Number of concurrent workers

    # Result backend
    result_expires=3600,  # Results expire after 1 hour

    # Task routing (optional, for scaling)
    task_routes={
        "api.app.worker.tasks.generation.*": {"queue": "generation"},
        "api.app.worker.tasks.alerts.*": {"queue": "alerts"},
    },

    # Default queue
    task_default_queue="default",
)

# Periodic tasks (Celery Beat)
celery_app.conf.beat_schedule = {
    # Evaluate alert rules every 15 minutes
    "evaluate-alerts-every-15-minutes": {
        "task": "api.app.worker.tasks.alerts.evaluate_alert_rules",
        "schedule": crontab(minute="*/15"),
    },
}


# Task state callbacks for WebSocket broadcasting
@celery_app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery connectivity."""
    print(f"Request: {self.request!r}")
    return {"status": "ok", "task_id": self.request.id}


def get_celery_app():
    """Get the Celery app instance."""
    return celery_app
