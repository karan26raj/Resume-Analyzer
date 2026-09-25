from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.rate_limit import ai_embed_limit, limit_per_user
from app.core.config import settings
from app.core.database import get_db
from app.core.errors import upstream_failure

from app.models.job import Job
from app.models.resume import Resume
from app.models.user import User

from app.schemas.embedding import (
    EmbeddingIndexRequest,
    EmbeddingIndexResponse,
    EmbeddingSearchRequest,
    EmbeddingSearchResult,
)

from app.services.embeddings import (
    QUERY_TASK_TYPE,
    EmbeddingServiceError,
    create_embeddings,
)
from app.services.indexing import (
    EmptyDocumentError,
    index_document,
    job_to_text,
    mark_indexed,
)

from app.ai.vector_store import search_chunks

router = APIRouter(
    prefix="/embeddings",
    tags=["Embeddings"]
)


@router.post(
    "/index",
    response_model=EmbeddingIndexResponse,
    status_code=status.HTTP_201_CREATED
)
def index_document_endpoint(
    request: EmbeddingIndexRequest,
    current_user: User = Depends(limit_per_user(ai_embed_limit)),
    db: Session = Depends(get_db)
):

    if request.resume_id:

        document = (
            db.query(Resume)
            .filter(
                Resume.id == request.resume_id,
                Resume.user_id == current_user.id
            )
            .first()
        )

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found"
            )

        text = document.raw_text or ""
        document_type = "resume"

    else:

        document = (
            db.query(Job)
            .filter(
                Job.id == request.job_id,
                Job.user_id == current_user.id
            )
            .first()
        )

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )

        text = job_to_text(document)
        document_type = "job"

    try:
        chunk_count, tokens = index_document(
            user_id=current_user.id,
            document_type=document_type,
            document_id=document.id,
            text=text,
        )

    except EmptyDocumentError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error)
        )

    except EmbeddingServiceError as error:
        raise upstream_failure(error)

    mark_indexed(document, chunk_count)
    db.commit()

    return {
        "document_type": document_type,
        "document_id": document.id,
        "chunk_count": chunk_count,
        "model": settings.GEMINI_EMBEDDING_MODEL,
        "input_tokens": tokens,
    }


@router.post(
    "/search",
    response_model=list[EmbeddingSearchResult]
)
def search_embeddings(
    request: EmbeddingSearchRequest,
    current_user: User = Depends(limit_per_user(ai_embed_limit)),
):

    try:
        query_vectors, _ = create_embeddings(
            [request.query],
            task_type=QUERY_TASK_TYPE,
        )

    except EmbeddingServiceError as error:
        raise upstream_failure(error)

    results = search_chunks(
        query_vector=query_vectors[0],
        user_id=current_user.id,
        limit=request.limit,
        document_type=request.document_type,
    )

    return [
        {
            "chunk_id": str(hit.id),
            "document_type": hit.payload["document_type"],
            "resume_id": (
                hit.payload["document_id"]
                if hit.payload["document_type"] == "resume"
                else None
            ),
            "job_id": (
                hit.payload["document_id"]
                if hit.payload["document_type"] == "job"
                else None
            ),
            "chunk_index": hit.payload["chunk_index"],
            "content": hit.payload["content"],
            "score": hit.score,
        }
        for hit in results
    ]
