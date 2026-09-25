from pydantic import BaseModel, ConfigDict, Field


class RewriteRequest(BaseModel):
    resume_id: int = Field(gt=0)
    job_id: int = Field(gt=0)
    # Skip the cache and always generate new suggestions (phase 14).
    force: bool = False


class RewriteSuggestionOutput(BaseModel):
    """One suggestion as returned by Gemini."""

    model_config = ConfigDict(extra="forbid")

    section: str = Field(max_length=80)
    original: str = Field(min_length=1, max_length=800)
    rewritten: str = Field(min_length=1, max_length=800)
    rationale: str = Field(max_length=400)


class LLMRewriteOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    suggestions: list[RewriteSuggestionOutput] = Field(max_length=15)


class RewriteSuggestion(BaseModel):
    section: str
    original: str
    rewritten: str
    rationale: str


class RejectedSuggestion(RewriteSuggestion):
    reason: str
    unsupported_terms: list[str] = []


class RewriteResponse(BaseModel):
    resume_id: int
    job_id: int
    model: str
    input_tokens: int | None
    output_tokens: int | None
    suggestions: list[RewriteSuggestion]
    # Suggestions dropped by the "never invent" guard, with the reason, for transparency.
    rejected: list[RejectedSuggestion]
    # True when these suggestions came from the cache instead of a new Gemini call.
    cached: bool = False
