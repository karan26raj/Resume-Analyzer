import fakeredis
import pytest

from app.api import rate_limit
from app.core import redis as redis_module
from app.core.config import settings
from app.models.analysis_result import AnalysisResult
from app.services import analysis as analysis_service
from app.services import cache
from app.services.retrieval import RetrievedEvidence
from app.tests.helpers import create_analysis, create_job, create_resume, create_user_and_headers
from app.tests.test_analysis import RESUME_TEXT, fake_assessment
from app.tests.test_resumes import _pdf_bytes


def count_gemini_matches(monkeypatch):
    calls = []

    def fake_generate_match(**kwargs):
        calls.append(kwargs)
        return fake_assessment(), 1000, 250, "gemini-test-model"

    monkeypatch.setattr(
        analysis_service,
        "retrieve_resume_evidence",
        lambda **kwargs: RetrievedEvidence(
            passages=[{"chunk_index": 0, "content": RESUME_TEXT, "score": 0.7}], similarity=0.7
        ),
    )
    monkeypatch.setattr(analysis_service, "generate_match", fake_generate_match)
    return calls


def count_rewrites(monkeypatch, resume, job):
    calls = []

    def fake_rewrite(**kwargs):
        calls.append(kwargs)
        return {
            "resume_id": resume.id, "job_id": job.id, "model": "gemini-test-model",
            "input_tokens": 10, "output_tokens": 5, "rejected": [],
            "suggestions": [{"section": "Experience", "original": "a", "rewritten": f"b{len(calls)}", "rationale": "r"}],
        }

    monkeypatch.setattr("app.api.rewrite.rewrite_resume", fake_rewrite)
    return calls


def setup_pair(client, db_session):
    user, headers = create_user_and_headers(client, db_session)
    resume = create_resume(db_session, user, raw_text=RESUME_TEXT)
    job = create_job(db_session, user)
    return user, headers, resume, job


def match(client, headers, resume, job, **extra):
    return client.post("/analysis/match", headers=headers, json={"resume_id": resume.id, "job_id": job.id, **extra})


def rewrite(client, headers, resume, job, **extra):
    return client.post("/resumes/rewrite", headers=headers, json={"resume_id": resume.id, "job_id": job.id, **extra})


def disconnected_redis():
    server = fakeredis.FakeServer()
    server.connected = False
    return fakeredis.FakeRedis(server=server, decode_responses=True)


def test_repeated_analysis_is_served_from_cache(client, db_session, monkeypatch):
    user, headers, resume, job = setup_pair(client, db_session)
    calls = count_gemini_matches(monkeypatch)

    first = match(client, headers, resume, job)
    second = match(client, headers, resume, job)

    assert first.status_code == 201 and first.json()["cached"] is False
    assert second.status_code == 200 and second.json()["cached"] is True
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["requirements"] == first.json()["requirements"]
    assert len(calls) == 1
    assert db_session.query(AnalysisResult).filter(AnalysisResult.user_id == user.id).count() == 1


def test_force_runs_a_new_analysis_and_updates_the_cache(client, db_session, monkeypatch):
    _, headers, resume, job = setup_pair(client, db_session)
    calls = count_gemini_matches(monkeypatch)

    first = match(client, headers, resume, job)
    forced = match(client, headers, resume, job, force=True)
    after = match(client, headers, resume, job)

    assert forced.status_code == 201 and forced.json()["cached"] is False
    assert forced.json()["id"] != first.json()["id"]
    assert after.json()["id"] == forced.json()["id"]
    assert len(calls) == 2


def test_cached_id_of_a_missing_analysis_is_ignored(client, db_session, monkeypatch, redis_client):
    user, headers, resume, job = setup_pair(client, db_session)
    calls = count_gemini_matches(monkeypatch)
    redis_client.set(cache.analysis_key(user.id, resume.id, job.id), "987654321")

    response = match(client, headers, resume, job)

    assert response.status_code == 201 and response.json()["cached"] is False
    assert len(calls) == 1


def test_other_pairs_are_not_served_from_the_cache(client, db_session, monkeypatch):
    user, headers, resume, job = setup_pair(client, db_session)
    other_job = create_job(db_session, user, title="Data Engineer")
    calls = count_gemini_matches(monkeypatch)

    match(client, headers, resume, job)
    response = match(client, headers, resume, other_job)

    assert response.status_code == 201 and response.json()["job_id"] == other_job.id
    assert len(calls) == 2


