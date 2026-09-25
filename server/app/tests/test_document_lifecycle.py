from pathlib import Path

import pymupdf

from app.ai.vector_store import search_chunks, upsert_chunks
from app.api import jobs as jobs_api
from app.api import resumes as resumes_api
from app.core.config import settings
from app.models.analysis_result import AnalysisResult
from app.models.resume import Resume
from app.tests.helpers import (
    create_analysis,
    create_job,
    create_resume,
    create_user_and_headers,
    unit_vector,
)


def _pdf_bytes(text: str) -> bytes:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    content = document.tobytes()
    document.close()
    return content


def test_delete_job_cascades_analyses_and_removes_vectors(client, db_session):
    user, headers = create_user_and_headers(client, db_session)
    resume = create_resume(db_session, user)
    job = create_job(db_session, user)
    analysis = create_analysis(db_session, user, resume, job)
    analysis_id = analysis.id
    upsert_chunks(
        user_id=user.id, document_type="job", document_id=job.id,
        chunks=["job chunk"], embeddings=[unit_vector(0)],
    )

    response = client.delete(f"/jobs/{job.id}", headers=headers)

    assert response.status_code == 204
    db_session.expire_all()
    assert db_session.query(AnalysisResult).filter(AnalysisResult.id == analysis_id).first() is None
    assert search_chunks(unit_vector(0), user_id=user.id, limit=10) == []


def test_delete_resume_removes_file_analyses_and_vectors(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    user, headers = create_user_and_headers(client, db_session)

    upload_response = client.post(
        "/resumes/upload",
        headers=headers,
        files={"file": ("resume.pdf", _pdf_bytes("Python developer"), "application/pdf")},
    )
    resume_id = upload_response.json()["resume_id"]
    resume = db_session.query(Resume).filter(Resume.id == resume_id).one()
    stored_file = Path(resume.file_path)
    assert stored_file.is_file()

    job = create_job(db_session, user)
    analysis_id = create_analysis(db_session, user, resume, job).id
    upsert_chunks(
        user_id=user.id, document_type="resume", document_id=resume_id,
        chunks=["resume chunk"], embeddings=[unit_vector(0)],
    )

    response = client.delete(f"/resumes/{resume_id}", headers=headers)

    assert response.status_code == 204
    assert not stored_file.exists()
    db_session.expire_all()
    assert db_session.query(AnalysisResult).filter(AnalysisResult.id == analysis_id).first() is None
    assert search_chunks(unit_vector(0), user_id=user.id, limit=10) == []
    assert client.get(f"/resumes/{resume_id}", headers=headers).status_code == 404


def test_delete_resume_never_touches_files_outside_upload_dir(client, db_session, tmp_path, monkeypatch):
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_dir))
    outside_file = tmp_path / "important.txt"
    outside_file.write_text("keep me")

    user, headers = create_user_and_headers(client, db_session)
    resume = create_resume(db_session, user)
    resume.file_path = str(outside_file)
    db_session.commit()

    response = client.delete(f"/resumes/{resume.id}", headers=headers)

    assert response.status_code == 204
    assert outside_file.read_text() == "keep me"


def test_delete_resume_of_another_user_returns_404(client, db_session):
    owner, _ = create_user_and_headers(client, db_session)
    resume = create_resume(db_session, owner)
    _, other_headers = create_user_and_headers(client, db_session)

    response = client.delete(f"/resumes/{resume.id}", headers=other_headers)

    assert response.status_code == 404


def test_get_resume_does_not_expose_file_path(client, db_session):
    user, headers = create_user_and_headers(client, db_session)
    resume = create_resume(db_session, user)

    response = client.get(f"/resumes/{resume.id}", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == resume.id
    assert "file_path" not in data
    assert "updated_at" in data


def test_upload_schedules_indexing_when_enabled(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "AUTO_INDEX_DOCUMENTS", True)
    calls = []
    monkeypatch.setattr(resumes_api, "index_document_in_background", lambda **kwargs: calls.append(kwargs))
    user, headers = create_user_and_headers(client, db_session)

    response = client.post(
        "/resumes/upload",
        headers=headers,
        files={"file": ("resume.pdf", _pdf_bytes("Python developer"), "application/pdf")},
    )

    assert response.status_code == 201
    assert calls == [
        {
            "user_id": user.id,
            "document_type": "resume",
            "document_id": response.json()["resume_id"],
            "text": "Python developer",
        }
    ]


def test_create_job_schedules_indexing_when_enabled(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "AUTO_INDEX_DOCUMENTS", True)
    calls = []
    monkeypatch.setattr(jobs_api, "index_document_in_background", lambda **kwargs: calls.append(kwargs))
    user, headers = create_user_and_headers(client, db_session)

    response = client.post(
        "/jobs",
        headers=headers,
        json={"title": "Dev", "company": "Acme", "description": "Python"},
    )

    assert response.status_code == 201
    assert calls == [
        {
            "user_id": user.id,
            "document_type": "job",
            "document_id": response.json()["id"],
            "text": "Dev\nAcme\nPython",
        }
    ]


def test_background_indexing_failure_does_not_fail_the_request(client, db_session, monkeypatch):
    # Real background task with no Gemini key configured: indexing fails, the request still succeeds.
    monkeypatch.setattr(settings, "AUTO_INDEX_DOCUMENTS", True)
    _, headers = create_user_and_headers(client, db_session)

    response = client.post(
        "/jobs",
        headers=headers,
        json={"title": "Dev", "company": "Acme", "description": "Python"},
    )

    assert response.status_code == 201
