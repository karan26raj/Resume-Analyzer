"""Request IDs, the error format, safe messages for external failures, and logging."""
import json
import logging
import re

import httpx
import pytest
from google.genai import errors as genai_errors
from qdrant_client.http.exceptions import ResponseHandlingException
from sqlalchemy.exc import OperationalError

from app.core.config import settings
from app.core.logging import JsonFormatter, request_id_var
from app.services import analysis as analysis_service
from app.services import indexing as indexing_service
from app.services import matching as matching_service
from app.services.matching import AnalysisServiceError
from app.services.retrieval import RetrievedEvidence
from app.tests.helpers import create_job, create_resume, create_user_and_headers, unit_vector
from app.tests.test_analysis import RESUME_TEXT


GENERATED_ID = re.compile(r"^[0-9a-f]{32}$")


def assert_error(response, status_code, code):
    body = response.json()
    assert response.status_code == status_code
    assert body["code"] == code
    assert body["request_id"] == response.headers["X-Request-ID"]
    assert "detail" in body
    return body


def gemini_error(code: int, message: str):
    error_class = genai_errors.ServerError if code >= 500 else genai_errors.ClientError
    return error_class(code, {"error": {"code": code, "message": message, "status": "X"}})


def gemini_fails_with(monkeypatch, error):
    """Run the real analysis pipeline up to the Gemini call, which raises `error`."""
    monkeypatch.setattr(
        analysis_service,
        "retrieve_resume_evidence",
        lambda **kwargs: RetrievedEvidence(passages=[{"chunk_index": 0, "content": RESUME_TEXT, "score": 0.7}], similarity=0.7),
    )

    def raise_error(**kwargs):
        raise error

    monkeypatch.setattr(matching_service, "generate_content_with_fallback", raise_error)


def match(client, db_session):
    user, headers = create_user_and_headers(client, db_session)
    resume = create_resume(db_session, user, raw_text=RESUME_TEXT)
    job = create_job(db_session, user)
    return client.post("/analysis/match", headers=headers, json={"resume_id": resume.id, "job_id": job.id})


def test_every_response_gets_a_request_id(client):
    response = client.get("/health")

    assert GENERATED_ID.match(response.headers["X-Request-ID"])


def test_each_request_gets_its_own_id(client):
    assert client.get("/").headers["X-Request-ID"] != client.get("/").headers["X-Request-ID"]


def test_a_valid_incoming_request_id_is_kept(client):
    response = client.get("/health", headers={"X-Request-ID": "frontend-4f2a.1_b"})

    assert response.headers["X-Request-ID"] == "frontend-4f2a.1_b"


@pytest.mark.parametrize("bad_id", ["has spaces", "x" * 65, "semi;colon", "<script>"])
def test_unsafe_incoming_request_ids_are_replaced(client, bad_id):
    response = client.get("/health", headers={"X-Request-ID": bad_id})

    assert GENERATED_ID.match(response.headers["X-Request-ID"])


def test_not_found_uses_the_error_format(client, db_session):
    _, headers = create_user_and_headers(client, db_session)

    body = assert_error(client.get("/resumes/987654321", headers=headers), 404, "not_found")

    assert body["detail"] == "Resume not found"


def test_unauthenticated_keeps_the_www_authenticate_header(client):
    response = client.get("/auth/me", headers={"Authorization": "Bearer nope"})

    assert_error(response, 401, "not_authenticated")
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_conflict_uses_the_error_format(client, db_session):
    user, _ = create_user_and_headers(client, db_session)

    response = client.post("/auth/register", json={"email": user.email, "password": "password123"})

    assert_error(response, 409, "conflict")


def test_validation_errors_do_not_echo_submitted_values(client):
    response = client.post("/auth/register", json={"email": "not-an-email", "password": "sh"})

    body = assert_error(response, 422, "validation_error")
    fields = {tuple(error["loc"]) for error in body["detail"]}
    assert ("body", "email") in fields
    assert all(set(error) == {"loc", "msg", "type"} for error in body["detail"])
    assert "not-an-email" not in response.text