def test_history_endpoints_report_uncached(client, db_session, monkeypatch):
    _, headers, resume, job = setup_pair(client, db_session)
    count_gemini_matches(monkeypatch)
    analysis_id = match(client, headers, resume, job).json()["id"]

    assert client.get(f"/analysis/{analysis_id}", headers=headers).json()["cached"] is False
    assert client.get("/analysis", headers=headers).json()[0]["cached"] is False


def test_repeated_rewrite_is_served_from_cache(client, db_session, monkeypatch):
    _, headers, resume, job = setup_pair(client, db_session)
    calls = count_rewrites(monkeypatch, resume, job)

    first = rewrite(client, headers, resume, job)
    second = rewrite(client, headers, resume, job)

    assert first.json()["cached"] is False
    assert second.json()["cached"] is True
    assert second.json()["suggestions"] == first.json()["suggestions"]
    assert len(calls) == 1


def test_force_generates_new_rewrites(client, db_session, monkeypatch):
    _, headers, resume, job = setup_pair(client, db_session)
    calls = count_rewrites(monkeypatch, resume, job)

    rewrite(client, headers, resume, job)
    forced = rewrite(client, headers, resume, job, force=True)
    after = rewrite(client, headers, resume, job)

    assert forced.json()["cached"] is False
    assert forced.json()["suggestions"][0]["rewritten"] == "b2"
    assert after.json()["suggestions"][0]["rewritten"] == "b2"
    assert len(calls) == 2


def test_deleting_a_job_invalidates_only_that_jobs_entries(client, db_session, monkeypatch, redis_client):
    user, headers, resume, job = setup_pair(client, db_session)
    other_job = create_job(db_session, user, title="Data Engineer")
    count_gemini_matches(monkeypatch)
    count_rewrites(monkeypatch, resume, job)
    for target in (job, other_job):
        match(client, headers, resume, target)
        rewrite(client, headers, resume, target)

    assert client.delete(f"/jobs/{job.id}", headers=headers).status_code == 204

    assert redis_client.get(cache.analysis_key(user.id, resume.id, job.id)) is None
    assert redis_client.get(cache.rewrite_key(user.id, resume.id, job.id)) is None
    assert redis_client.get(cache.analysis_key(user.id, resume.id, other_job.id)) is not None
    assert redis_client.get(cache.rewrite_key(user.id, resume.id, other_job.id)) is not None


def test_deleting_a_resume_invalidates_its_entries(client, db_session, monkeypatch, redis_client):
    user, headers, resume, job = setup_pair(client, db_session)
    count_gemini_matches(monkeypatch)
    count_rewrites(monkeypatch, resume, job)
    match(client, headers, resume, job)
    rewrite(client, headers, resume, job)

    assert client.delete(f"/resumes/{resume.id}", headers=headers).status_code == 204

    assert redis_client.get(cache.analysis_key(user.id, resume.id, job.id)) is None
    assert redis_client.get(cache.rewrite_key(user.id, resume.id, job.id)) is None


def test_invalidation_does_not_touch_other_users(client, db_session, monkeypatch, redis_client):
    user, headers, resume, job = setup_pair(client, db_session)
    other_key = cache.analysis_key(user.id + 1, resume.id, job.id)
    redis_client.set(other_key, "1")

    client.delete(f"/jobs/{job.id}", headers=headers)

    assert redis_client.get(other_key) == "1"


def test_skill_gap_summary_is_cached_until_the_user_changes_something(client, db_session):
    user, headers, resume, job = setup_pair(client, db_session)

    assert client.get("/recommendations", headers=headers).json()["analysis_count"] == 0
    create_analysis(db_session, user, resume, job)
    assert client.get("/recommendations", headers=headers).json()["analysis_count"] == 0

    client.post("/jobs", headers=headers, json={"title": "SRE", "company": "Acme", "description": "Linux"})
    assert client.get("/recommendations", headers=headers).json()["analysis_count"] == 1


