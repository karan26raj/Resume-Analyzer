import re
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from app.core.config import settings
from app.main import app
from app.models.user import User
from app.tests.helpers import create_user_and_headers
from app.utils.jwt import create_access_token


PUBLIC_ROUTES = {("GET", "/"), ("GET", "/health"), ("GET", "/health/live"), ("POST", "/auth/register"), ("POST", "/auth/login")}


def token(payload: dict, key: str | None = None, algorithm: str | None = None) -> dict[str, str]:
    encoded = jwt.encode(payload, key or settings.JWT_SECRET_KEY, algorithm=algorithm or settings.JWT_ALGORITHM)
    return {"Authorization": f"Bearer {encoded}"}


def in_minutes(minutes: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=minutes)


def api_routes() -> set[tuple[str, str]]:
    return {
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        for method in operations
    }


def protected_routes():
    for method, path in api_routes() - PUBLIC_ROUTES:
        yield method, re.sub(r"\{[^}]+\}", "1", path)


PROTECTED = sorted(set(protected_routes()))


def test_route_discovery_finds_the_api():
    assert len(PROTECTED) >= 15


@pytest.mark.parametrize(("method", "path"), PROTECTED)
def test_every_non_public_route_requires_a_token(client, method, path):
    response = client.request(method, path)

    assert response.status_code == 401, f"{method} {path} is reachable without a token"


def test_public_routes_list_matches_the_app():
    assert PUBLIC_ROUTES <= api_routes()


def test_valid_token_is_accepted(client, db_session):
    user, _ = create_user_and_headers(client, db_session)

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {create_access_token(user.id)}"})

    assert response.status_code == 200
    assert response.json()["id"] == user.id


def test_expired_token_is_rejected(client, db_session):
    user, _ = create_user_and_headers(client, db_session)

    response = client.get("/auth/me", headers=token({"sub": str(user.id), "exp": in_minutes(-1)}))

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_token_signed_with_another_key_is_rejected(client, db_session):
    user, _ = create_user_and_headers(client, db_session)

    response = client.get("/auth/me", headers=token({"sub": str(user.id), "exp": in_minutes(5)}, key="not-the-secret"))

    assert response.status_code == 401


def test_token_with_another_algorithm_is_rejected(client, db_session):
    user, _ = create_user_and_headers(client, db_session)

    response = client.get(
        "/auth/me", headers=token({"sub": str(user.id), "exp": in_minutes(5)}, algorithm="HS512")
    )

    assert response.status_code == 401


@pytest.mark.parametrize("value", ["not-a-jwt", "a.b.c", ""])
def test_malformed_tokens_are_rejected(client, value):
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {value}"})

    assert response.status_code == 401


def test_non_bearer_scheme_is_rejected(client, db_session):
    user, _ = create_user_and_headers(client, db_session)

    response = client.get("/auth/me", headers={"Authorization": f"Basic {create_access_token(user.id)}"})

    assert response.status_code == 401


@pytest.mark.parametrize("payload", [{}, {"sub": "abc"}, {"sub": ""}, {"sub": "12.5"}])
def test_tokens_without_a_valid_subject_are_rejected(client, payload):
    response = client.get("/auth/me", headers=token({**payload, "exp": in_minutes(5)}))

    assert response.status_code == 401


def test_token_of_a_deleted_user_is_rejected(client, db_session):
    user, headers = create_user_and_headers(client, db_session)
    db_session.delete(db_session.get(User, user.id))
    db_session.commit()

    assert client.get("/auth/me", headers=headers).status_code == 401


def test_login_with_unknown_email_gives_the_same_error_as_a_wrong_password(client, db_session):
    user, _ = create_user_and_headers(client, db_session)

    unknown = client.post("/auth/login", json={"email": "nobody@example.com", "password": "password123"})
    wrong = client.post("/auth/login", json={"email": user.email, "password": "wrong-password"})

    assert unknown.status_code == wrong.status_code == 401
    for field in ("detail", "code"):
        assert unknown.json()[field] == wrong.json()[field]


def test_oversized_upload_is_rejected(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_BYTES", 1024)
    _, headers = create_user_and_headers(client, db_session)

    response = client.post(
        "/resumes/upload",
        headers=headers,
        files={"file": ("big.pdf", b"%PDF-1.7\n" + b"0" * 2048, "application/pdf")},
    )

    assert response.status_code == 413
    assert list(tmp_path.iterdir()) == []
