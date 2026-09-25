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

_queue_skip_until = 0.0


class EmptyDocumentError(Exception):
    pass


class TransientIndexingError(Exception):
    pass


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
    document.index_status = IndexStatus.INDEXED
    document.index_error = None
    document.indexed_at = utc_now()
    document.chunk_count = chunk_count


def _short(error: Exception) -> str:
    message = str(error) or error.__class__.__name__
    return message[:MAX_ERROR_CHARACTERS]


def _set_status(db: Session, model, document_id: int, **values) -> bool:
    result = db.execute(update(model).where(model.id == document_id).values(**values))
    db.commit()
    return result.rowcount > 0


def run_indexing(document_type: str, document_id: int, *, final_attempt: bool = True) -> None:
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
            remove_document_from_index(user_id=user_id, document_type=document_type, document_id=document_id)


def run_indexing_safely(document_type: str, document_id: int) -> None:
    try:
        run_indexing(document_type, document_id, final_attempt=True)
    except Exception:
        logger.exception("Failed to index %s %s", document_type, document_id)


def schedule_indexing(
    db: Session,
    document: Resume | Job,
    background_tasks: BackgroundTasks,
) -> None:
    if not settings.AUTO_INDEX_DOCUMENTS:
        return

    document_type = "resume" if isinstance(document, Resume) else "job"
    document.index_status = IndexStatus.QUEUED
    document.index_error = None
    db.commit()

    global _queue_skip_until
    if settings.TASK_QUEUE_ENABLED and time.monotonic() >= _queue_skip_until:
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
    try:
        delete_document_chunks(user_id, document_type, document_id)
    except Exception:
        logger.exception("Failed to remove %s %s from the vector index", document_type, document_id)
