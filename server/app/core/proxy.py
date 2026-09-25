from collections.abc import Mapping

from app.core.config import settings


def client_ip(headers: Mapping[str, str], peer: str | None) -> str:
    if settings.TRUSTED_PROXY_COUNT > 0:
        forwarded = [part.strip() for part in headers.get("x-forwarded-for", "").split(",") if part.strip()]
        if len(forwarded) >= settings.TRUSTED_PROXY_COUNT:
            return forwarded[-settings.TRUSTED_PROXY_COUNT]
    return peer or "unknown"
