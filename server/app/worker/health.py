from app.core.config import settings
from app.services import cache
from app.worker.celery_app import celery_app


STATUS_KEY = f"{cache.SCHEMA_VERSION}:health:worker"
STATUS_TTL_SECONDS = 15
PING_TIMEOUT_SECONDS = 0.5


def worker_status(redis_state: str) -> str:
    """'online', 'offline' (no worker running), 'unavailable' (broker unreachable) or 'disabled'."""
    if not settings.TASK_QUEUE_ENABLED:
        return "disabled"
    # The broker lives on the same Redis server; don't wait on a ping that can't succeed.
    if redis_state == "unavailable":
        return "unavailable"

    cached = cache.get_value(STATUS_KEY)
    if cached:
        return cached

    try:
        replies = celery_app.control.ping(timeout=PING_TIMEOUT_SECONDS)
    except Exception:
        state = "unavailable"
    else:
        state = "online" if replies else "offline"
    cache.set_value(STATUS_KEY, state, STATUS_TTL_SECONDS)
    return state
