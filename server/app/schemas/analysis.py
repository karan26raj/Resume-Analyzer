from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


RequirementCategory = Literal["skill", "experience", "education"]
RequirementImportance = Literal["required", "preferred"]
RequirementStatus = Literal["met", "partial", "missing"]


class MatchRequest(BaseModel):
    resume_id: int = Field(gt=0)
    job_id: int = Field(gt=0)


class RequirementAssessment(BaseModel):
    """One job requirement judged against the resume (Gemini output, phase 13)."""

    model_config = ConfigDict(extra="forbid")

    requirement: str = Field(min_length=1, max_length=120)
    category: RequirementCategory
    importance: RequirementImportance
    status: RequirementStatus
    # Short verbatim quote from the resume; empty when the requirement is missing.
    evidence: str = Field(max_length=400)


class LLMMatchOutput(BaseModel):
    """What Gemini returns. The match score is NOT asked of the model - it is computed in code."""

    model_config = ConfigDict(extra="forbid")

    requirements: list[RequirementAssessment] = Field(max_length=30)
    strengths: list[str]
    weaknesses: list[str]
    recommendations: list[str]


class RequirementResult(RequirementAssessment):
    """A requirement after server-side verification of its evidence."""

    evidence_verified: bool
    # The model's own verdict before verification; differs from `status` when it was downgraded.
    model_status: RequirementStatus


class ScoreComponent(BaseModel):
    name: Literal["skills", "experience", "education", "semantic"]
    score: float | None
    weight: float
    effective_weight: float
    detail: str


class ScoreBreakdown(BaseModel):
    method: str
    components: list[ScoreComponent]


class RetrievedPassage(BaseModel):
    chunk_index: int
    content: str
    score: float


class MatchOutput(BaseModel):
    """The analysis fields every client relies on (unchanged since the first version)."""

    model_config = ConfigDict(extra="forbid")

    match_score: int = Field(ge=0, le=100)
    matched_skills: list[str]
    missing_skills: list[str]
    strengths: list[str]
    weaknesses: list[str]
    recommendations: list[str]


class MatchResponse(MatchOutput):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: int
    resume_id: int
    job_id: int
    model: str
    input_tokens: int | None
    output_tokens: int | None
    created_at: datetime

    # Added in phases 9-13; null for analyses created before them.
    requirements: list[RequirementResult] | None = None
    score_breakdown: ScoreBreakdown | None = None
    semantic_similarity: float | None = None
    retrieved_evidence: list[RetrievedPassage] | None = None
