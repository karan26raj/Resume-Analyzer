from datetime import datetime

from pydantic import BaseModel, Field


class JobCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    company: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=10_000)


class JobResponse(BaseModel):
    id: int
    title: str
    company: str
    description: str
    created_at: datetime

    model_config = {"from_attributes": True}
