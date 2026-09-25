"""Resume rewriting that never invents experience."""
import json
from types import SimpleNamespace

import pytest

from app.ai import gemini as gemini_module
from app.core.config import settings
from app.services import rewrite as rewrite_service
from app.services.retrieval import RetrievalError, RetrievedEvidence
from app.services.rewrite import RewriteServiceError, rewrite_resume, validate_suggestions
from app.tests.helpers import create_job, create_resume, create_user_and_headers


RESUME = """Experience
Worked on backend APIs using Python and FastAPI at Northwind Labs.
Wrote tests with pytest and set up Docker builds.
Added Redis caching that cut p95 latency by 40%."""


def suggestion(original, rewritten, section="Experience", rationale="Closer to the job wording"):
    return {"section": section, "original": original, "rewritten": rewritten, "rationale": rationale}


def test_truthful_rephrasing_is_accepted():
    item = suggestion(
        "Worked on backend APIs using Python and FastAPI at Northwind Labs.",
        "Developed backend APIs with Python and FastAPI at Northwind Labs, backed by pytest tests.",
    )

    accepted, rejected = validate_suggestions([item], RESUME)

    assert accepted == [item]
    assert rejected == []


def test_job_vocabulary_the_resume_does_not_contain_is_rejected():
    # This resume never says "REST", so a rewrite may not add it even though the job asks for it.
    item = suggestion(
        "Worked on backend APIs using Python and FastAPI at Northwind Labs.",
        "Built REST APIs with Python and FastAPI at Northwind Labs.",
    )

    _, [rejected] = validate_suggestions([item], RESUME)

    assert rejected["unsupported_terms"] == ["REST"]


def test_rewrite_that_invents_technology_is_rejected():
    item = suggestion(
        "Worked on backend APIs using Python and FastAPI at Northwind Labs.",
        "Built Kubernetes-hosted microservices on AWS using Python and FastAPI.",
    )

    accepted, [rejected] = validate_suggestions([item], RESUME)

    assert accepted == []
    assert rejected["reason"] == "The rewrite adds terms that are not in your résumé."
    assert rejected["unsupported_terms"] == ["Kubernetes-hosted", "AWS"]


def test_rewrite_that_invents_a_metric_is_rejected():
    item = suggestion(
        "Wrote tests with pytest and set up Docker builds.",
        "Raised test coverage to 95% with pytest and Docker builds.",
    )

    _, [rejected] = validate_suggestions([item], RESUME)

    assert rejected["unsupported_terms"] == ["95"]


def test_existing_metrics_may_be_reused():
    item = suggestion(
        "Added Redis caching that cut p95 latency by 40%.",
        "Cut p95 latency by 40% by introducing Redis caching.",
    )

    accepted, _ = validate_suggestions([item], RESUME)

    assert accepted == [item]


def test_original_must_exist_in_the_resume():
    item = suggestion("Led a team of eight engineers.", "Led and mentored a team of engineers.")

    _, [rejected] = validate_suggestions([item], RESUME)

    assert rejected["reason"] == "The original text was not found in your résumé."


def test_unchanged_rewrite_is_rejected():
    line = "Wrote tests with pytest and set up Docker builds."

    _, [rejected] = validate_suggestions([suggestion(line, f"  {line.upper()} ")], RESUME)

    assert rejected["reason"] == "The rewrite does not change the original."


def test_accepted_suggestions_are_capped(monkeypatch):
    monkeypatch.setattr(settings, "MAX_REWRITE_SUGGESTIONS", 1)
    items = [
        suggestion("Wrote tests with pytest and set up Docker builds.", "Set up Docker builds and pytest suites."),
        suggestion("Added Redis caching that cut p95 latency by 40%.", "Cut p95 latency by 40% with Redis caching."),
    ]

    accepted, _ = validate_suggestions(items, RESUME)

    assert len(accepted) == 1


class FakeModels:
    def __init__(self, payload=None, error=None):
        self.payload = payload
        self.error = error
        self.calls = []

    def generate_content(self, *, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "config": config})
        if self.error:
            raise self.error
        return SimpleNamespace(
            text=json.dumps(self.payload) if self.payload is not None else "",
            usage_metadata=SimpleNamespace(prompt_token_count=500, candidates_token_count=120),
        )


@pytest.fixture
def fake_gemini(monkeypatch):
    def install(models):
        monkeypatch.setattr(gemini_module, "get_gemini_client", lambda: SimpleNamespace(models=models))
        return models

    monkeypatch.setattr(
        rewrite_service,
        "retrieve_resume_evidence",
        lambda **kwargs: RetrievedEvidence(
            passages=[{"chunk_index": 0, "content": "Worked on backend APIs", "score": 0.7}], similarity=0.7
        ),
    )
    return install


