from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.job import Job
from app.models.user import User
from app.schemas.job import JobCreate, JobResponse
from app.services import cache
from app.services.indexing import remove_document_from_index, schedule_indexing


router = APIRouter(
    prefix="/jobs",
    tags=["Jobs"]
)


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(
    job_data: JobCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = Job(user_id=current_user.id, **job_data.model_dump())
    db.add(job)
    db.commit()
    db.refresh(job)
    cache.invalidate_user_recommendations(current_user.id)
    schedule_indexing(db, job, background_tasks)

    return job


@router.get("", response_model=list[JobResponse])
def get_jobs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(Job)
        .filter(Job.user_id == current_user.id)
        .order_by(Job.id.desc())
        .all()
    )


def _get_owned_job(job_id: int, user_id: int, db: Session) -> Job:
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == user_id).first()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    return job


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _get_owned_job(job_id, current_user.id, db)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = _get_owned_job(job_id, current_user.id, db)
    db.delete(job)
    db.commit()
    cache.invalidate_job(current_user.id, job_id)

    remove_document_from_index(
        user_id=current_user.id,
        document_type="job",
        document_id=job_id,
    )
