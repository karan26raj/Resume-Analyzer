import math

import pytest

from app.ai.vector_store import upsert_chunks
from app.services import job_recommendations as service
from app.services.embeddings import EmbeddingServiceError
from app.tests.helpers import (
    create_analysis,
    create_job,
    create_resume,
    create_user_and_headers,
    mixed_vector,
    unit_vector,
)


def index(user_id, document_type, document_id, text, vector):
    upsert_chunks(user_id=user_id, document_type=document_type, document_id=document_id,
                  chunks=[text], embeddings=[vector])


def test_jobs_are_ranked_by_similarity(client, db_session):
    user, headers = create_user_and_headers(client, db_session)
    resume = create_resume(db_session, user)
    close = create_job(db_session, user, title="Close match")
    medium = create_job(db_session, user, title="Medium match")
    far = create_job(db_session, user, title="Far match")
    index(user.id, "resume", resume.id, "Python FastAPI backend", unit_vector(0))
    index(user.id, "job", close.id, "Python backend role", mixed_vector(1.0, 0.2))
    index(user.id, "job", medium.id, "Half related role", mixed_vector(1.0, 1.0))
    index(user.id, "job", far.id, "Unrelated role", unit_vector(1))

    response = client.get("/recommendations/jobs", headers=headers, params={"resume_id": resume.id})

    assert response.status_code == 200
    data = response.json()
    assert data["resume_id"] == resume.id
    assert data["unindexed_job_ids"] == []
    ranked = data["recommendations"]
    assert [item["title"] for item in ranked] == ["Close match", "Medium match", "Far match"]
    assert ranked[0]["similarity"] == pytest.approx(1 / math.sqrt(1.04), abs=1e-3)
    assert ranked[0]["match_score"] == 100
    assert ranked[1]["match_score"] == round(100 * (1 / math.sqrt(2) - 0.70) / 0.15)
    assert ranked[2]["match_score"] == 0
    assert ranked[0]["reason"].startswith("Strong semantic match")
    assert ranked[0]["resume_passage"] == "Python FastAPI backend"
    assert ranked[0]["job_passage"] == "Python backend role"


def test_latest_analysis_score_is_included(client, db_session):
    user, headers = create_user_and_headers(client, db_session)
    resume = create_resume(db_session, user)
    job = create_job(db_session, user)
    create_analysis(db_session, user, resume, job, match_score=40)
    latest = create_analysis(db_session, user, resume, job, match_score=72)
    index(user.id, "resume", resume.id, "resume", unit_vector(0))
    index(user.id, "job", job.id, "job", unit_vector(0))

    [item] = client.get("/recommendations/jobs", headers=headers).json()["recommendations"]

    assert item["analysis_id"] == latest.id
    assert item["analysis_score"] == 72
    assert "latest full analysis for this job scored 72/100" in item["reason"]


def test_defaults_to_most_recent_resume_and_respects_limit(client, db_session):
    user, headers = create_user_and_headers(client, db_session)
    create_resume(db_session, user)
    newest = create_resume(db_session, user)
    index(user.id, "resume", newest.id, "resume", unit_vector(0))
    for position in range(3):
        job = create_job(db_session, user, title=f"Job {position}")
        index(user.id, "job", job.id, "job", unit_vector(0))

    data = client.get("/recommendations/jobs", headers=headers, params={"limit": 2}).json()

    assert data["resume_id"] == newest.id
    assert len(data["recommendations"]) == 2


def test_unindexed_documents_are_indexed_on_the_fly(client, db_session, monkeypatch):
    user, headers = create_user_and_headers(client, db_session)
    resume = create_resume(db_session, user)
    job = create_job(db_session, user)
    indexed = []

    def fake_index_document(*, user_id, document_type, document_id, text):
        indexed.append((document_type, document_id))
        index(user_id, document_type, document_id, text, unit_vector(0))
        return 1, None

    monkeypatch.setattr(service, "index_document", fake_index_document)

    data = client.get("/recommendations/jobs", headers=headers).json()

    assert indexed == [("resume", resume.id), ("job", job.id)]
    assert [item["job_id"] for item in data["recommendations"]] == [job.id]


