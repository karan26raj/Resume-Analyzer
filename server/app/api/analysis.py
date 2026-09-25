from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.analysis_result import AnalysisResult
from app.models.job import Job
from app.models.resume import Resume
from app.models.user import User
from app.schemas.analysis import MatchRequest, MatchResponse
from app.services.analysis import run_match_analysis
from app.services.matching import AnalysisServiceError


router = APIRouter(
    prefix="/analysis",
    tags=["Analysis"]
)


@router.get("", response_model=list[MatchResponse])
def list_analyses(
    resume_id: int | None = Query(default=None, gt=0),
    job_id: int | None = Query(default=None, gt=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(AnalysisResult).filter(AnalysisResult.user_id == current_user.id)

    if resume_id is not None:
        query = query.filter(AnalysisResult.resume_id == resume_id)
    if job_id is not None:
        query = query.filter(AnalysisResult.job_id == job_id)

    return query.order_by(AnalysisResult.id.desc()).all()


@router.get("/{analysis_id}", response_model=MatchResponse)
def get_analysis(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    analysis = (
        db.query(AnalysisResult)
        .filter(AnalysisResult.id == analysis_id, AnalysisResult.user_id == current_user.id)
        .first()
    )
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    return analysis


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
        result = run_match_analysis(user_id=current_user.id, resume=resume, job=job)
    except AnalysisServiceError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error))

    analysis_result = AnalysisResult(
        user_id=current_user.id,
        resume_id=resume.id,
        job_id=job.id,
        **result,
    )
    db.add(analysis_result)
    db.commit()
    db.refresh(analysis_result)
    return analysis_result
