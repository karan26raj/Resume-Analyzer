from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


QuestionType = Literal["conceptual", "practical", "scenario", "experience"]
Difficulty = Literal["easy", "medium", "hard"]
TechnologySource = Literal["both", "job", "resume"]


class InterviewRequest(BaseModel):
    resume_id: int = Field(gt=0)
    job_id: int = Field(gt=0)
    force: bool = False


class InterviewQuestionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=500)
    type: QuestionType
    difficulty: Difficulty
    what_they_assess: str = Field(max_length=400)
    answer_tips: list[str]
    resume_evidence: str = Field(max_length=400)


class TechnologyQuestionsOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    technology: str = Field(min_length=1, max_length=80)
    questions: list[InterviewQuestionOutput]


class LLMInterviewOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    technologies: list[TechnologyQuestionsOutput]


class InterviewQuestion(BaseModel):
    question: str
    type: QuestionType
    difficulty: Difficulty
    what_they_assess: str
    answer_tips: list[str]
    resume_evidence: str | None = None


class TechnologyQuestions(BaseModel):
    technology: str
    source: TechnologySource
    questions: list[InterviewQuestion]


class SkippedTechnology(BaseModel):
    technology: str
    reason: str


class InterviewPrepResponse(BaseModel):
    resume_id: int
    job_id: int
    model: str
    input_tokens: int | None
    output_tokens: int | None
    technologies: list[TechnologyQuestions]
    skipped: list[SkippedTechnology]
    cached: bool = False