def test_jobs_that_cannot_be_indexed_are_reported(client, db_session, monkeypatch):
    user, headers = create_user_and_headers(client, db_session)
    resume = create_resume(db_session, user)
    ok_job = create_job(db_session, user, title="Indexed")
    broken_job = create_job(db_session, user, title="Not indexed")
    index(user.id, "resume", resume.id, "resume", unit_vector(0))
    index(user.id, "job", ok_job.id, "job", unit_vector(0))

    def failing_index_document(**kwargs):
        raise EmbeddingServiceError("quota exceeded")

    monkeypatch.setattr(service, "index_document", failing_index_document)

    data = client.get("/recommendations/jobs", headers=headers).json()

    assert [item["job_id"] for item in data["recommendations"]] == [ok_job.id]
    assert data["unindexed_job_ids"] == [broken_job.id]


def test_only_own_jobs_are_recommended(client, db_session):
    user, headers = create_user_and_headers(client, db_session)
    other, _ = create_user_and_headers(client, db_session)
    resume = create_resume(db_session, user)
    own_job = create_job(db_session, user)
    other_job = create_job(db_session, other)
    index(user.id, "resume", resume.id, "resume", unit_vector(0))
    index(user.id, "job", own_job.id, "job", unit_vector(0))
    index(other.id, "job", other_job.id, "job", unit_vector(0))

    data = client.get("/recommendations/jobs", headers=headers).json()

    assert [item["job_id"] for item in data["recommendations"]] == [own_job.id]


def test_stale_vectors_of_deleted_jobs_are_ignored(client, db_session):
    user, headers = create_user_and_headers(client, db_session)
    resume = create_resume(db_session, user)
    index(user.id, "resume", resume.id, "resume", unit_vector(0))
    index(user.id, "job", 987654, "deleted job", unit_vector(0))

    data = client.get("/recommendations/jobs", headers=headers).json()

    assert data["recommendations"] == []


def test_no_jobs_returns_empty_list(client, db_session):
    user, headers = create_user_and_headers(client, db_session)
    create_resume(db_session, user)

    data = client.get("/recommendations/jobs", headers=headers).json()

    assert data["recommendations"] == []


@pytest.mark.parametrize("params", [{}, {"resume_id": 999999}])
def test_missing_resume_returns_404(client, db_session, params):
    _, headers = create_user_and_headers(client, db_session)

    response = client.get("/recommendations/jobs", headers=headers, params=params)

    assert response.status_code == 404


def test_other_users_resume_returns_404(client, db_session):
    owner, _ = create_user_and_headers(client, db_session)
    resume = create_resume(db_session, owner)
    _, other_headers = create_user_and_headers(client, db_session)

    response = client.get("/recommendations/jobs", headers=other_headers, params={"resume_id": resume.id})

    assert response.status_code == 404


def test_empty_resume_returns_422(client, db_session):
    user, headers = create_user_and_headers(client, db_session)
    create_resume(db_session, user, raw_text="")
    create_job(db_session, user)

    response = client.get("/recommendations/jobs", headers=headers)

    assert response.status_code == 422


def test_resume_indexing_failure_returns_503(client, db_session, monkeypatch):
    user, headers = create_user_and_headers(client, db_session)
    create_resume(db_session, user)
    create_job(db_session, user)

    response = client.get("/recommendations/jobs", headers=headers)

    assert response.status_code == 503
    assert response.json()["code"] == "ai_not_configured"


def test_skill_gap_endpoint_is_unchanged(client, db_session):
    _, headers = create_user_and_headers(client, db_session)

    data = client.get("/recommendations", headers=headers).json()

    assert set(data) == {"analysis_count", "average_match_score", "top_missing_skills", "recommendations"}