def _resume_and_job():
    resume = SimpleNamespace(id=1, raw_text=RESUME)
    job = SimpleNamespace(id=2, title="Backend Engineer", company="Acme", description="Python, FastAPI, REST APIs")
    return resume, job


def test_rewrite_resume_splits_accepted_and_rejected(fake_gemini):
    models = fake_gemini(
        FakeModels(
            {
                "suggestions": [
                    suggestion(
                        "Worked on backend APIs using Python and FastAPI at Northwind Labs.",
                        "Built backend APIs with Python and FastAPI at Northwind Labs.",
                    ),
                    suggestion(
                        "Wrote tests with pytest and set up Docker builds.",
                        "Automated Kubernetes deployments and pytest suites.",
                    ),
                ]
            }
        )
    )
    resume, job = _resume_and_job()

    result = rewrite_resume(user_id=1, resume=resume, job=job)

    assert [item["rewritten"] for item in result["suggestions"]] == [
        "Built backend APIs with Python and FastAPI at Northwind Labs."
    ]
    assert [item["unsupported_terms"] for item in result["rejected"]] == [["Kubernetes"]]
    assert (result["input_tokens"], result["output_tokens"]) == (500, 120)
    call = models.calls[0]
    assert "Worked on backend APIs" in call["contents"]           # retrieved passages are in the prompt
    assert "NEVER add a technology" in call["config"].system_instruction
    assert call["config"].response_mime_type == "application/json"


def test_rewrite_continues_without_retrieval(fake_gemini, monkeypatch):
    def failing_retrieval(**kwargs):
        raise RetrievalError("down")

    models = fake_gemini(FakeModels({"suggestions": []}))
    monkeypatch.setattr(rewrite_service, "retrieve_resume_evidence", failing_retrieval)
    resume, job = _resume_and_job()

    result = rewrite_resume(user_id=1, resume=resume, job=job)

    assert result["suggestions"] == []
    assert "(no passages retrieved)" in models.calls[0]["contents"]


@pytest.mark.parametrize(
    ("models", "message"),
    [
        (FakeModels(error=RuntimeError("503 overloaded")), "503 overloaded"),
        (FakeModels(payload=None), "empty response"),
        (FakeModels(payload={"suggestions": [{"section": "x"}]}), "invalid structured output"),
    ],
)
def test_rewrite_errors(fake_gemini, models, message):
    fake_gemini(models)
    resume, job = _resume_and_job()

    with pytest.raises(RewriteServiceError, match=message):
        rewrite_resume(user_id=1, resume=resume, job=job)


def test_rewrite_endpoint(client, db_session, monkeypatch):
    user, headers = create_user_and_headers(client, db_session)
    resume = create_resume(db_session, user, raw_text=RESUME)
    job = create_job(db_session, user)
    captured = {}

    def fake_rewrite(**kwargs):
        captured.update(kwargs)
        return {
            "resume_id": resume.id, "job_id": job.id, "model": "m", "input_tokens": 1, "output_tokens": 2,
            "suggestions": [suggestion("a", "b")], "rejected": [],
        }

    monkeypatch.setattr("app.api.rewrite.rewrite_resume", fake_rewrite)

    response = client.post("/resumes/rewrite", headers=headers, json={"resume_id": resume.id, "job_id": job.id})

    assert response.status_code == 200
    assert response.json()["suggestions"][0]["rewritten"] == "b"
    assert captured["resume"].id == resume.id and captured["job"].id == job.id


def test_rewrite_endpoint_ownership_and_validation(client, db_session):
    user, headers = create_user_and_headers(client, db_session)
    other, _ = create_user_and_headers(client, db_session)
    own_resume = create_resume(db_session, user, raw_text=RESUME)
    empty_resume = create_resume(db_session, user, raw_text="")
    own_job = create_job(db_session, user)
    other_resume = create_resume(db_session, other)
    other_job = create_job(db_session, other)

    def post(resume_id, job_id):
        return client.post("/resumes/rewrite", headers=headers, json={"resume_id": resume_id, "job_id": job_id})

    assert post(other_resume.id, own_job.id).status_code == 404
    assert post(own_resume.id, other_job.id).status_code == 404
    assert post(empty_resume.id, own_job.id).status_code == 422
    assert post(0, own_job.id).status_code == 422


def test_rewrite_endpoint_returns_502_on_gemini_failure(client, db_session, monkeypatch):
    user, headers = create_user_and_headers(client, db_session)
    resume = create_resume(db_session, user, raw_text=RESUME)
    job = create_job(db_session, user)

    def failing_rewrite(**kwargs):
        raise RewriteServiceError("Gemini rewrite failed: 503")

    monkeypatch.setattr("app.api.rewrite.rewrite_resume", failing_rewrite)

    response = client.post("/resumes/rewrite", headers=headers, json={"resume_id": resume.id, "job_id": job.id})

    assert response.status_code == 502