def test_new_analysis_refreshes_recommendations(client, db_session, monkeypatch):
    _, headers, resume, job = setup_pair(client, db_session)
    count_gemini_matches(monkeypatch)

    assert client.get("/recommendations", headers=headers).json()["analysis_count"] == 0
    match(client, headers, resume, job)
    assert client.get("/recommendations", headers=headers).json()["analysis_count"] == 1


def test_job_recommendations_are_cached_but_partial_results_are_not(client, db_session, monkeypatch):
    _, headers, resume, job = setup_pair(client, db_session)
    calls = []
    unindexed = [[job.id], []]

    def fake_recommend_jobs(**kwargs):
        calls.append(kwargs)
        return [], unindexed[len(calls) - 1]

    monkeypatch.setattr("app.api.recommendations.recommend_jobs", fake_recommend_jobs)

    first = client.get("/recommendations/jobs", headers=headers).json()
    second = client.get("/recommendations/jobs", headers=headers).json()
    third = client.get("/recommendations/jobs", headers=headers).json()

    assert first["unindexed_job_ids"] == [job.id]
    assert second["unindexed_job_ids"] == []
    assert third == second
    assert len(calls) == 2


def test_uploading_a_resume_refreshes_latest_resume_recommendations(client, db_session, monkeypatch, tmp_path):
    _, headers, first_resume, _ = setup_pair(client, db_session)
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr("app.api.recommendations.recommend_jobs", lambda **kwargs: ([], []))
    assert client.get("/recommendations/jobs", headers=headers).json()["resume_id"] == first_resume.id

    upload = client.post(
        "/resumes/upload",
        headers=headers,
        files={"file": ("newer.pdf", _pdf_bytes("Python FastAPI PostgreSQL"), "application/pdf")},
    )
    assert upload.status_code == 201

    assert client.get("/recommendations/jobs", headers=headers).json()["resume_id"] == upload.json()["resume_id"]


