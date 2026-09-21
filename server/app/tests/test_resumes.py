from io import BytesIO
from pathlib import Path

import pymupdf
import pytest
from docx import Document

from app.core.config import settings
from app.models.resume import Resume


def _auth_headers(client, email: str) -> dict[str, str]:
    password = "password123"
    register_response = client.post(
        "/auth/register", json={"email": email, "password": password}
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/auth/login", json={"email": email, "password": password}
    )
    return {"Authorization": f"Bearer {login_response.json()['access_token']}"}


def _pdf_bytes(text: str) -> bytes:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    content = document.tobytes()
    document.close()
    return content


def _docx_bytes(text: str) -> bytes:
    document = Document()
    document.add_paragraph(text)
    content = BytesIO()
    document.save(content)
    return content.getvalue()


@pytest.fixture
def resume_client(client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    return client


def test_upload_pdf_extracts_text_stores_file_and_metadata(resume_client, db_session):
    headers = _auth_headers(resume_client, "pdf-upload@example.com")

    response = resume_client.post(
        "/resumes/upload",
        headers=headers,
        files={"file": ("resume.pdf", _pdf_bytes("Python developer"), "application/pdf")},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["resume_id"] > 0
    assert data["filename"] == "resume.pdf"
    assert data["text_length"] == len("Python developer")

    resume = db_session.query(Resume).filter(Resume.id == data["resume_id"]).one()
    assert resume.file_type == ".pdf"
    assert resume.raw_text == "Python developer"
    assert resume.file_path
    assert Path(resume.file_path).is_file()


def test_upload_docx_extracts_text_stores_file_and_metadata(resume_client, db_session):
    headers = _auth_headers(resume_client, "docx-upload@example.com")

    response = resume_client.post(
        "/resumes/upload",
        headers=headers,
        files={
            "file": (
                "resume.docx",
                _docx_bytes("Data analyst experience"),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 201
    resume = db_session.query(Resume).filter(Resume.id == response.json()["resume_id"]).one()
    assert resume.file_type == ".docx"
    assert "Data analyst experience" in resume.raw_text


def test_upload_rejects_unsupported_file_type(resume_client):
    headers = _auth_headers(resume_client, "invalid-extension@example.com")

    response = resume_client.post(
        "/resumes/upload",
        headers=headers,
        files={"file": ("resume.txt", b"plain text", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Only PDF and DOCX files are allowed"


def test_upload_rejects_mismatched_file_contents(resume_client):
    headers = _auth_headers(resume_client, "invalid-content@example.com")

    response = resume_client.post(
        "/resumes/upload",
        headers=headers,
        files={"file": ("resume.pdf", b"not a PDF", "application/pdf")},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "The uploaded file is not a valid PDF"


def test_resume_text_is_available_only_to_its_owner(resume_client):
    owner_headers = _auth_headers(resume_client, "resume-owner@example.com")
    upload_response = resume_client.post(
        "/resumes/upload",
        headers=owner_headers,
        files={"file": ("resume.pdf", _pdf_bytes("Private resume"), "application/pdf")},
    )
    resume_id = upload_response.json()["resume_id"]

    owner_response = resume_client.get(f"/resumes/{resume_id}/text", headers=owner_headers)
    assert owner_response.status_code == 200
    assert owner_response.json()["text"] == "Private resume"

    other_headers = _auth_headers(resume_client, "other-user@example.com")
    other_response = resume_client.get(f"/resumes/{resume_id}/text", headers=other_headers)
    assert other_response.status_code == 404
