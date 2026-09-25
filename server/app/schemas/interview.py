from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


QuestionType = Literal["conceptual", "practical", "scenario", "experience"]
Difficulty = Literal["easy", "medium", "hard"]
TechnologySource = Literal["both", "job", "resume"]


class InterviewRequest(BaseModel):
    resume_id: int = Field(gt=0)
    job_id: int = Field(gt=0)
    # Skip the cache and always generate new questions.
    force: bool = False


# What Gemini returns. No list-length limits: Gemini rejects a response schema with maxItems on an array nested
# inside another array that has one (400 INVALID_ARGUMENT). The counts are enforced in code
# (app/services/interview.py) instead.

class InterviewQuestionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=500)
    type: QuestionType
    difficulty: Difficulty
    what_they_assess: str = Field(max_length=400)
    # Points a strong answer covers (an answer guide, not a script).
    answer_tips: list[str]
    # Verbatim resume quote the question builds on; empty when it isn't about the candidate's experience.
    resume_evidence: str = Field(max_length=400)


class TechnologyQuestionsOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    technology: str = Field(min_length=1, max_length=80)
    questions: list[InterviewQuestionOutput]


class LLMInterviewOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    technologies: list[TechnologyQuestionsOutput]


# What the API returns, after verification in code.

class InterviewQuestion(BaseModel):
    question: str
    type: QuestionType
    difficulty: Difficulty
    what_they_assess: str
    answer_tips: list[str]
    # Only present when the quote was found in the resume.
    resume_evidence: str | None = None


class TechnologyQuestions(BaseModel):
    technology: str
    # Where the technology appears, determined in code: in both documents, only the job
    # description (a gap to prepare for) or only the resume.
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
    # Groups removed by verification, with the reason, for transparency.
    skipped: list[SkippedTechnology]
    # True when these questions came from the cache instead of a new Gemini call.
    cached: bool = False
