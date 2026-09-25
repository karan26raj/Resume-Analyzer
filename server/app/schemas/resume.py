from datetime import datetime

from pydantic import BaseModel


class ResumeResponse(BaseModel):
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
