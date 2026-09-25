"""Document indexing (chunk, embed, store in Qdrant), with the outcome recorded on the document.

`schedule_indexing` queues the work for the Celery worker, or runs it in-process after the response
when the queue is disabled or unreachable. `run_indexing` opens its own database session, so it can
run in either place.
"""
import logging
import time

from fastapi import BackgroundTasks
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.ai.vector_store import delete_document_chunks, upsert_chunks
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.logging import request_id_var
from app.models.index_status import IndexStatus
from app.models.job import Job
from app.models.resume import Resume
from app.services.embeddings import chunk_text, create_embeddings
from app.utils.time import utc_now


logger = logging.getLogger(__name__)

DOCUMENT_MODELS = {"resume": Resume, "job": Job}
MAX_ERROR_CHARACTERS = 500

# After a failed publish, skip the queue for a while instead of making every upload wait on a timeout.
_queue_skip_until = 0.0


class EmptyDocumentError(Exception):
    pass


class TransientIndexingError(Exception):
    """A failure worth retrying (embedding API or vector store temporarily unavailable)."""


def job_to_text(job: Job) -> str:
    return f"{job.title}\n{job.company}\n{job.description}"


def document_text(document: Resume | Job) -> str:
    if isinstance(document, Resume):
        return document.raw_text or ""
    return job_to_text(document)


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


def mark_indexed(document: Resume | Job, chunk_count: int) -> None:
    """Record a successful indexing on an ORM object (the caller commits)."""
    document.index_status = IndexStatus.INDEXED
    document.index_error = None
    document.indexed_at = utc_now()
    document.chunk_count = chunk_count


def _short(error: Exception) -> str:
    message = str(error) or error.__class__.__name__
    return message[:MAX_ERROR_CHARACTERS]


def _set_status(db: Session, model, document_id: int, **values) -> bool:
    """Update the document's status columns; False when the document no longer exists."""
    result = db.execute(update(model).where(model.id == document_id).values(**values))
    db.commit()
    return result.rowcount > 0


def run_indexing(document_type: str, document_id: int, *, final_attempt: bool = True) -> None:
    """Index one document and record the outcome on it.

    Raises TransientIndexingError when the attempt failed for a retryable reason and
    `final_attempt` is False; the caller (the Celery task) schedules the retry.
    """
    model = DOCUMENT_MODELS[document_type]
    with SessionLocal() as db:
        document = db.get(model, document_id)
        if document is None:
            logger.info("Skipped indexing %s %s: it was deleted", document_type, document_id)
            return
        user_id, text = document.user_id, document_text(document)
        _set_status(db, model, document_id, index_status=IndexStatus.PROCESSING)

        try:
            chunk_count, _ = index_document(
                user_id=user_id, document_type=document_type, document_id=document_id, text=text
            )
        except EmptyDocumentError as error:
            _set_status(db, model, document_id, index_status=IndexStatus.FAILED, index_error=_short(error))
            return
        except Exception as error:
            if final_attempt:
                logger.exception("Gave up indexing %s %s", document_type, document_id)
                _set_status(db, model, document_id, index_status=IndexStatus.FAILED, index_error=_short(error))
                return
            logger.warning("Indexing %s %s failed, will retry: %s", document_type, document_id, error)
            _set_status(
                db, model, document_id,
                index_status=IndexStatus.QUEUED, index_error=f"Retrying after an error: {_short(error)}",
            )
            raise TransientIndexingError(str(error)) from error

        still_exists = _set_status(
            db, model, document_id,
            index_status=IndexStatus.INDEXED, index_error=None, indexed_at=utc_now(), chunk_count=chunk_count,
        )
        if not still_exists:
            # Deleted while it was being embedded: don't leave orphaned vectors behind.
            remove_document_from_index(user_id=user_id, document_type=document_type, document_id=document_id)


def run_indexing_safely(document_type: str, document_id: int) -> None:
    """In-process fallback: a single attempt whose failures never reach the original request."""
    try:
        run_indexing(document_type, document_id, final_attempt=True)
    except Exception:
        logger.exception("Failed to index %s %s", document_type, document_id)


def schedule_indexing(
    db: Session,
    document: Resume | Job,
    background_tasks: BackgroundTasks,
) -> None:
    """Mark a freshly committed document as queued and hand it to the worker (or the fallback)."""
    if not settings.AUTO_INDEX_DOCUMENTS:
        return

    document_type = "resume" if isinstance(document, Resume) else "job"
    document.index_status = IndexStatus.QUEUED
    document.index_error = None
    db.commit()

    global _queue_skip_until
    if settings.TASK_QUEUE_ENABLED and time.monotonic() >= _queue_skip_until:
        # Imported here: the worker module imports this one.
        from app.worker.tasks import index_document_task

        try:
            index_document_task.apply_async(
                args=(document_type, document.id),
                headers={"request_id": request_id_var.get()},
                retry=False,
            )
            return
        except Exception as error:
            _queue_skip_until = time.monotonic() + settings.REDIS_RETRY_AFTER_SECONDS
            logger.warning(
                "Task queue unavailable (%s); indexing in-process for the next %ss",
                error,
                settings.REDIS_RETRY_AFTER_SECONDS,
            )

    background_tasks.add_task(run_indexing_safely, document_type, document.id)


def remove_document_from_index(*, user_id: int, document_type: str, document_id: int) -> None:
    """Best-effort vector cleanup after a document is deleted from the database."""
    try:
        delete_document_chunks(user_id, document_type, document_id)
    except Exception:
        logger.exception("Failed to remove %s %s from the vector index", document_type, document_id)
