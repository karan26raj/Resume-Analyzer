from pydantic import BaseModel, Field


class AssistantQuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2_000)
    limit: int = Field(default=5, ge=1, le=20)
    resume_id: int | None = Field(default=None, gt=0)
    job_id: int | None = Field(default=None, gt=0)


class AssistantSource(BaseModel):
    document_type: str
    document_id: int
    chunk_index: int
    score: float


class AssistantQuestionResponse(BaseModel):
    answer: str
    sources: list[AssistantSource]
