from app.api import assistant as assistant_api
from app.services.rag import RAGServiceError
from app.tests.helpers import create_job, create_resume, create_user_and_headers


def test_assistant_scopes_retrieval_to_owned_documents(client, db_session, monkeypatch):
    user, headers = create_user_and_headers(client, db_session)
    resume = create_resume(db_session, user)
    job = create_job(db_session, user)
    captured = {}

    def fake_ask_question(**kwargs):
        captured.update(kwargs)
        return "answer", [
            {"document_type": "resume", "document_id": resume.id, "chunk_index": 0, "score": 0.9}
        ]

    monkeypatch.setattr(assistant_api, "ask_question", fake_ask_question)

    response = client.post(
        "/assistant/ask",
        headers=headers,
        json={"question": "How do I fit?", "resume_id": resume.id, "job_id": job.id},
    )

    assert response.status_code == 200
    assert response.json()["answer"] == "answer"
    assert captured["documents"] == [("resume", resume.id), ("job", job.id)]
    assert captured["user_id"] == user.id
    assert captured["document_names"][("resume", resume.id)] == resume.filename
    assert captured["document_names"][("job", job.id)] == f"{job.title} at {job.company}"


def test_assistant_document_names_only_include_own_documents(client, db_session, monkeypatch):
    _, headers = create_user_and_headers(client, db_session)
    other, _ = create_user_and_headers(client, db_session)
    other_resume = create_resume(db_session, other)
    captured = {}

    def fake_ask_question(**kwargs):
        captured.update(kwargs)
        return "answer", []

    monkeypatch.setattr(assistant_api, "ask_question", fake_ask_question)

    client.post("/assistant/ask", headers=headers, json={"question": "Hi"})

    assert ("resume", other_resume.id) not in captured["document_names"]


def test_assistant_without_scope_searches_all_documents(client, db_session, monkeypatch):
    _, headers = create_user_and_headers(client, db_session)
    captured = {}

    def fake_ask_question(**kwargs):
        captured.update(kwargs)
        return "answer", []

    monkeypatch.setattr(assistant_api, "ask_question", fake_ask_question)

    response = client.post("/assistant/ask", headers=headers, json={"question": "Hi"})

    assert response.status_code == 200
    assert captured["documents"] is None


def test_assistant_rejects_documents_of_another_user(client, db_session, monkeypatch):
    owner, _ = create_user_and_headers(client, db_session)
    resume = create_resume(db_session, owner)
    _, other_headers = create_user_and_headers(client, db_session)
    monkeypatch.setattr(
        assistant_api, "ask_question", lambda **kwargs: (_ for _ in ()).throw(AssertionError("not called"))
    )

    response = client.post(
        "/assistant/ask",
        headers=other_headers,
        json={"question": "Hi", "resume_id": resume.id},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Resume not found"


def test_assistant_validates_input(client, db_session):
    _, headers = create_user_and_headers(client, db_session)

    assert client.post("/assistant/ask", headers=headers, json={"question": ""}).status_code == 422
    assert (
        client.post("/assistant/ask", headers=headers, json={"question": "Hi", "limit": 1000}).status_code
        == 422
    )


def test_assistant_returns_502_on_upstream_failure(client, db_session, monkeypatch):
    _, headers = create_user_and_headers(client, db_session)

    def failing_ask_question(**kwargs):
        raise RAGServiceError("Gemini response failed: quota")

    monkeypatch.setattr(assistant_api, "ask_question", failing_ask_question)

    response = client.post("/assistant/ask", headers=headers, json={"question": "Hi"})

    assert response.status_code == 502
