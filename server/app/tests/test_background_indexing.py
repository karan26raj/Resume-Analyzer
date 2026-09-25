import pytest
from celery.exceptions import Retry
from kombu.exceptions import OperationalError

from app.ai.vector_store import get_document_points
from app.core.config import settings
from app.models.index_status import IndexStatus
from app.models.job import Job
from app.services import indexing as indexing_service
from app.services.embeddings import EmbeddingServiceError
from app.tests.helpers import create_job, create_resume, create_user_and_headers, unit_vector
from app.tests.test_resumes import _pdf_bytes
from app.worker import health as worker_health
from app.worker.tasks import index_document_task


@pytest.fixture(autouse=True)
def vector_store(qdrant):
    return qdrant


@pytest.fixture
def fake_embeddings(monkeypatch):
    calls = []

    def create_embeddings(chunks, **kwargs):
        calls.append(chunks)
        return [unit_vector(index % 10) for index, _ in enumerate(chunks)], None

    monkeypatch.setattr(indexing_service, "create_embeddings", create_embeddings)
    return calls


@pytest.fixture
def auto_index(monkeypatch, worker_sessions):
    monkeypatch.setattr(settings, "AUTO_INDEX_DOCUMENTS", True)
    monkeypatch.setattr(indexing_service, "_queue_skip_until", 0.0)


@pytest.fixture
def queue_enabled(monkeypatch, auto_index):
    monkeypatch.setattr(settings, "TASK_QUEUE_ENABLED", True)
    published = []
    original = index_document_task.apply_async

    def apply_async(*args, **kwargs):
        published.append(kwargs.get("args"))
        return original(*args, **kwargs)

    monkeypatch.setattr(index_document_task, "apply_async", apply_async)
    return published


def upload(client, headers, text="Python FastAPI PostgreSQL developer"):
    return client.post(
        "/resumes/upload",
        headers=headers,
        files={"file": ("resume.pdf", _pdf_bytes(text), "application/pdf")},
    )


def reload(db_session, document):
    db_session.expire_all()
    return db_session.get(type(document), document.id)


def test_uploaded_resume_is_indexed_by_the_worker(client, db_session, tmp_path, monkeypatch, queue_enabled, fake_embeddings):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    user, headers = create_user_and_headers(client, db_session)

    response = upload(client, headers)

    assert response.status_code == 201
    resume_id = response.json()["resume_id"]
    assert queue_enabled == [("resume", resume_id)]
    detail = client.get(f"/resumes/{resume_id}", headers=headers).json()
    assert detail["index_status"] == "indexed"
    assert detail["chunk_count"] == 1
    assert detail["indexed_at"] is not None and detail["index_error"] is None
    assert len(get_document_points(user.id, "resume", resume_id)) == 1


def test_created_job_is_indexed_by_the_worker(client, db_session, queue_enabled, fake_embeddings):
    user, headers = create_user_and_headers(client, db_session)

    response = client.post("/jobs", headers=headers, json={"title": "Dev", "company": "Acme", "description": "Python"})

    job_id = response.json()["id"]
    assert queue_enabled == [("job", job_id)]
    assert fake_embeddings == [["Dev Acme Python"]]
    assert client.get(f"/jobs/{job_id}", headers=headers).json()["index_status"] == "indexed"
    assert len(get_document_points(user.id, "job", job_id)) == 1


def test_list_endpoints_include_the_status(client, db_session):
    user, headers = create_user_and_headers(client, db_session)
    create_resume(db_session, user)
    create_job(db_session, user)

    [resume] = client.get("/resumes/", headers=headers).json()
    [job] = client.get("/jobs", headers=headers).json()

    for document in (resume, job):
        assert document["index_status"] == "pending"
        assert {"index_error", "indexed_at", "chunk_count"} <= set(document)


def test_nothing_is_scheduled_when_auto_indexing_is_off(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "AUTO_INDEX_DOCUMENTS", False)
    monkeypatch.setattr(settings, "TASK_QUEUE_ENABLED", True)
    monkeypatch.setattr(index_document_task, "apply_async", lambda *a, **k: pytest.fail("should not publish"))
    _, headers = create_user_and_headers(client, db_session)

    response = client.post("/jobs", headers=headers, json={"title": "Dev", "company": "Acme", "description": "Python"})

    assert response.json()["index_status"] == "pending"


