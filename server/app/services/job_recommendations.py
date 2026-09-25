"""Rank a user's saved jobs by semantic similarity to one of their resumes (no LLM call)."""
import logging

from app.ai.vector_store import get_document_points, indexed_document_ids, search_chunks
from app.core.config import settings
from app.models.job import Job
from app.models.resume import Resume
from app.services.embeddings import EmbeddingServiceError
from app.services.indexing import EmptyDocumentError, index_document, job_to_text
from app.services.scoring import semantic_score


logger = logging.getLogger(__name__)

PASSAGE_PREVIEW_CHARACTERS = 240


class JobRecommendationError(Exception):
    pass


class EmptyResumeError(JobRecommendationError):
    pass


def _preview(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= PASSAGE_PREVIEW_CHARACTERS else f"{text[:PASSAGE_PREVIEW_CHARACTERS].rstrip()}…"


def _strength(score: float) -> str:
    if score >= 75:
        return "Strong"
    if score >= 50:
        return "Moderate"
    return "Weak"


def _ensure_resume_points(user_id: int, resume: Resume):
    points = get_document_points(user_id, "resume", resume.id)
    if points:
        return points
    try:
        index_document(user_id=user_id, document_type="resume", document_id=resume.id, text=resume.raw_text or "")
    except EmptyDocumentError as error:
        raise EmptyResumeError("Resume has no extractable text") from error
    except EmbeddingServiceError as error:
        raise JobRecommendationError(f"Could not index the resume: {error}") from error
    return get_document_points(user_id, "resume", resume.id)


def _ensure_jobs_indexed(user_id: int, jobs: list[Job]) -> list[int]:
    """Index any job missing from Qdrant. Returns the IDs of jobs that still couldn't be indexed."""
    indexed = indexed_document_ids(user_id, "job")
    failed = []
    for job in jobs:
        if job.id in indexed:
            continue
        try:
            index_document(user_id=user_id, document_type="job", document_id=job.id, text=job_to_text(job))
        except Exception:
            logger.warning("Could not index job %s for recommendations", job.id, exc_info=True)
            failed.append(job.id)
    return failed


def recommend_jobs(
    *,
    user_id: int,
    resume: Resume,
    jobs: list[Job],
    latest_analyses: dict[int, tuple[int, int]],
    limit: int,
) -> tuple[list[dict], list[int]]:
    """Returns (recommendations, unindexed_job_ids).

    `latest_analyses` maps job_id -> (analysis_id, match_score) of the newest analysis for this resume.
    """
    if not jobs:
        return [], []

    resume_points = _ensure_resume_points(user_id, resume)
    unindexed = _ensure_jobs_indexed(user_id, jobs)
    jobs_by_id = {job.id: job for job in jobs}

    # Enough neighbours per resume chunk that every candidate job can surface.
    per_chunk_limit = max(20, limit * 5)
    best: dict[int, tuple[float, str, str]] = {}
    for point in resume_points:
        hits = search_chunks(point.vector, user_id=user_id, limit=per_chunk_limit, document_type="job")
        for hit in hits:
            job_id = hit.payload["document_id"]
            if job_id not in jobs_by_id:
                continue  # stale vectors of a deleted job
            if job_id not in best or hit.score > best[job_id][0]:
                best[job_id] = (float(hit.score), point.payload["content"], hit.payload["content"])

    ranked = sorted(best.items(), key=lambda item: item[1][0], reverse=True)[:limit]

    recommendations = []
    for job_id, (similarity, resume_passage, job_passage) in ranked:
        job = jobs_by_id[job_id]
        score, _ = semantic_score(
            similarity,
            floor=settings.RECOMMENDATION_SIMILARITY_FLOOR,
            ceiling=settings.RECOMMENDATION_SIMILARITY_CEILING,
        )
        analysis = latest_analyses.get(job_id)
        reason = f"{_strength(score)} semantic match between your résumé and this job (similarity {similarity:.2f})."
        if analysis:
            reason += f" Your latest full analysis for this job scored {analysis[1]}/100."
        recommendations.append(
            {
                "job_id": job.id,
                "title": job.title,
                "company": job.company,
                "similarity": round(similarity, 4),
                "match_score": int(round(score)),
                "reason": reason,
                "resume_passage": _preview(resume_passage),
                "job_passage": _preview(job_passage),
                "analysis_id": analysis[0] if analysis else None,
                "analysis_score": analysis[1] if analysis else None,
            }
        )

    return recommendations, unindexed
