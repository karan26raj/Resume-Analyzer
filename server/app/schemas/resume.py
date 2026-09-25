from datetime import datetime

from pydantic import BaseModel


class IndexStatusFields(BaseModel):
    """Where the document is in the embedding pipeline (phase 15)."""

    index_status: str
    index_error: str | None = None
    indexed_at: datetime | None = None
    chunk_count: int | None = None


class ResumeResponse(IndexStatusFields):
    id: int
    filename: str
    file_type: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ResumeDetailResponse(ResumeResponse):
    updated_at: datetime


class ResumeUploadResponse(BaseModel):
    message: str
    resume_id: int
    filename: str
    text_length: int
    index_status: str
