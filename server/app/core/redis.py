import logging
import threading
import time
from collections.abc import Callable
from typing import TypeVar

import redis

from app.core.config import settings


logger = logging.getLogger(__name__)

T = TypeVar("T")

_lock = threading.Lock()
_client: redis.Redis | None = None
_initialized = False
_skip_until = 0.0


def _create_client() -> redis.Redis | None:
    if not settings.REDIS_URL:
        return None
    return redis.Redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=settings.REDIS_TIMEOUT_SECONDS,
        socket_timeout=settings.REDIS_TIMEOUT_SECONDS,
    )


def get_redis() -> redis.Redis | None:
    global _client, _initialized
    if not _initialized:
        with _lock:
            if not _initialized:
                _client = _create_client()
                _initialized = True
    return _client


def set_redis_client(client: redis.Redis | None) -> None:
    global _client, _initialized, _skip_until
    with _lock:
        _client = client
        _initialized = True
        _skip_until = 0.0


def run(operation: Callable[[redis.Redis], T], default: T) -> T:
    global _skip_until
    client = get_redis()
    if client is None or time.monotonic() < _skip_until:
        return default
    try:
        return operation(client)
    except redis.RedisError as error:
        _skip_until = time.monotonic() + settings.REDIS_RETRY_AFTER_SECONDS
        logger.warning(
            "Redis unavailable (%s); continuing without cache and rate limits for %ss",
            error,
            settings.REDIS_RETRY_AFTER_SECONDS,
        )
        return default


def redis_status() -> str:
    if get_redis() is None:
        return "disabled"
    return "connected" if run(lambda client: client.ping(), False) else "unavailable"
