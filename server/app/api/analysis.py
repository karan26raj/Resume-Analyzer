from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.analysis_result import AnalysisResult
from app.models.job import Job
from app.models.resume import Resume
from app.models.user import User
from app.schemas.analysis import MatchRequest, MatchResponse
from app.services.matching import AnalysisServiceError, generate_match


router = APIRouter(
    prefix="/analysis",
    tags=["Analysis"]
)


@router.get("/")
def get_analysis(
    current_user: User = Depends(get_current_user)
):
    return {
        "message": "Authenticated request",
        "user_id": current_user.id
    }


@router.post("/match", response_model=MatchResponse, status_code=status.HTTP_201_CREATED)
def match_resume_to_job(
    match_request: MatchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    resume = (
        db.query(Resume)
        .filter(Resume.id == match_request.resume_id, Resume.user_id == current_user.id)
        .first()
    )
    if resume is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    if not resume.raw_text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Resume has no extractable text",
        )

    job = (
        db.query(Job)
        .filter(Job.id == match_request.job_id, Job.user_id == current_user.id)
        .first()
    )
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    try:
        match, input_tokens, output_tokens = generate_match(
            resume_text=resume.raw_text,
            job_title=job.title,
            company=job.company,
            job_description=job.description,
        )
    except AnalysisServiceError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error))

    analysis_result = AnalysisResult(
        user_id=current_user.id,
        resume_id=resume.id,
        job_id=job.id,
        model=settings.GEMINI_MODEL,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        **match.model_dump(),
    )
    db.add(analysis_result)
    db.commit()
    db.refresh(analysis_result)
    return analysis_result
