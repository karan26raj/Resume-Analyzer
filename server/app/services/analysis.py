import logging

from app.models.job import Job
from app.models.resume import Resume
from app.services.evidence import is_supported
from app.services.indexing import job_to_text
from app.services.matching import AnalysisServiceError, generate_match
from app.services.retrieval import RetrievalError, retrieve_resume_evidence
from app.services.scoring import ScoringError, compute_match_score


logger = logging.getLogger(__name__)

DOWNGRADE = {"met": "partial", "partial": "missing", "missing": "missing"}


def verify_requirements(requirements: list[dict], resume_text: str) -> list[dict]:
    verified = []
    for item in requirements:
        status = item["status"]
        supported = status != "missing" and is_supported(item["evidence"], resume_text)
        verified.append(
            {
                **item,
                "evidence": item["evidence"] if status != "missing" else "",
                "model_status": status,
                "status": status if supported or status == "missing" else DOWNGRADE[status],
                "evidence_verified": supported,
            }
        )
    return verified


def skill_lists(requirements: list[dict]) -> tuple[list[str], list[str]]:
    skills = [item for item in requirements if item["category"] == "skill"]
    matched = [item["requirement"] for item in skills if item["status"] in ("met", "partial")]
    missing = [item["requirement"] for item in skills if item["status"] == "missing"]
    return matched, missing


def run_match_analysis(*, user_id: int, resume: Resume, job: Job) -> dict:
    try:
        evidence = retrieve_resume_evidence(
            user_id=user_id,
            resume_id=resume.id,
            resume_text=resume.raw_text,
            job_text=job_to_text(job),
        )
    except RetrievalError:
        logger.warning("Retrieval failed for resume %s / job %s; continuing without it", resume.id, job.id, exc_info=True)
        evidence = None

    passages = evidence.passages if evidence else []
    similarity = evidence.similarity if evidence else None

    assessment, input_tokens, output_tokens, model_used = generate_match(
        resume_text=resume.raw_text,
        job_title=job.title,
        company=job.company,
        job_description=job.description,
        retrieved_passages=passages,
    )

    requirements = verify_requirements(
        [item.model_dump() for item in assessment.requirements],
        resume.raw_text,
    )

    try:
        match_score, breakdown = compute_match_score(requirements, similarity)
    except ScoringError as error:
        raise AnalysisServiceError(str(error)) from error

    matched_skills, missing_skills = skill_lists(requirements)

    return {
        "match_score": match_score,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "strengths": assessment.strengths,
        "weaknesses": assessment.weaknesses,
        "recommendations": assessment.recommendations,
        "requirements": requirements,
        "score_breakdown": breakdown,
        "semantic_similarity": similarity,
        "retrieved_evidence": passages,
        "model": model_used,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }
