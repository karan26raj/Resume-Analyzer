from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import rate_limit
from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.job import Job
from app.models.resume import Resume
from app.models.user import User
from app.schemas.rewrite import RewriteRequest, RewriteResponse
from app.services import cache
from app.services.rewrite import RewriteServiceError, rewrite_resume


router = APIRouter(
    prefix="/resumes",
    tags=["Resume Rewriting"]
)


@router.post("/rewrite", response_model=RewriteResponse)
def rewrite_resume_for_job(
    request: RewriteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Suggest truthful rewrites of resume lines tailored to a job (phase 12)."""
    resume = (
        db.query(Resume)
        .filter(Resume.id == request.resume_id, Resume.user_id == current_user.id)
        .first()
    )
    if resume is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    if not resume.raw_text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Resume has no extractable text",
        )

    job = db.query(Job).filter(Job.id == request.job_id, Job.user_id == current_user.id).first()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    cache_key = cache.rewrite_key(current_user.id, resume.id, job.id)
    if not request.force:
        cached = cache.get_json(cache_key)
        if cached is not None:
            return {**cached, "cached": True}

    # Only requests that actually reach Gemini count towards the limit.
    rate_limit.enforce(rate_limit.ai_generate_limit(), f"user:{current_user.id}")

    try:
        result = rewrite_resume(user_id=current_user.id, resume=resume, job=job)
    except RewriteServiceError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error))

    cache.set_json(cache_key, result, settings.CACHE_TTL_REWRITE_SECONDS)
    return result
