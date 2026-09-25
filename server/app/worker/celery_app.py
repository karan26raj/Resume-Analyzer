import logging

from celery import Celery
from celery.signals import setup_logging, task_postrun, task_prerun, worker_init

from app.core.config import settings
from app.core.logging import configure_logging, request_id_var


logger = logging.getLogger(__name__)

celery_app = Celery("resume_analyzer", broker=settings.CELERY_BROKER_URL, include=["app.worker.tasks"])

celery_app.conf.update(
    # Outcomes are recorded on the documents in PostgreSQL, so no result backend is needed.
    task_ignore_result=True,
    # Acknowledge a task only after it finishes: if a worker dies mid-task, Redis redelivers it.
    # Safe because indexing is idempotent (re-indexing replaces a document's vectors).
    task_acks_late=True,
    task_reject_on_worker_lost=True,
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
    worker_hijack_root_logger=False,
)


@setup_logging.connect
def use_app_logging(**kwargs):
    # Connecting to this signal stops Celery from installing its own logging configuration.
    configure_logging(settings.LOG_LEVEL, settings.LOG_JSON)


_request_id_tokens = {}


def task_request_id(task) -> str | None:
    """The request ID the API attached when it queued the task (see schedule_indexing)."""
    request = task.request
    # A worker exposes custom message headers on the request; eager (test) mode nests them.
    return request.get("request_id") or (getattr(request, "headers", None) or {}).get("request_id")


@task_prerun.connect
def bind_request_id(task_id=None, task=None, **kwargs):
    _request_id_tokens[task_id] = request_id_var.set(task_request_id(task) or task_id)


@task_postrun.connect
def unbind_request_id(task_id=None, **kwargs):
    token = _request_id_tokens.pop(task_id, None)
    if token is not None:
        request_id_var.reset(token)


@worker_init.connect
def prepare_worker(**kwargs):
    # The API creates the Qdrant collection at startup; a worker may start first.
    from app.ai.qdrant_client import ensure_collection

    try:
        ensure_collection()
    except Exception:
        logger.exception("Could not prepare the Qdrant collection; indexing tasks will fail until it is reachable")
