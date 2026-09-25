import uuid

from app.core.config import settings
from app.models.analysis_result import AnalysisResult
from app.models.job import Job
from app.models.resume import Resume
from app.models.user import User


def create_user_and_headers(client, db_session) -> tuple[User, dict[str, str]]:
    email = f"user-{uuid.uuid4()}@example.com"
    password = "password123"

    register_response = client.post(
        "/auth/register", json={"email": email, "password": password}
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/auth/login", json={"email": email, "password": password}
    )
    assert login_response.status_code == 200

    user = db_session.query(User).filter(User.email == email).one()
    return user, {"Authorization": f"Bearer {login_response.json()['access_token']}"}


def create_resume(db_session, user: User, raw_text: str = "Python FastAPI PostgreSQL") -> Resume:
    resume = Resume(
        user_id=user.id,
        filename="resume.pdf",
        file_type=".pdf",
        file_path="uploads/resume.pdf",
        raw_text=raw_text,
    )
    db_session.add(resume)
    db_session.commit()
    db_session.refresh(resume)
    return resume


def create_job(db_session, user: User, title: str = "Backend Developer") -> Job:
    job = Job(
        user_id=user.id,
        title=title,
        company="Example",
        description="Python, FastAPI, PostgreSQL, Docker and AWS experience required.",
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


def create_analysis(
    db_session,
    user: User,
    resume: Resume,
    job: Job,
    *,
    match_score: int = 70,
    missing_skills: list[str] | None = None,
    recommendations: list[str] | None = None,
) -> AnalysisResult:
    analysis = AnalysisResult(
        user_id=user.id,
        resume_id=resume.id,
        job_id=job.id,
        match_score=match_score,
        matched_skills=["Python"],
        missing_skills=missing_skills if missing_skills is not None else ["Docker"],
        strengths=["Backend experience"],
        weaknesses=["No cloud experience"],
        recommendations=recommendations if recommendations is not None else ["Learn Docker"],
        model=settings.GEMINI_MODEL,
    )
    db_session.add(analysis)
    db_session.commit()
    db_session.refresh(analysis)
    return analysis


def unit_vector(index: int) -> list[float]:
    vector = [0.0] * settings.EMBEDDING_DIMENSIONS
    vector[index] = 1.0
    return vector


def mixed_vector(first: float, second: float) -> list[float]:
    vector = [0.0] * settings.EMBEDDING_DIMENSIONS
    vector[0] = first
    vector[1] = second
    return vector
