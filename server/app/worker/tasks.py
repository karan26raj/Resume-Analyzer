from app.core.config import settings
from app.services.indexing import TransientIndexingError, run_indexing
from app.worker.celery_app import celery_app


@celery_app.task(name="documents.index", bind=True)
def index_document_task(self, document_type: str, document_id: int) -> None:
    final_attempt = self.request.retries >= settings.INDEX_TASK_MAX_RETRIES
    try:
        run_indexing(document_type, document_id, final_attempt=final_attempt)
    except TransientIndexingError as error:
        countdown = settings.INDEX_TASK_RETRY_BASE_SECONDS * 2 ** self.request.retries
        raise self.retry(exc=error, countdown=countdown, max_retries=settings.INDEX_TASK_MAX_RETRIES)
