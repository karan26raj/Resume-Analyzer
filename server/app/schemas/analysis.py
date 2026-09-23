from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MatchRequest(BaseModel):
    resume_id: int = Field(gt=0)
    job_id: int = Field(gt=0)


class MatchOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    match_score: int = Field(ge=0, le=100)
    matched_skills: list[str]
    missing_skills: list[str]
    strengths: list[str]
    weaknesses: list[str]
    recommendations: list[str]


class MatchResponse(MatchOutput):
    id: int
    resume_id: int
    job_id: int
    model: str
    input_tokens: int | None
    output_tokens: int | None
    created_at: datetime

    model_config = {"from_attributes": True}
