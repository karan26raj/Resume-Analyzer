from pydantic import BaseModel


class AssistantQuestionRequest(BaseModel):
    question: str
    limit: int = 5


class AssistantSource(BaseModel):
    document_type: str
    document_id: int
    chunk_index: int


class AssistantQuestionResponse(BaseModel):
    answer: str
    sources: list[AssistantSource]