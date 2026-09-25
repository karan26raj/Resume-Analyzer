from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column


class IndexStatus(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


class IndexStatusMixin:
    index_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=IndexStatus.PENDING, server_default=IndexStatus.PENDING
    )
    index_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    chunk_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