def test_indexes_in_process_when_the_queue_is_disabled(client, db_session, auto_index, fake_embeddings, monkeypatch):
    monkeypatch.setattr(settings, "TASK_QUEUE_ENABLED", False)
    monkeypatch.setattr(index_document_task, "apply_async", lambda *a, **k: pytest.fail("should not publish"))
    _, headers = create_user_and_headers(client, db_session)

    job_id = client.post("/jobs", headers=headers, json={"title": "Dev", "company": "Acme", "description": "Python"}).json()["id"]

    assert client.get(f"/jobs/{job_id}", headers=headers).json()["index_status"] == "indexed"


def test_falls_back_to_in_process_when_the_broker_is_down(client, db_session, auto_index, fake_embeddings, monkeypatch):
    monkeypatch.setattr(settings, "TASK_QUEUE_ENABLED", True)
    attempts = []

    def broker_down(*args, **kwargs):
        attempts.append(kwargs.get("args"))
        raise OperationalError("Timeout connecting to server")

    monkeypatch.setattr(index_document_task, "apply_async", broker_down)
    _, headers = create_user_and_headers(client, db_session)
    body = {"title": "Dev", "company": "Acme", "description": "Python"}

    first = client.post("/jobs", headers=headers, json=body).json()["id"]
    second = client.post("/jobs", headers=headers, json=body).json()["id"]

    assert len(attempts) == 1
    for job_id in (first, second):
        assert client.get(f"/jobs/{job_id}", headers=headers).json()["index_status"] == "indexed"


def test_transient_failure_is_retried_with_backoff(db_session, worker_sessions, monkeypatch):
    user, _ = create_user_and_headers_direct(db_session)
    job = create_job(db_session, user)
    monkeypatch.setattr(indexing_service, "create_embeddings", failing_embeddings)

    with pytest.raises(Retry) as retry:
        index_document_task.apply(args=("job", job.id), retries=1, throw=True)

    assert retry.value.when == settings.INDEX_TASK_RETRY_BASE_SECONDS * 2
    job = reload(db_session, job)
    assert job.index_status == IndexStatus.QUEUED
    assert job.index_error.startswith("Retrying after an error: 503 UNAVAILABLE")


def test_final_attempt_marks_the_document_failed(db_session, worker_sessions, monkeypatch):
    user, _ = create_user_and_headers_direct(db_session)
    job = create_job(db_session, user)
    monkeypatch.setattr(indexing_service, "create_embeddings", failing_embeddings)

    index_document_task.apply(args=("job", job.id), retries=settings.INDEX_TASK_MAX_RETRIES, throw=True)

    job = reload(db_session, job)
    assert job.index_status == IndexStatus.FAILED
    assert job.index_error == "503 UNAVAILABLE"
    assert job.indexed_at is None


def test_successful_retry_clears_the_error(db_session, worker_sessions, fake_embeddings):
    user, _ = create_user_and_headers_direct(db_session)
    job = create_job(db_session, user)
    job.index_status, job.index_error = IndexStatus.QUEUED, "Retrying after an error: 503"
    db_session.commit()

    index_document_task.apply(args=("job", job.id), retries=2, throw=True)

    job = reload(db_session, job)
    assert (job.index_status, job.index_error, job.chunk_count) == (IndexStatus.INDEXED, None, 1)


def test_empty_resume_fails_without_retrying(db_session, worker_sessions, fake_embeddings):
    user, _ = create_user_and_headers_direct(db_session)
    resume = create_resume(db_session, user, raw_text="   ")

    index_document_task.apply(args=("resume", resume.id), retries=0, throw=True)

    resume = reload(db_session, resume)
    assert resume.index_status == IndexStatus.FAILED
    assert resume.index_error == "Document has no text to embed"
    assert fake_embeddings == []


def test_deleted_document_is_skipped(db_session, worker_sessions, fake_embeddings):
    index_document_task.apply(args=("resume", 987654321), throw=True)

    assert fake_embeddings == []


def test_document_deleted_during_indexing_leaves_no_vectors(client, db_session, worker_sessions, monkeypatch):
    user, _ = create_user_and_headers_direct(db_session)
    job = create_job(db_session, user)

    def embed_then_delete(chunks, **kwargs):
        db_session.delete(db_session.get(Job, job.id))
        db_session.commit()
        return [unit_vector(0) for _ in chunks], None

    monkeypatch.setattr(indexing_service, "create_embeddings", embed_then_delete)

    index_document_task.apply(args=("job", job.id), throw=True)

    assert get_document_points(user.id, "job", job.id) == []


