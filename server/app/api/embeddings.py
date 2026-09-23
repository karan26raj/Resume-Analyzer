from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.database import get_db

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
    EmbeddingServiceError,
    chunk_text,
    create_embeddings,
)

from app.ai.vector_store import (
    upsert_chunks,
    search_chunks,
)

router = APIRouter(
    prefix="/embeddings",
    tags=["Embeddings"]
)


@router.post(
    "/index",
    response_model=EmbeddingIndexResponse,
    status_code=status.HTTP_201_CREATED
)
def index_document(
    request: EmbeddingIndexRequest,
    current_user: User = Depends(get_current_user),
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
                status_code=404,
                detail="Resume not found"
            )

        text = document.raw_text or ""
        document_type = "resume"
        document_id = document.id

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
                status_code=404,
                detail="Job not found"
            )

        text = (
            f"{document.title}\n"
            f"{document.company}\n"
            f"{document.description}"
        )

        document_type = "job"
        document_id = document.id

    chunks = chunk_text(text)

    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Document has no text to embed"
        )

    try:
        vectors, tokens = create_embeddings(chunks)

    except EmbeddingServiceError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(error)
        )

    if len(vectors) != len(chunks):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OpenAI returned incomplete embeddings"
        )

    try:

        upsert_chunks(
            user_id=current_user.id,
            document_type=document_type,
            document_id=document_id,
            chunks=chunks,
            embeddings=vectors
        )

    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store vectors in Qdrant: {str(error)}"
        )

    return {
        "document_type": document_type,
        "document_id": document_id,
        "chunk_count": len(chunks),
        "model":settings.GEMINI_EMBEDDING_MODEL,
        "input_tokens": tokens,
    }


@router.post(
    "/search",
    response_model=list[EmbeddingSearchResult]
)
def search_embeddings(
    request: EmbeddingSearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    try:
        query_vectors, _ = create_embeddings(
            [request.query]
        )

    except EmbeddingServiceError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(error)
        )

    try:

        results = search_chunks(
            query_vector=query_vectors[0],
            user_id=current_user.id,
            limit=request.limit
        )

    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vector search failed: {str(error)}"
        )

    response = []

    for hit in results:

        payload = hit.payload

        response.append(
            {
                "chunk_id": hash(str(hit.id)) % 1000000,
                "document_type": payload["document_type"],
                "resume_id": (
                    payload["document_id"]
                    if payload["document_type"] == "resume"
                    else None
                ),
                "job_id": (
                    payload["document_id"]
                    if payload["document_type"] == "job"
                    else None
                ),
                "chunk_index": payload["chunk_index"],
                "content": payload["content"],
                "score": hit.score,
                "metadata": payload,
                "created_at": None,
            }
        )

    return response