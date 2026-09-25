import pytest
from pydantic import ValidationError

from app.ai import qdrant_client as qdrant_module
from app.core import proxy
from app.core.config import Settings, settings
from app.core.database import engine
from app.models.resume import Resume
from app.tests.helpers import create_user_and_headers
from app.tests.test_resumes import _pdf_bytes


BASE = {"DATABASE_URL": "postgresql+psycopg2://u:p@db/app", "JWT_SECRET_KEY": "x" * 40}
FRONTEND = ["https://resume-analyzer.vercel.app"]


def make(**overrides):
    return Settings(_env_file=None, **{**BASE, **overrides})


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("postgres://u:p@ep-1.neon.tech/app?sslmode=require", "postgresql+psycopg2://u:p@ep-1.neon.tech/app?sslmode=require"),
        ("postgresql://u:p@db:5432/app", "postgresql+psycopg2://u:p@db:5432/app"),
        ("postgresql+psycopg2://u:p@db/app", "postgresql+psycopg2://u:p@db/app"),
    ],
)
def test_database_urls_from_hosting_providers_are_normalised(given, expected):
    assert make(DATABASE_URL=given).DATABASE_URL == expected


def test_valid_production_settings_are_accepted():
    production = make(ENVIRONMENT="production", DEBUG=False, CORS_ORIGINS=FRONTEND)

    assert production.ENVIRONMENT == "production"


@pytest.mark.parametrize(
    ("overrides", "problem"),
    [
        ({"DEBUG": True, "CORS_ORIGINS": FRONTEND}, "DEBUG must be false"),
        ({"JWT_SECRET_KEY": "short", "CORS_ORIGINS": FRONTEND}, "JWT_SECRET_KEY must be at least 32 characters"),
        ({"CORS_ORIGINS": []}, "CORS_ORIGINS (or CORS_ORIGIN_REGEX) must name the frontend"),
        ({"CORS_ORIGINS": ["*"]}, "CORS_ORIGINS must not contain '*'"),
    ],
)
def test_unsafe_production_settings_refuse_to_start(overrides, problem):
    with pytest.raises(ValidationError) as error:
        make(ENVIRONMENT="production", **overrides)

    assert problem in str(error.value)


def test_development_allows_debug_and_short_secrets():
    development = make(DEBUG=True, JWT_SECRET_KEY="dev")

    assert development.DEBUG is True


def test_qdrant_cloud_uses_url_and_api_key(monkeypatch):
    captured = {}
    monkeypatch.setattr(settings, "QDRANT_LOCATION", None)
    monkeypatch.setattr(settings, "QDRANT_URL", "https://abc.eu-central.aws.cloud.qdrant.io:6333")
    monkeypatch.setattr(settings, "QDRANT_API_KEY", "secret-key")
    monkeypatch.setattr(qdrant_module, "QdrantClient", lambda **kwargs: captured.update(kwargs) or object())
    qdrant_module.get_qdrant_client.cache_clear()

    try:
        qdrant_module.get_qdrant_client()
    finally:
        qdrant_module.get_qdrant_client.cache_clear()

    assert captured == {"url": "https://abc.eu-central.aws.cloud.qdrant.io:6333", "api_key": "secret-key"}


def test_database_connections_are_checked_before_use():
    assert engine.pool._pre_ping is True
    assert engine.pool._recycle == 300


@pytest.mark.parametrize(
    ("proxies", "header", "expected"),
    [
        (0, "203.0.113.9", "10.0.0.2"),
        (1, "203.0.113.9", "203.0.113.9"),
        (1, "1.2.3.4, 203.0.113.9", "203.0.113.9"),
        (2, "1.2.3.4, 203.0.113.9, 10.1.1.1", "203.0.113.9"),
        (2, "203.0.113.9", "10.0.0.2"),
        (1, "", "10.0.0.2"),
    ],
)
def test_client_ip_behind_proxies(monkeypatch, proxies, header, expected):
    monkeypatch.setattr(settings, "TRUSTED_PROXY_COUNT", proxies)

    assert proxy.client_ip({"x-forwarded-for": header}, "10.0.0.2") == expected


def test_rate_limit_counts_the_real_client_not_the_proxy(client, monkeypatch):
    monkeypatch.setattr(settings, "TRUSTED_PROXY_COUNT", 1)
    monkeypatch.setattr(settings, "RATE_LIMIT_LOGIN", 1)
    body = {"email": "nobody@example.com", "password": "wrong-password"}

    def login(ip):
        return client.post("/auth/login", json=body, headers={"X-Forwarded-For": ip}).status_code

    assert login("203.0.113.1") == 401
    assert login("203.0.113.1") == 429
    assert login("203.0.113.2") == 401


def test_spoofed_forwarded_for_does_not_bypass_the_limit(client, monkeypatch):
    monkeypatch.setattr(settings, "TRUSTED_PROXY_COUNT", 1)
    monkeypatch.setattr(settings, "RATE_LIMIT_LOGIN", 1)
    body = {"email": "nobody@example.com", "password": "wrong-password"}

    first = client.post("/auth/login", json=body, headers={"X-Forwarded-For": "6.6.6.1, 203.0.113.7"})
    second = client.post("/auth/login", json=body, headers={"X-Forwarded-For": "6.6.6.2, 203.0.113.7"})

    assert (first.status_code, second.status_code) == (401, 429)


def test_liveness_check_does_not_touch_redis(client, monkeypatch):
    def fail():
        raise AssertionError("liveness must not call Redis")

    monkeypatch.setattr("app.main.redis_status", fail)

    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_uploads_without_file_storage(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "STORE_UPLOADED_FILES", False)
    _, headers = create_user_and_headers(client, db_session)

    response = client.post(
        "/resumes/upload",
        headers=headers,
        files={"file": ("resume.pdf", _pdf_bytes("Python developer"), "application/pdf")},
    )

    assert response.status_code == 201
    resume = db_session.get(Resume, response.json()["resume_id"])
    assert (resume.raw_text, resume.file_path) == ("Python developer", "")
    assert list(tmp_path.iterdir()) == []
    assert client.get(f"/resumes/{resume.id}/text", headers=headers).json()["text"] == "Python developer"
    assert client.delete(f"/resumes/{resume.id}", headers=headers).status_code == 204
    assert list(tmp_path.iterdir()) == []