def test_manual_reindex_records_the_status(client, db_session, monkeypatch):
    user, headers = create_user_and_headers(client, db_session)
    resume = create_resume(db_session, user)
    monkeypatch.setattr("app.api.embeddings.index_document", lambda **kwargs: (3, None))

    response = client.post("/embeddings/index", headers=headers, json={"resume_id": resume.id})

    assert response.status_code == 201
    resume = reload(db_session, resume)
    assert (resume.index_status, resume.chunk_count) == (IndexStatus.INDEXED, 3)


@pytest.mark.parametrize(
    ("ping", "expected"),
    [(lambda timeout: [{"celery@host": {"ok": "pong"}}], "online"), (lambda timeout: [], "offline")],
)
def test_health_reports_the_worker(client, monkeypatch, ping, expected):
    monkeypatch.setattr(settings, "TASK_QUEUE_ENABLED", True)
    monkeypatch.setattr(worker_health.celery_app.control, "ping", ping)

    assert client.get("/health").json()["worker"] == expected


def test_worker_status_is_cached_briefly(client, monkeypatch):
    monkeypatch.setattr(settings, "TASK_QUEUE_ENABLED", True)
    pings = []
    monkeypatch.setattr(worker_health.celery_app.control, "ping", lambda timeout: pings.append(1) or [])

    client.get("/health")
    client.get("/health")

    assert len(pings) == 1


def test_unreachable_broker_is_reported(client, monkeypatch):
    monkeypatch.setattr(settings, "TASK_QUEUE_ENABLED", True)

    def ping(timeout):
        raise OperationalError("Timeout connecting to server")

    monkeypatch.setattr(worker_health.celery_app.control, "ping", ping)

    assert client.get("/health").json()["worker"] == "unavailable"


def failing_embeddings(chunks, **kwargs):
    raise EmbeddingServiceError("503 UNAVAILABLE")


def create_user_and_headers_direct(db_session):
    from app.models.user import User

    user = User(email=f"worker-{id(db_session)}-{db_session.query(User).count()}@example.com", password_hash="x")
    db_session.add(user)
    db_session.commit()
    return user, None


def test_sync_marks_documents_found_in_qdrant(db_session):
    from app.ai.vector_store import upsert_chunks
    from app.scripts.sync_index_status import sync

    user, _ = create_user_and_headers_direct(db_session)
    in_qdrant = create_resume(db_session, user)
    missing = create_resume(db_session, user)
    lost = create_job(db_session, user)
    lost.index_status = IndexStatus.INDEXED
    db_session.commit()
    upsert_chunks(user_id=user.id, document_type="resume", document_id=in_qdrant.id, chunks=["x"], embeddings=[unit_vector(0)])

    counts = sync(db_session, queue=False)

    assert counts["marked_indexed"] == 1 and counts["marked_pending"] == 1
    assert reload(db_session, in_qdrant).index_status == IndexStatus.INDEXED
    assert reload(db_session, missing).index_status == IndexStatus.PENDING
    assert reload(db_session, lost).index_status == IndexStatus.PENDING


def test_sync_can_queue_unindexed_documents(db_session, monkeypatch):
    from app.scripts.sync_index_status import sync

    user, _ = create_user_and_headers_direct(db_session)
    resume = create_resume(db_session, user)
    job = create_job(db_session, user)
    published = []
    monkeypatch.setattr(settings, "TASK_QUEUE_ENABLED", True)
    monkeypatch.setattr(index_document_task, "apply_async", lambda args: published.append(args))

    counts = sync(db_session, queue=True)

    assert counts["queued"] == 2
    assert sorted(published) == sorted([("resume", resume.id), ("job", job.id)])
    assert reload(db_session, resume).index_status == IndexStatus.QUEUED


def test_sync_indexes_right_away_without_a_task_queue(db_session, worker_sessions, fake_embeddings, monkeypatch):
    from app.scripts.sync_index_status import sync

    monkeypatch.setattr(settings, "TASK_QUEUE_ENABLED", False)
    monkeypatch.setattr(index_document_task, "apply_async", lambda *a, **k: pytest.fail("no worker to publish to"))
    user, _ = create_user_and_headers_direct(db_session)
    resume = create_resume(db_session, user)
    job = create_job(db_session, user)

    counts = sync(db_session, queue=True)

    assert counts["indexed_now"] == 2
    assert reload(db_session, resume).index_status == IndexStatus.INDEXED
    assert reload(db_session, job).index_status == IndexStatus.INDEXED
    assert len(get_document_points(user.id, "job", job.id)) == 1
