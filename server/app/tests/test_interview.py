import json
from types import SimpleNamespace

import pytest
from google.genai import errors as genai_errors

from app.ai import gemini as gemini_module
from app.core.config import settings
from app.schemas.interview import LLMInterviewOutput
from app.services import cache
from app.services.evidence import mentions
from app.services.interview import generate_interview_questions, verify_questions
from app.tests.helpers import create_job, create_resume, create_user_and_headers


RESUME = (
    "Backend engineer. Built REST APIs with Python and FastAPI serving 2M requests per day. "
    "Designed PostgreSQL schemas. Frontend work in React.js with Redux."
)
JOB_TEXT = "Full-stack Developer\nAcme\nWe need React, FastAPI, PostgreSQL and Kubernetes experience."


def question(text="How does X work?", *, evidence="", kind="conceptual", difficulty="medium"):
    return {
        "question": text,
        "type": kind,
        "difficulty": difficulty,
        "what_they_assess": "Understanding of the fundamentals.",
        "answer_tips": ["Point one", "Point two"],
        "resume_evidence": evidence,
    }


def group(technology, count=5, **kwargs):
    return {"technology": technology, "questions": [question(f"{technology} question {i}?", **kwargs) for i in range(count)]}


def output(*groups):
    return LLMInterviewOutput.model_validate({"technologies": list(groups)})


def verify(*groups, resume=RESUME, job=JOB_TEXT):
    return verify_questions(output(*groups), resume, job)


@pytest.mark.parametrize(
    ("term", "text", "expected"),
    [
        ("React", "Built apps with React.js", True),
        ("ReactJS", "React and Redux", True),
        ("Node.js", "NodeJS services", True),
        ("REST APIs", "Designed RESTful API endpoints", True),
        ("CI/CD", "GitHub Actions CI/CD pipelines", True),
        ("Java", "JavaScript only", False),
        ("C#", "C++ and Rust", False),
        ("Kubernetes", "Docker and Compose", False),
        ("Go", "Golang", False),
    ],
)
def test_technology_mentions(term, text, expected):
    assert mentions(term, text) is expected


def test_source_is_decided_from_the_documents():
    kept, skipped = verify(group("FastAPI"), group("Kubernetes"), group("Redux"))

    assert [(item["technology"], item["source"]) for item in kept] == [
        ("FastAPI", "both"),
        ("Kubernetes", "job"),
        ("Redux", "resume"),
    ]
    assert skipped == []


def test_technologies_in_neither_document_are_skipped():
    kept, skipped = verify(group("React"), group("Terraform"))

    assert [item["technology"] for item in kept] == ["React"]
    assert skipped == [{"technology": "Terraform", "reason": "Not mentioned in the job description or your résumé."}]


def test_spelling_variants_are_accepted():
    kept, _ = verify(group("React.js"), group("Postgresql"))

    assert [item["technology"] for item in kept] == ["React.js", "Postgresql"]


def test_duplicate_technologies_are_skipped():
    kept, skipped = verify(group("React"), group("React.js"), group("react"))

    assert [item["technology"] for item in kept] == ["React"]
    assert [item["reason"] for item in skipped] == ["Duplicate of another technology in the list."] * 2


def test_groups_are_capped_at_the_maximum_questions():
    [kept], _ = verify(group("FastAPI", count=7))

    assert len(kept["questions"]) == settings.INTERVIEW_MAX_QUESTIONS


def test_groups_with_too_few_questions_are_skipped():
    kept, skipped = verify(group("FastAPI", count=3), group("React", count=4))

    assert [item["technology"] for item in kept] == ["React"]
    assert skipped == [{"technology": "FastAPI", "reason": "Only 3 usable questions (at least 4 needed)."}]


def test_duplicate_questions_do_not_count():
    repeated = {"technology": "FastAPI", "questions": [question("Same question?")] * 3 + [question("Other?")]}

    kept, skipped = verify(repeated)

    assert kept == []
    assert skipped[0]["reason"] == "Only 2 usable questions (at least 4 needed)."


