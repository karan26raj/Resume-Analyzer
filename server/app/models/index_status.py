from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column


class IndexStatus(StrEnum):
    """Where a document is in the embedding pipeline."""

    PENDING = "pending"        # not scheduled (or created before status tracking existed)
    QUEUED = "queued"          # waiting for a worker, or waiting to retry
    PROCESSING = "processing"  # a worker is chunking and embedding it
    INDEXED = "indexed"        # its vectors are in Qdrant
    FAILED = "failed"          # gave up; index_error says why


class IndexStatusMixin:
    index_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=IndexStatus.PENDING, server_default=IndexStatus.PENDING
    )
    index_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    chunk_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
