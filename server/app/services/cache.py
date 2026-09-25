import json
from typing import Any

from app.core.redis import run

SCHEMA_VERSION = "v1"

def analysis_key(user_id: int, resume_id: int, job_id: int) -> str:
    return f"{SCHEMA_VERSION}:analysis:{user_id}:r{resume_id}:j{job_id}"


def rewrite_key(user_id: int, resume_id: int, job_id: int) -> str:
    return f"{SCHEMA_VERSION}:rewrite:{user_id}:r{resume_id}:j{job_id}"


def interview_key(user_id: int, resume_id: int, job_id: int) -> str:
    return f"{SCHEMA_VERSION}:interview:{user_id}:r{resume_id}:j{job_id}"


def _version_key(user_id: int) -> str:
    return f"{SCHEMA_VERSION}:user:{user_id}:version"


def recommendations_key(user_id: int, name: str, *parts: object) -> str:
    version = run(lambda client: client.get(_version_key(user_id)), None) or "0"
    suffix = ":".join(str(part) for part in parts)
    return f"{SCHEMA_VERSION}:recs:{user_id}:v{version}:{name}:{suffix}"


def get_value(key: str) -> str | None:
    return run(lambda client: client.get(key), None)


def set_value(key: str, value: str, ttl_seconds: int) -> None:
    run(lambda client: client.set(key, value, ex=ttl_seconds), None)


def get_json(key: str) -> Any | None:
    raw = get_value(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except ValueError:
        return None


def set_json(key: str, value: Any, ttl_seconds: int) -> None:
    set_value(key, json.dumps(value, default=str), ttl_seconds)


def delete(*keys: str) -> None:
    if keys:
        run(lambda client: client.delete(*keys), None)


def _delete_matching(pattern: str) -> None:
    def operation(client):
        keys = list(client.scan_iter(match=pattern, count=500))
        if keys:
            client.delete(*keys)

    run(operation, None)


def invalidate_user_recommendations(user_id: int) -> None:
    run(lambda client: client.incr(_version_key(user_id)), None)


def invalidate_resume(user_id: int, resume_id: int) -> None:
    for kind in ("analysis", "rewrite", "interview"):
        _delete_matching(f"{SCHEMA_VERSION}:{kind}:{user_id}:r{resume_id}:j*")
    invalidate_user_recommendations(user_id)


def invalidate_job(user_id: int, job_id: int) -> None:
    for kind in ("analysis", "rewrite", "interview"):
        _delete_matching(f"{SCHEMA_VERSION}:{kind}:{user_id}:r*:j{job_id}")
    invalidate_user_recommendations(user_id)