def test_rate_limit_keeps_retry_after(client, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_LOGIN", 1)
    body = {"email": "nobody@example.com", "password": "wrong-password"}
    client.post("/auth/login", json=body)

    response = client.post("/auth/login", json=body)

    assert_error(response, 429, "rate_limited")
    assert int(response.headers["Retry-After"]) > 0


def test_unknown_route_uses_the_error_format(client):
    assert_error(client.get("/no-such-route"), 404, "not_found")


def test_unhandled_error_returns_a_safe_500_and_logs_the_traceback(client, db_session, monkeypatch, caplog):
    _, headers = create_user_and_headers(client, db_session)

    def broken(*args, **kwargs):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr("app.api.recommendations.cache.get_json", broken)

    with caplog.at_level(logging.ERROR, logger="app.errors"):
        response = client.get("/recommendations", headers=headers)

    body = assert_error(response, 500, "internal_error")
    assert "secret internal detail" not in response.text
    assert body["detail"] == "Something went wrong on our side. Please try again."
    [record] = [r for r in caplog.records if r.name == "app.errors"]
    assert record.exc_info and "secret internal detail" in str(record.exc_info[1])
    assert record.request_id == body["request_id"]  # the user's reference finds the traceback


def test_database_outage_returns_503(client, db_session, monkeypatch):
    _, headers = create_user_and_headers(client, db_session)

    def database_down(*args, **kwargs):
        raise OperationalError("SELECT 1", {}, Exception("connection to server at 10.0.0.5 refused"))

    monkeypatch.setattr("app.api.recommendations.cache.get_json", database_down)

    response = client.get("/recommendations", headers=headers)

    assert_error(response, 503, "database_unavailable")
    assert response.headers["Retry-After"] == "30"
    assert "10.0.0.5" not in response.text


def test_vector_store_outage_returns_503(client, db_session, monkeypatch):
    _, headers = create_user_and_headers(client, db_session)
    monkeypatch.setattr("app.api.embeddings.create_embeddings", lambda texts, task_type: ([unit_vector(0)], None))

    def qdrant_down(**kwargs):
        raise ResponseHandlingException(httpx.ConnectError("connection refused by qdrant:6333"))

    monkeypatch.setattr("app.api.embeddings.search_chunks", qdrant_down)

    response = client.post("/embeddings/search", headers=headers, json={"query": "python"})

    assert_error(response, 503, "vector_store_unavailable")
    assert "qdrant:6333" not in response.text


def test_overloaded_gemini_returns_503_without_the_raw_error(client, db_session, monkeypatch, caplog):
    gemini_fails_with(monkeypatch, gemini_error(503, "The model is overloaded. Internal cluster us-east-7."))

    with caplog.at_level(logging.WARNING, logger="app.errors"):
        response = match(client, db_session)

    body = assert_error(response, 503, "ai_unavailable")
    assert response.headers["Retry-After"] == "30"
    assert "us-east-7" not in response.text
    assert body["detail"] == "The AI service is temporarily unavailable. Please try again shortly."
    assert any("us-east-7" in record.getMessage() for record in caplog.records)


def test_rate_limited_gemini_returns_503_with_a_longer_retry(client, db_session, monkeypatch):
    gemini_fails_with(monkeypatch, gemini_error(429, "Quota exceeded for project 123456"))

    response = match(client, db_session)

    assert_error(response, 503, "ai_rate_limited")
    assert response.headers["Retry-After"] == "60"
    assert "123456" not in response.text


def test_rejected_gemini_request_returns_a_generic_502(client, db_session, monkeypatch):
    gemini_fails_with(monkeypatch, gemini_error(400, "Invalid argument: field x.y.z"))

    body = assert_error(match(client, db_session), 502, "upstream_error")

    assert "x.y.z" not in body["detail"]


def test_our_own_messages_are_shown_as_written(client, db_session, monkeypatch):
    def fail(**kwargs):
        raise AnalysisServiceError("Gemini returned an empty response")

    monkeypatch.setattr(
        analysis_service,
        "retrieve_resume_evidence",
        lambda **kwargs: RetrievedEvidence(passages=[], similarity=None),
    )
    monkeypatch.setattr(analysis_service, "generate_match", fail)

    body = assert_error(match(client, db_session), 502, "upstream_error")

    assert body["detail"] == "Gemini returned an empty response"


def test_access_log_line_carries_the_request_id(client, db_session, caplog):
    _, headers = create_user_and_headers(client, db_session)

    with caplog.at_level(logging.INFO, logger="app.access"):
        response = client.get("/jobs", headers={**headers, "X-Request-ID": "trace-jobs-1"})

    [line] = [r for r in caplog.records if r.name == "app.access" and "/jobs" in r.getMessage()]
    assert re.match(r"^GET /jobs 200 \d+ms$", line.getMessage())
    assert line.request_id == response.headers["X-Request-ID"] == "trace-jobs-1"


def test_health_checks_are_not_logged_at_info(client, caplog):
    with caplog.at_level(logging.INFO, logger="app.access"):
        client.get("/health")

    assert not [r for r in caplog.records if r.name == "app.access"]


def test_json_log_format():
    token = request_id_var.set("abc123")
    try:
        record = logging.getLogger("app.test").makeRecord("app.test", logging.WARNING, __file__, 1, "hello %s", ("world",), None)
    finally:
        request_id_var.reset(token)

    entry = json.loads(JsonFormatter().format(record))

    assert entry["message"] == "hello world"
    assert entry["request_id"] == "abc123"
    assert entry["level"] == "WARNING"


def test_worker_logs_carry_the_request_id_of_the_upload(client, db_session, monkeypatch, worker_sessions):
    monkeypatch.setattr(settings, "AUTO_INDEX_DOCUMENTS", True)
    monkeypatch.setattr(settings, "TASK_QUEUE_ENABLED", True)
    monkeypatch.setattr(indexing_service, "_queue_skip_until", 0.0)
    seen = []

    def create_embeddings(chunks, **kwargs):
        seen.append(request_id_var.get())  # what the task's log lines would carry
        return [unit_vector(0) for _ in chunks], None

    monkeypatch.setattr(indexing_service, "create_embeddings", create_embeddings)
    _, headers = create_user_and_headers(client, db_session)

    client.post(
        "/jobs",
        headers={**headers, "X-Request-ID": "upload-trace-7"},
        json={"title": "Dev", "company": "Acme", "description": "Python"},
    )

    assert seen == ["upload-trace-7"]