def test_resume_evidence_is_kept_only_when_it_is_in_the_resume():
    real = "Built REST APIs with Python and FastAPI serving 2M requests per day."
    invented = "Led a team of 12 engineers migrating FastAPI services to Go."
    groups = {"technology": "FastAPI", "questions": [
        question("Q1?", evidence=real, kind="experience"),
        question("Q2?", evidence=invented, kind="experience"),
        question("Q3?"),
        question("Q4?"),
    ]}

    [kept], _ = verify(groups)

    assert [item["resume_evidence"] for item in kept["questions"]] == [real, None, None, None]


def test_number_of_technologies_is_capped(monkeypatch):
    monkeypatch.setattr(settings, "INTERVIEW_MAX_TECHNOLOGIES", 2)

    kept, skipped = verify(group("React"), group("FastAPI"), group("PostgreSQL"))

    assert [item["technology"] for item in kept] == ["React", "FastAPI"]
    assert skipped == [{"technology": "PostgreSQL", "reason": "Only 2 technologies are covered."}]


def test_answer_tips_are_capped():
    many = {"technology": "FastAPI", "questions": [
        {**question(f"Q{i}?"), "answer_tips": [f"Tip {n}" for n in range(7)]} for i in range(4)
    ]}

    [kept], _ = verify(many)

    assert kept["questions"][0]["answer_tips"] == ["Tip 0", "Tip 1", "Tip 2", "Tip 3"]


def test_gemini_schema_has_no_nested_list_limits():
    schema = json.dumps(LLMInterviewOutput.model_json_schema())

    assert "maxItems" not in schema and "minItems" not in schema


def test_blank_tips_are_dropped_and_whitespace_normalised():
    messy = {"technology": "  FastAPI \n", "questions": [
        {**question(f"Q{i}?"), "answer_tips": ["Keep", "  ", "Also keep "]} for i in range(4)
    ]}

    [kept], _ = verify(messy)

    assert kept["technology"] == "FastAPI"
    assert kept["questions"][0]["answer_tips"] == ["Keep", "Also keep"]


class FakeModels:
    def __init__(self, payload=None, error=None, text=None):
        self.payload, self.error, self.text = payload, error, text
        self.calls = []

    def generate_content(self, *, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "config": config})
        if self.error:
            raise self.error
        text = self.text if self.text is not None else json.dumps(self.payload)
        return SimpleNamespace(text=text, usage_metadata=SimpleNamespace(prompt_token_count=900, candidates_token_count=1500))


@pytest.fixture
def fake_gemini(monkeypatch):
    def install(models):
        monkeypatch.setattr(gemini_module, "get_gemini_client", lambda: SimpleNamespace(models=models))
        return models

    return install


def documents():
    resume = SimpleNamespace(id=1, raw_text=RESUME)
    job = SimpleNamespace(
        id=2, title="Full-stack Developer", company="Acme",
        description="We need React, FastAPI, PostgreSQL and Kubernetes experience.",
    )
    return resume, job


def test_service_returns_verified_groups(fake_gemini):
    models = fake_gemini(FakeModels({"technologies": [group("React"), group("Kubernetes"), group("Terraform")]}))
    resume, job = documents()

    result = generate_interview_questions(resume=resume, job=job)

    assert [(t["technology"], t["source"]) for t in result["technologies"]] == [("React", "both"), ("Kubernetes", "job")]
    assert [s["technology"] for s in result["skipped"]] == ["Terraform"]
    assert (result["resume_id"], result["job_id"]) == (1, 2)
    assert (result["input_tokens"], result["output_tokens"]) == (900, 1500)
    call = models.calls[0]
    assert "Kubernetes experience" in call["contents"] and "React.js with Redux" in call["contents"]
    assert "exactly 5 questions (never fewer than 4)" in call["config"].system_instruction
    assert "Never invent experience" in call["config"].system_instruction
    assert call["config"].response_mime_type == "application/json"


def test_service_fails_when_nothing_usable_remains(fake_gemini):
    fake_gemini(FakeModels({"technologies": [group("Terraform")]}))
    resume, job = documents()

    with pytest.raises(Exception, match="No usable interview questions"):
        generate_interview_questions(resume=resume, job=job)


@pytest.mark.parametrize(("text", "message"), [("", "empty response"), ("{not json", "invalid JSON"), ('{"technologies": "x"}', "invalid structured output")])
def test_service_rejects_bad_model_output(fake_gemini, text, message):
    fake_gemini(FakeModels(text=text))
    resume, job = documents()

    with pytest.raises(Exception, match=message):
        generate_interview_questions(resume=resume, job=job)


