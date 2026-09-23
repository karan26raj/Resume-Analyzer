from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class EmbeddingIndexRequest(BaseModel):
    resume_id: int | None = Field(default=None, gt=0)
    job_id: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def exactly_one_document(self):
        if (self.resume_id is None) == (self.job_id is None):
            raise ValueError("Provide exactly one of resume_id or job_id")
        return self


class EmbeddingIndexResponse(BaseModel):
    document_type: Literal["resume", "job"]
    document_id: int
    chunk_count: int
    model: str
    input_tokens: int | None


class EmbeddingSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=5_000)
    document_type: Literal["resume", "job"] | None = None
    limit: int = Field(default=5, ge=1, le=20)


class EmbeddingSearchResult(BaseModel):
    chunk_id: int
    document_type: str
    resume_id: int | None
    job_id: int | None
    chunk_index: int
    content: str
    score: float
    metadata: dict
    created_at: datetime | None=None
