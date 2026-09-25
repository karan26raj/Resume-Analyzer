"""Fixed-window rate limiting in Redis. Fails open: if Redis is unavailable, requests are allowed."""
import math
import time
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.redis import run
from app.models.user import User


@dataclass(frozen=True)
class Limit:
    bucket: str
    limit: int
    window_seconds: int


def login_limit() -> Limit:
    return Limit("login", settings.RATE_LIMIT_LOGIN, settings.RATE_LIMIT_LOGIN_WINDOW_SECONDS)


def register_limit() -> Limit:
    return Limit("register", settings.RATE_LIMIT_REGISTER, settings.RATE_LIMIT_REGISTER_WINDOW_SECONDS)


def ai_generate_limit() -> Limit:
    return Limit("ai-generate", settings.RATE_LIMIT_AI_GENERATE, settings.RATE_LIMIT_AI_GENERATE_WINDOW_SECONDS)


def ai_embed_limit() -> Limit:
    return Limit("ai-embed", settings.RATE_LIMIT_AI_EMBED, settings.RATE_LIMIT_AI_EMBED_WINDOW_SECONDS)


def enforce(rule: Limit, identifier: str) -> None:
    """Count one request; raise 429 with a Retry-After header once the window's limit is exceeded."""
    if not settings.RATE_LIMIT_ENABLED:
        return

    now = time.time()
    window_start = int(now // rule.window_seconds) * rule.window_seconds
    window_end = window_start + rule.window_seconds
    key = f"ratelimit:{rule.bucket}:{identifier}:{window_start}"

    def count(client):
        pipeline = client.pipeline()
        pipeline.incr(key)
        pipeline.expireat(key, window_end)
        return pipeline.execute()[0]

    requests = run(count, None)
    if requests is not None and requests > rule.limit:
        retry_after = max(1, math.ceil(window_end - now))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many requests. Try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )


def client_ip(request: Request) -> str:
    # Behind a reverse proxy this is the proxy's address, not the client's.
    return request.client.host if request.client else "unknown"


def limit_per_user(rule_factory):
    """Dependency that rate-limits the authenticated user, e.g. Depends(limit_per_user(ai_embed_limit))."""

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        enforce(rule_factory(), f"user:{current_user.id}")
        return current_user

    return dependency
