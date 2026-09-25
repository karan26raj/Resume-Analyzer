import logging

from app.ai.vector_store import delete_document_chunks, upsert_chunks
from app.models.job import Job
from app.services.embeddings import EmbeddingServiceError, chunk_text, create_embeddings


logger = logging.getLogger(__name__)


class EmptyDocumentError(Exception):
    pass


def job_to_text(job: Job) -> str:
    return f"{job.title}\n{job.company}\n{job.description}"


def index_document(
    *,
    user_id: int,
    document_type: str,
    document_id: int,
    text: str,
) -> tuple[int, None]:
    """Chunk, embed and store a document in Qdrant. Returns (chunk_count, input_tokens)."""
    chunks = chunk_text(text)

    if not chunks:
        raise EmptyDocumentError("Document has no text to embed")

    vectors, tokens = create_embeddings(chunks)

    upsert_chunks(
        user_id=user_id,
        document_type=document_type,
        document_id=document_id,
        chunks=chunks,
        embeddings=vectors,
    )

    return len(chunks), tokens


def index_document_in_background(
    *,
    user_id: int,
    document_type: str,
    document_id: int,
    text: str,
) -> None:
    """Background-task wrapper: indexing failures are logged and never affect the original request."""
    try:
        index_document(
            user_id=user_id,
            document_type=document_type,
            document_id=document_id,
            text=text,
        )
    except EmptyDocumentError:
        logger.info("Skipped indexing empty %s %s", document_type, document_id)
    except EmbeddingServiceError:
        logger.exception("Failed to embed %s %s", document_type, document_id)
    except Exception:
        logger.exception("Failed to index %s %s", document_type, document_id)


def remove_document_from_index(*, user_id: int, document_type: str, document_id: int) -> None:
    """Best-effort vector cleanup after a document is deleted from the database."""
    try:
        delete_document_chunks(user_id, document_type, document_id)
    except Exception:
        logger.exception("Failed to remove %s %s from the vector index", document_type, document_id)