def test_login_is_rate_limited_per_ip(client, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_LOGIN", 3)
    body = {"email": "nobody@example.com", "password": "wrong-password"}

    statuses = [client.post("/auth/login", json=body).status_code for _ in range(4)]

    assert statuses == [401, 401, 401, 429]
    limited = client.post("/auth/login", json=body)
    assert int(limited.headers["Retry-After"]) > 0
    assert "Too many requests" in limited.json()["detail"]


def test_register_is_rate_limited_per_ip(client, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_REGISTER", 2)

    statuses = [
        client.post("/auth/register", json={"email": f"user{index}@example.com", "password": "password123"}).status_code
        for index in range(3)
    ]

    assert statuses == [201, 201, 429]


def test_ai_limit_counts_only_real_gemini_calls(client, db_session, monkeypatch):
    _, headers, resume, job = setup_pair(client, db_session)
    count_gemini_matches(monkeypatch)
    monkeypatch.setattr(settings, "RATE_LIMIT_AI_GENERATE", 1)

    assert match(client, headers, resume, job).status_code == 201
    assert match(client, headers, resume, job).status_code == 200
    assert match(client, headers, resume, job, force=True).status_code == 429


def test_ai_limit_is_shared_by_rewrite_and_assistant(client, db_session, monkeypatch):
    _, headers, resume, job = setup_pair(client, db_session)
    count_rewrites(monkeypatch, resume, job)
    monkeypatch.setattr("app.api.assistant.ask_question", lambda **kwargs: ("answer", []))
    monkeypatch.setattr(settings, "RATE_LIMIT_AI_GENERATE", 2)

    assert rewrite(client, headers, resume, job).status_code == 200
    assert client.post("/assistant/ask", headers=headers, json={"question": "Hi?"}).status_code == 200
    assert client.post("/assistant/ask", headers=headers, json={"question": "Hi?"}).status_code == 429


def test_ai_limits_are_per_user(client, db_session, monkeypatch):
    _, headers = create_user_and_headers(client, db_session)
    _, other_headers = create_user_and_headers(client, db_session)
    monkeypatch.setattr("app.api.assistant.ask_question", lambda **kwargs: ("answer", []))
    monkeypatch.setattr(settings, "RATE_LIMIT_AI_GENERATE", 1)

    assert client.post("/assistant/ask", headers=headers, json={"question": "Hi?"}).status_code == 200
    assert client.post("/assistant/ask", headers=headers, json={"question": "Hi?"}).status_code == 429
    assert client.post("/assistant/ask", headers=other_headers, json={"question": "Hi?"}).status_code == 200


def test_embedding_endpoints_have_their_own_limit(client, db_session, monkeypatch):
    _, headers = create_user_and_headers(client, db_session)
    monkeypatch.setattr("app.api.embeddings.create_embeddings", lambda texts, task_type: ([[0.0] * 3], 1))
    monkeypatch.setattr("app.api.embeddings.search_chunks", lambda **kwargs: [])
    monkeypatch.setattr(settings, "RATE_LIMIT_AI_EMBED", 1)

    assert client.post("/embeddings/search", headers=headers, json={"query": "python"}).status_code == 200
    assert client.post("/embeddings/search", headers=headers, json={"query": "python"}).status_code == 429


def test_limit_resets_in_the_next_window(client, monkeypatch, redis_client):
    monkeypatch.setattr(settings, "RATE_LIMIT_LOGIN", 1)
    body = {"email": "nobody@example.com", "password": "wrong-password"}
    now = 1_800_000_000.0
    monkeypatch.setattr(rate_limit.time, "time", lambda: now)

    assert client.post("/auth/login", json=body).status_code == 401
    assert client.post("/auth/login", json=body).status_code == 429
    [key] = redis_client.keys("ratelimit:login:*")
    assert 0 < redis_client.ttl(key) <= settings.RATE_LIMIT_LOGIN_WINDOW_SECONDS

    now += settings.RATE_LIMIT_LOGIN_WINDOW_SECONDS
    assert client.post("/auth/login", json=body).status_code == 401


def test_rate_limiting_can_be_disabled(client, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)
    monkeypatch.setattr(settings, "RATE_LIMIT_LOGIN", 1)
    body = {"email": "nobody@example.com", "password": "wrong-password"}

    assert [client.post("/auth/login", json=body).status_code for _ in range(3)] == [401, 401, 401]


def test_api_keeps_working_when_redis_is_down(client, db_session, monkeypatch):
    _, headers, resume, job = setup_pair(client, db_session)
    calls = count_gemini_matches(monkeypatch)
    monkeypatch.setattr(settings, "RATE_LIMIT_AI_GENERATE", 1)
    redis_module.set_redis_client(disconnected_redis())

    first = match(client, headers, resume, job)
    second = match(client, headers, resume, job)

    assert (first.status_code, second.status_code) == (201, 201)
    assert len(calls) == 2
    assert client.get("/health").json() == {"status": "healthy", "redis": "unavailable", "worker": "disabled"}


def test_redis_is_skipped_for_a_while_after_a_failure(monkeypatch):
    server = fakeredis.FakeServer()
    client = fakeredis.FakeRedis(server=server, decode_responses=True)
    redis_module.set_redis_client(client)
    client.set("key", "value")

    server.connected = False
    assert cache.get_value("key") is None

    server.connected = True
    assert cache.get_value("key") is None

    monkeypatch.setattr(redis_module, "_skip_until", 0.0)
    assert cache.get_value("key") == "value"


def test_redis_can_be_disabled(client, monkeypatch):
    monkeypatch.setattr(settings, "REDIS_URL", "")
    redis_module.set_redis_client(None)

    assert client.get("/health").json() == {"status": "healthy", "redis": "disabled", "worker": "disabled"}
    assert cache.get_value("anything") is None
    rate_limit.enforce(rate_limit.login_limit(), "1.2.3.4")


@pytest.mark.parametrize("disabled", ["", None])
def test_empty_redis_url_disables_redis(monkeypatch, disabled):
    monkeypatch.setattr(settings, "REDIS_URL", disabled)

    assert redis_module._create_client() is None


@pytest.mark.parametrize(
    "bad_url",
    ["https://example.upstash.io", "redis-cli --tls -u redis://default:p@example.upstash.io:6379"],
)
def test_malformed_redis_url_disables_redis_instead_of_crashing(client, monkeypatch, caplog, bad_url):
    monkeypatch.setattr(settings, "REDIS_URL", bad_url)
    monkeypatch.setattr(redis_module, "_initialized", False)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["redis"] == "unavailable"
    assert "REDIS_URL is not a valid Redis URL" in caplog.text
    assert cache.get_value("anything") is None