def setup_pair(client, db_session):
    user, headers = create_user_and_headers(client, db_session)
    resume = create_resume(db_session, user, raw_text=RESUME)
    job = create_job(db_session, user, title="Full-stack Developer")
    job.description = "We need React, FastAPI, PostgreSQL and Kubernetes experience."
    db_session.commit()
    return user, headers, resume, job


def ask(client, headers, resume, job, **extra):
    return client.post("/interview/questions", headers=headers, json={"resume_id": resume.id, "job_id": job.id, **extra})


def test_endpoint_returns_questions_grouped_by_technology(client, db_session, fake_gemini):
    _, headers, resume, job = setup_pair(client, db_session)
    fake_gemini(FakeModels({"technologies": [group("React"), group("FastAPI"), group("Kubernetes")]}))

    response = ask(client, headers, resume, job)

    assert response.status_code == 200
    data = response.json()
    assert data["cached"] is False
    assert [t["technology"] for t in data["technologies"]] == ["React", "FastAPI", "Kubernetes"]
    assert all(4 <= len(t["questions"]) <= 5 for t in data["technologies"])
    first = data["technologies"][0]["questions"][0]
    assert set(first) == {"question", "type", "difficulty", "what_they_assess", "answer_tips", "resume_evidence"}


def test_repeated_request_is_served_from_cache_and_force_regenerates(client, db_session, fake_gemini):
    _, headers, resume, job = setup_pair(client, db_session)
    models = fake_gemini(FakeModels({"technologies": [group("React")]}))

    first = ask(client, headers, resume, job).json()
    second = ask(client, headers, resume, job).json()
    forced = ask(client, headers, resume, job, force=True).json()

    assert (first["cached"], second["cached"], forced["cached"]) == (False, True, False)
    assert second["technologies"] == first["technologies"]
    assert len(models.calls) == 2


def test_deleting_the_job_clears_cached_questions(client, db_session, fake_gemini, redis_client):
    user, headers, resume, job = setup_pair(client, db_session)
    fake_gemini(FakeModels({"technologies": [group("React")]}))
    ask(client, headers, resume, job)
    key = cache.interview_key(user.id, resume.id, job.id)
    assert redis_client.get(key) is not None

    client.delete(f"/jobs/{job.id}", headers=headers)

    assert redis_client.get(key) is None


def test_other_users_documents_are_not_found(client, db_session):
    _, headers, resume, job = setup_pair(client, db_session)
    other, _ = create_user_and_headers(client, db_session)
    other_resume = create_resume(db_session, other)
    other_job = create_job(db_session, other)

    assert ask(client, headers, other_resume, job).status_code == 404
    assert ask(client, headers, resume, other_job).status_code == 404


def test_empty_resume_returns_422(client, db_session):
    user, headers, _, job = setup_pair(client, db_session)
    empty = create_resume(db_session, user, raw_text="")

    assert ask(client, headers, empty, job).status_code == 422


def test_counts_towards_the_ai_rate_limit(client, db_session, fake_gemini, monkeypatch):
    _, headers, resume, job = setup_pair(client, db_session)
    fake_gemini(FakeModels({"technologies": [group("React")]}))
    monkeypatch.setattr(settings, "RATE_LIMIT_AI_GENERATE", 1)

    assert ask(client, headers, resume, job).status_code == 200
    assert ask(client, headers, resume, job).status_code == 200
    assert ask(client, headers, resume, job, force=True).status_code == 429


def test_overloaded_gemini_returns_a_safe_503(client, db_session, fake_gemini):
    _, headers, resume, job = setup_pair(client, db_session)
    error = genai_errors.ServerError(503, {"error": {"code": 503, "message": "overloaded in cluster zz-9", "status": "UNAVAILABLE"}})
    fake_gemini(FakeModels(error=error))

    response = ask(client, headers, resume, job)

    assert response.status_code == 503
    assert response.json()["code"] == "ai_unavailable"
    assert "zz-9" not in response.text


def test_unusable_output_returns_502_with_our_message(client, db_session, fake_gemini):
    _, headers, resume, job = setup_pair(client, db_session)
    fake_gemini(FakeModels({"technologies": [group("Terraform")]}))

    response = ask(client, headers, resume, job)

    assert response.status_code == 502
    assert response.json()["detail"].startswith("No usable interview questions")
