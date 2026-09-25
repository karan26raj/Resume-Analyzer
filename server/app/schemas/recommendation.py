from pydantic import BaseModel


class SkillGap(BaseModel):
    skill: str
    count: int


class RecommendationsResponse(BaseModel):
    analysis_count: int
    average_match_score: float | None
    top_missing_skills: list[SkillGap]
    recommendations: list[str]


class JobRecommendation(BaseModel):
    job_id: int
    title: str
    company: str
    similarity: float
    match_score: int
    reason: str
    resume_passage: str
    job_passage: str
    analysis_id: int | None
    analysis_score: int | None


class JobRecommendationsResponse(BaseModel):
    resume_id: int
    recommendations: list[JobRecommendation]
    unindexed_job_ids: list[int]
