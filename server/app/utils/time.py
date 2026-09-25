from datetime import datetime, timezone


def utc_now() -> datetime:
    """Naive UTC timestamp for the existing `timestamp without time zone` columns (replaces datetime.utcnow)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
