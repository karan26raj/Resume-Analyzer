"""Reconcile each document's index_status with what is actually in Qdrant (phase 15).

Documents created before status tracking start as "pending". Run from the server directory:

    python -m app.scripts.sync_index_status           # mark documents found in Qdrant as indexed
    python -m app.scripts.sync_index_status --queue   # ...and queue every document that isn't indexed

Queued documents are picked up by the Celery worker, so start it first when using --queue.
"""
import argparse
from collections import defaultdict

from sqlalchemy.orm import Session

from app.ai.vector_store import indexed_document_ids
from app.core.database import SessionLocal
from app.models.index_status import IndexStatus
from app.services.indexing import DOCUMENT_MODELS


def sync(db: Session, *, queue: bool) -> dict[str, int]:
    counts = defaultdict(int)
    to_queue: list[tuple[str, int]] = []

    for document_type, model in DOCUMENT_MODELS.items():
        documents = db.query(model).all()
        by_user = defaultdict(list)
        for document in documents:
            by_user[document.user_id].append(document)

        for user_id, user_documents in by_user.items():
            in_qdrant = indexed_document_ids(user_id, document_type)
            for document in user_documents:
                if document.id in in_qdrant:
                    if document.index_status != IndexStatus.INDEXED:
                        document.index_status = IndexStatus.INDEXED
                        document.index_error = None
                        counts["marked_indexed"] += 1
                    counts["indexed"] += 1
                    continue

                counts["not_indexed"] += 1
                if queue:
                    document.index_status = IndexStatus.QUEUED
                    document.index_error = None
                    to_queue.append((document_type, document.id))
                elif document.index_status == IndexStatus.INDEXED:
                    # Marked indexed, but its vectors are gone (e.g. the Qdrant volume was reset).
                    document.index_status = IndexStatus.PENDING
                    counts["marked_pending"] += 1

    db.commit()

    if to_queue:
        from app.worker.tasks import index_document_task

        for document_type, document_id in to_queue:
            index_document_task.apply_async(args=(document_type, document_id))
        counts["queued"] = len(to_queue)

    return dict(counts)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--queue", action="store_true", help="queue every document that isn't indexed")
    args = parser.parse_args()

    with SessionLocal() as db:
        counts = sync(db, queue=args.queue)

    print(
        f"{counts.get('indexed', 0)} indexed ({counts.get('marked_indexed', 0)} newly marked), "
        f"{counts.get('not_indexed', 0)} not indexed, "
        f"{counts.get('queued', 0)} queued, {counts.get('marked_pending', 0)} reset to pending"
    )


if __name__ == "__main__":
    main()
