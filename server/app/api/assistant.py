from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from app.api.rate_limit import ai_generate_limit, limit_per_user
from app.core.database import get_db

from app.models.job import Job
from app.models.resume import Resume
from app.models.user import User

from app.schemas.assistant import (
    AssistantQuestionRequest,
    AssistantQuestionResponse,
)

from app.services.rag import (
    ask_question,
    RAGServiceError,
)

router = APIRouter(
    prefix="/assistant",
    tags=["Assistant"]
)


@router.post(
    "/ask",
    response_model=AssistantQuestionResponse,
    status_code=status.HTTP_200_OK
)
def assistant_question(
    request: AssistantQuestionRequest,
    current_user: User = Depends(limit_per_user(ai_generate_limit)),
    db: Session = Depends(get_db),
):
    documents: list[tuple[str, int]] = []

    if request.resume_id is not None:
        resume = (
            db.query(Resume)
            .filter(Resume.id == request.resume_id, Resume.user_id == current_user.id)
            .first()
        )
        if resume is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
        documents.append(("resume", resume.id))

    if request.job_id is not None:
        job = (
            db.query(Job)
            .filter(Job.id == request.job_id, Job.user_id == current_user.id)
            .first()
        )
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        documents.append(("job", job.id))

    # Human-readable names let the model cite "your résumé" or the job title instead of IDs.
    document_names = {
        ("resume", resume_id): filename
        for resume_id, filename in db.query(Resume.id, Resume.filename).filter(Resume.user_id == current_user.id)
    }
    document_names.update(
        {
            ("job", job_id): f"{title} at {company}"
            for job_id, title, company in db.query(Job.id, Job.title, Job.company).filter(Job.user_id == current_user.id)
        }
    )

    try:

        answer, sources = ask_question(
            question=request.question,
            user_id=current_user.id,
            limit=request.limit,
            documents=documents or None,
            document_names=document_names,
        )

    except RAGServiceError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(error)
        )

    return {
        "answer": answer,
        "sources": sources
    }
