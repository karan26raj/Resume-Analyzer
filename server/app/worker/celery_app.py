import logging

from celery import Celery
from celery.signals import worker_init

from app.core.config import settings


logger = logging.getLogger(__name__)

celery_app = Celery("resume_analyzer", broker=settings.CELERY_BROKER_URL, include=["app.worker.tasks"])

celery_app.conf.update(
    # Outcomes are recorded on the documents in PostgreSQL, so no result backend is needed.
    task_ignore_result=True,
    # Acknowledge a task only after it finishes: if a worker dies mid-task, Redis redelivers it.
    # Safe because indexing is idempotent (re-indexing replaces a document's vectors).
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Take one task at a time per thread, so a long task doesn't hold others hostage.
    worker_prefetch_multiplier=1,
    task_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    # Publishing from the API must fail fast when Redis is down (the API then indexes in-process).
    broker_connection_timeout=1,
    broker_transport_options={
        "socket_connect_timeout": 1,
        "socket_timeout": 5,
        # Unacknowledged tasks are redelivered after this long; it must exceed the longest task.
        "visibility_timeout": 3600,
    },
    broker_connection_retry_on_startup=True,
)


@worker_init.connect
def prepare_worker(**kwargs):
    # The API creates the Qdrant collection at startup; a worker may start first.
    from app.ai.qdrant_client import ensure_collection

    try:
        ensure_collection()
    except Exception:
        logger.exception("Could not prepare the Qdrant collection; indexing tasks will fail until it is reachable")
