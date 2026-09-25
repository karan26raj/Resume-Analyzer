from app.models.analysis_result import AnalysisResult
from app.schemas.analysis import LLMMatchOutput, RequirementAssessment
from app.services import analysis as analysis_service
from app.services.matching import AnalysisServiceError
from app.services.retrieval import RetrievedEvidence
from app.tests.helpers import create_job, create_resume, create_user_and_headers


RESUME_TEXT = "Backend engineer. Built REST APIs with Python and FastAPI. Designed PostgreSQL schemas."


def fake_assessment() -> LLMMatchOutput:
    return LLMMatchOutput(
        requirements=[
            RequirementAssessment(
                requirement="Python", category="skill", importance="required",
                status="met", evidence="Built REST APIs with Python and FastAPI",
            ),
            RequirementAssessment(
                requirement="PostgreSQL", category="skill", importance="required",
                status="met", evidence="Designed PostgreSQL schemas",
            ),
            RequirementAssessment(
                requirement="Docker", category="skill", importance="required",
                status="missing", evidence="",
            ),
            RequirementAssessment(
                requirement="AWS", category="skill", importance="preferred",
                status="missing", evidence="",
            ),
        ],
        strengths=["Relevant backend experience"],
        weaknesses=["No cloud deployment evidence"],
        recommendations=["Add cloud deployment experience"],
    )


def use_fake_pipeline(monkeypatch, similarity=0.65, assessment=None):
    monkeypatch.setattr(
        analysis_service,
        "retrieve_resume_evidence",
        lambda **kwargs: RetrievedEvidence(
            passages=[{"chunk_index": 0, "content": RESUME_TEXT, "score": similarity}],
            similarity=similarity,
        ),
    )
    monkeypatch.setattr(
        analysis_service,
        "generate_match",
        lambda **kwargs: (assessment or fake_assessment(), 1000, 250, "gemini-test-model"),
    )


def test_match_creates_and_stores_analysis(client, db_session, monkeypatch):
    user, headers = create_user_and_headers(client, db_session)
    resume = create_resume(db_session, user, raw_text=RESUME_TEXT)
    job = create_job(db_session, user)
    use_fake_pipeline(monkeypatch)

    response = client.post("/analysis/match", headers=headers, json={"resume_id": resume.id, "job_id": job.id})

    assert response.status_code == 201
    data = response.json()
    # Skills: required Python + PostgreSQL met (4/4 weight), required Docker (0/2) and preferred AWS (0/1) missing
    # -> 4 / 7 = 57.1. Semantic: (0.65 - 0.45) / 0.40 = 50.0.
    # Experience and education have no requirements, so skills and semantic share the weight 40:25.
    expected = round(57.1 * 0.40 / 0.65 + 50.0 * 0.25 / 0.65)
    assert data["match_score"] == expected
    assert data["matched_skills"] == ["Python", "PostgreSQL"]
    assert data["missing_skills"] == ["Docker", "AWS"]
    assert data["model"] == "gemini-test-model"
    assert (data["input_tokens"], data["output_tokens"]) == (1000, 250)
    assert data["semantic_similarity"] == 0.65
    assert data["retrieved_evidence"][0]["content"] == RESUME_TEXT
    assert [item["name"] for item in data["score_breakdown"]["components"]] == [
        "skills", "experience", "education", "semantic",
    ]
    assert all(item["evidence_verified"] for item in data["requirements"] if item["status"] == "met")

    stored = db_session.query(AnalysisResult).filter(AnalysisResult.id == data["id"]).one()
    assert stored.match_score == expected
    assert stored.requirements == data["requirements"]
    assert stored.score_breakdown == data["score_breakdown"]


def test_match_response_keeps_every_original_field(client, db_session, monkeypatch):
    # The frontend depends on these fields; later phases may only add to them.
    user, headers = create_user_and_headers(client, db_session)
    resume = create_resume(db_session, user, raw_text=RESUME_TEXT)
    job = create_job(db_session, user)
    use_fake_pipeline(monkeypatch)

    data = client.post("/analysis/match", headers=headers, json={"resume_id": resume.id, "job_id": job.id}).json()

    for field in (
        "id", "resume_id", "job_id", "match_score", "matched_skills", "missing_skills", "strengths",
        "weaknesses", "recommendations", "model", "input_tokens", "output_tokens", "created_at",
    ):
        assert field in data


def test_match_rejects_resume_not_owned(client, db_session, monkeypatch):
    owner, _ = create_user_and_headers(client, db_session)
    resume = create_resume(db_session, owner)
    job = create_job(db_session, owner)
    _, other_headers = create_user_and_headers(client, db_session)
    monkeypatch.setattr(
        analysis_service,
        "generate_match",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("LLM should not be called")),
    )

    response = client.post("/analysis/match", headers=other_headers, json={"resume_id": resume.id, "job_id": job.id})

    assert response.status_code == 404
    assert response.json()["detail"] == "Resume not found"


def test_match_rejects_job_not_owned(client, db_session):
    user, headers = create_user_and_headers(client, db_session)
    resume = create_resume(db_session, user)
    other, _ = create_user_and_headers(client, db_session)
    job = create_job(db_session, other)

    response = client.post("/analysis/match", headers=headers, json={"resume_id": resume.id, "job_id": job.id})

    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"


def test_match_rejects_empty_resume(client, db_session):
    user, headers = create_user_and_headers(client, db_session)
    resume = create_resume(db_session, user, raw_text="")
    job = create_job(db_session, user)

    response = client.post("/analysis/match", headers=headers, json={"resume_id": resume.id, "job_id": job.id})

    assert response.status_code == 422
    assert response.json()["detail"] == "Resume has no extractable text"


def test_match_returns_safe_error_when_gemini_fails(client, db_session, monkeypatch):
    user, headers = create_user_and_headers(client, db_session)
    resume = create_resume(db_session, user, raw_text=RESUME_TEXT)
    job = create_job(db_session, user)
    use_fake_pipeline(monkeypatch)

    def failing_generate_match(**kwargs):
        raise AnalysisServiceError("Gemini is temporarily unavailable")

    monkeypatch.setattr(analysis_service, "generate_match", failing_generate_match)

    response = client.post("/analysis/match", headers=headers, json={"resume_id": resume.id, "job_id": job.id})

    assert response.status_code == 502
    assert response.json()["detail"] == "Gemini is temporarily unavailable"
    assert db_session.query(AnalysisResult).filter(AnalysisResult.resume_id == resume.id).count() == 0


def test_match_returns_502_when_nothing_can_be_scored(client, db_session, monkeypatch):
    user, headers = create_user_and_headers(client, db_session)
    resume = create_resume(db_session, user, raw_text=RESUME_TEXT)
    job = create_job(db_session, user)
    empty = LLMMatchOutput(requirements=[], strengths=[], weaknesses=[], recommendations=[])
    monkeypatch.setattr(
        analysis_service,
        "retrieve_resume_evidence",
        lambda **kwargs: RetrievedEvidence(passages=[], similarity=None),
    )
    monkeypatch.setattr(analysis_service, "generate_match", lambda **kwargs: (empty, None, None, "m"))

    response = client.post("/analysis/match", headers=headers, json={"resume_id": resume.id, "job_id": job.id})

    assert response.status_code == 502
