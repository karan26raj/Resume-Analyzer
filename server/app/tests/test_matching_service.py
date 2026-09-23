import uuid

from app.api import analysis as analysis_api
from app.models.analysis_result import AnalysisResult
from app.models.job import Job
from app.models.resume import Resume
from app.models.user import User
from app.schemas.analysis import MatchOutput
from app.services.matching import AnalysisServiceError


def _create_user_and_headers(
    client,
    db_session
) -> tuple[User, dict[str, str]]:

    email = (
        f"analysis-user-{uuid.uuid4()}@example.com"
    )

    password = "password123"

    register_response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password,
        },
    )

    assert register_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )

    assert login_response.status_code == 200

    user = (
        db_session.query(User)
        .filter(User.email == email)
        .one()
    )

    return user, {
        "Authorization":
        f"Bearer {login_response.json()['access_token']}"
    }


def _create_resume_and_job(
    db_session,
    user: User,
    raw_text: str = "Python FastAPI PostgreSQL"
):

    resume = Resume(
        user_id=user.id,
        filename="resume.pdf",
        file_type=".pdf",
        file_path="uploads/resume.pdf",
        raw_text=raw_text,
    )

    job = Job(
        user_id=user.id,
        title="Backend Developer",
        company="Example",
        description=(
            "Python, FastAPI, PostgreSQL, "
            "Docker and AWS experience required."
        ),
    )

    db_session.add_all([resume, job])

    db_session.commit()

    db_session.refresh(resume)
    db_session.refresh(job)

    return resume, job


def test_match_creates_and_stores_structured_analysis(
    client,
    db_session,
    monkeypatch,
):

    user, headers = (
        _create_user_and_headers(
            client,
            db_session
        )
    )

    resume, job = (
        _create_resume_and_job(
            db_session,
            user
        )
    )

    def fake_generate_match(**kwargs):

        return (
            MatchOutput(
                match_score=78,
                matched_skills=[
                    "Python",
                    "FastAPI",
                    "PostgreSQL",
                ],
                missing_skills=[
                    "Docker",
                    "AWS",
                ],
                strengths=[
                    "Relevant backend experience"
                ],
                weaknesses=[
                    "No cloud deployment evidence"
                ],
                recommendations=[
                    "Add cloud deployment experience"
                ],
            ),
            None,
            None,
        )

    monkeypatch.setattr(
        analysis_api,
        "generate_match",
        fake_generate_match,
    )

    response = client.post(
        "/analysis/match",
        headers=headers,
        json={
            "resume_id": resume.id,
            "job_id": job.id,
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["match_score"] == 78

    assert data["matched_skills"] == [
        "Python",
        "FastAPI",
        "PostgreSQL",
    ]

    assert data["missing_skills"] == [
        "Docker",
        "AWS",
    ]

    stored_result = (
        db_session.query(AnalysisResult)
        .filter(
            AnalysisResult.id == data["id"]
        )
        .one()
    )

    assert stored_result.resume_id == resume.id
    assert stored_result.job_id == job.id
    assert stored_result.match_score == 78


def test_match_rejects_resume_or_job_not_owned_by_current_user(
    client,
    db_session,
    monkeypatch,
):

    owner, _ = (
        _create_user_and_headers(
            client,
            db_session
        )
    )

    resume, job = (
        _create_resume_and_job(
            db_session,
            owner
        )
    )

    _, other_headers = (
        _create_user_and_headers(
            client,
            db_session
        )
    )

    monkeypatch.setattr(
        analysis_api,
        "generate_match",
        lambda **kwargs: (
            _ for _ in ()
        ).throw(
            AssertionError(
                "Gemini must not be called"
            )
        ),
    )

    response = client.post(
        "/analysis/match",
        headers=other_headers,
        json={
            "resume_id": resume.id,
            "job_id": job.id,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Resume not found"


def test_match_rejects_resume_without_extracted_text(
    client,
    db_session,
    monkeypatch,
):

    user, headers = (
        _create_user_and_headers(
            client,
            db_session
        )
    )

    resume, job = (
        _create_resume_and_job(
            db_session,
            user,
            raw_text="",
        )
    )

    response = client.post(
        "/analysis/match",
        headers=headers,
        json={
            "resume_id": resume.id,
            "job_id": job.id,
        },
    )

    assert response.status_code == 422
    assert (
        response.json()["detail"]
        == "Resume has no extractable text"
    )


def test_match_returns_safe_error_when_gemini_call_fails(
    client,
    db_session,
    monkeypatch,
):

    user, headers = (
        _create_user_and_headers(
            client,
            db_session
        )
    )

    resume, job = (
        _create_resume_and_job(
            db_session,
            user
        )
    )

    def fake_generate_match(**kwargs):
        raise AnalysisServiceError(
            "Gemini is temporarily unavailable"
        )

    monkeypatch.setattr(
        analysis_api,
        "generate_match",
        fake_generate_match,
    )

    response = client.post(
        "/analysis/match",
        headers=headers,
        json={
            "resume_id": resume.id,
            "job_id": job.id,
        },
    )

    assert response.status_code == 502

    assert (
        response.json()["detail"]
        == "Gemini is temporarily unavailable"
    )