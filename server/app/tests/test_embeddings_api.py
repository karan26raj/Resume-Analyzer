from app.ai.qdrant_client import get_collection_name
from app.ai.vector_store import point_id, upsert_chunks
from app.api import embeddings as embeddings_api
from app.services import indexing as indexing_service
from app.tests.helpers import create_job, create_resume, create_user_and_headers, unit_vector


def test_index_job_stores_chunks(client, db_session, qdrant, monkeypatch):
    user, headers = create_user_and_headers(client, db_session)
    job = create_job(db_session, user)
    monkeypatch.setattr(
        indexing_service,
        "create_embeddings",
        lambda chunks: ([unit_vector(index) for index in range(len(chunks))], None),
    )

    response = client.post("/embeddings/index", headers=headers, json={"job_id": job.id})

    assert response.status_code == 201
    assert response.json()["document_type"] == "job"
    assert response.json()["chunk_count"] == 1
    stored = qdrant.retrieve(
        collection_name=get_collection_name(),
        ids=[point_id(user.id, "job", job.id, 0)],
        with_payload=True,
    )
    # chunk_text re-joins words with single spaces.
    assert stored[0].payload["content"].startswith("Backend Developer Example Python")


def test_index_rejects_empty_resume(client, db_session):
    user, headers = create_user_and_headers(client, db_session)
    resume = create_resume(db_session, user, raw_text="")

    response = client.post("/embeddings/index", headers=headers, json={"resume_id": resume.id})

    assert response.status_code == 422
    assert response.json()["detail"] == "Document has no text to embed"


def test_index_returns_503_when_gemini_is_not_configured(client, db_session):
    # conftest leaves GEMINI_API_KEY unset, so embedding can't run at all.
    user, headers = create_user_and_headers(client, db_session)
    resume = create_resume(db_session, user)

    response = client.post("/embeddings/index", headers=headers, json={"resume_id": resume.id})

    assert response.status_code == 503
    assert response.json()["code"] == "ai_not_configured"


def test_search_honours_document_type_and_returns_stable_ids(client, db_session, monkeypatch):
    user, headers = create_user_and_headers(client, db_session)
    upsert_chunks(
        user_id=user.id, document_type="resume", document_id=1,
        chunks=["resume text"], embeddings=[unit_vector(0)],
    )
    upsert_chunks(
        user_id=user.id, document_type="job", document_id=1,
        chunks=["job text"], embeddings=[unit_vector(0)],
    )
    monkeypatch.setattr(
        embeddings_api, "create_embeddings", lambda texts, task_type: ([unit_vector(0)], None)
    )

    response = client.post(
        "/embeddings/search",
        headers=headers,
        json={"query": "python", "document_type": "job"},
    )

    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["job_id"] == 1
    assert results[0]["resume_id"] is None
    assert results[0]["chunk_id"] == point_id(user.id, "job", 1, 0)
