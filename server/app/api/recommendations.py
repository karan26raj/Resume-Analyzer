from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.analysis_result import AnalysisResult
from app.models.job import Job
from app.models.resume import Resume
from app.models.user import User
from app.schemas.recommendation import JobRecommendationsResponse, RecommendationsResponse
from app.services import cache
from app.services.job_recommendations import EmptyResumeError, JobRecommendationError, recommend_jobs


router = APIRouter(
    prefix="/recommendations",
    tags=["Recommendations"]
)


MAX_RECOMMENDATIONS = 10


@router.get("", response_model=RecommendationsResponse)
def get_recommendations(
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Aggregate the user's analyses into their most frequent skill gaps and latest recommendations."""
    cache_key = cache.recommendations_key(current_user.id, "skills", limit)
    cached = cache.get_json(cache_key)
    if cached is not None:
        return cached

    analyses = (
        db.query(AnalysisResult)
        .filter(AnalysisResult.user_id == current_user.id)
        .order_by(AnalysisResult.id.desc())
        .all()
    )

    skill_counts: Counter[str] = Counter()
    # Keep the first spelling seen (from the newest analysis) for each case-insensitive skill.
    display_names: dict[str, str] = {}

    for analysis in analyses:
        # Count each skill at most once per analysis.
        seen_in_analysis = set()
        for skill in analysis.missing_skills:
            key = skill.strip().lower()
            if not key or key in seen_in_analysis:
                continue
            seen_in_analysis.add(key)
            skill_counts[key] += 1
            display_names.setdefault(key, skill.strip())

    recommendations: list[str] = []
    seen_recommendations = set()
    for analysis in analyses:
        for recommendation in analysis.recommendations:
            key = recommendation.strip().lower()
            if key and key not in seen_recommendations:
                seen_recommendations.add(key)
                recommendations.append(recommendation.strip())

    average_match_score = (
        round(sum(analysis.match_score for analysis in analyses) / len(analyses), 1)
        if analyses
        else None
    )

    response = {
        "analysis_count": len(analyses),
        "average_match_score": average_match_score,
        "top_missing_skills": [
            {"skill": display_names[key], "count": count}
            for key, count in skill_counts.most_common(limit)
        ],
        "recommendations": recommendations[:MAX_RECOMMENDATIONS],
    }
    cache.set_json(cache_key, response, settings.CACHE_TTL_RECOMMENDATIONS_SECONDS)
    return response


@router.get("/jobs", response_model=JobRecommendationsResponse)
def get_job_recommendations(
    resume_id: int | None = Query(default=None, gt=0, description="Defaults to your most recent resume"),
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Rank your saved jobs by semantic similarity to a resume (phase 11)."""
    cache_key = cache.recommendations_key(current_user.id, "jobs", resume_id or "latest", limit)
    cached = cache.get_json(cache_key)
    if cached is not None:
        return cached

    resume_query = db.query(Resume).filter(Resume.user_id == current_user.id)
    if resume_id is not None:
        resume = resume_query.filter(Resume.id == resume_id).first()
    else:
        resume = resume_query.order_by(Resume.id.desc()).first()
    if resume is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")

    jobs = db.query(Job).filter(Job.user_id == current_user.id).all()

    latest_analyses: dict[int, tuple[int, int]] = {}
    analyses = (
        db.query(AnalysisResult.id, AnalysisResult.job_id, AnalysisResult.match_score)
        .filter(AnalysisResult.user_id == current_user.id, AnalysisResult.resume_id == resume.id)
        .order_by(AnalysisResult.id.desc())
    )
    for analysis_id, job_id, match_score in analyses:
        latest_analyses.setdefault(job_id, (analysis_id, match_score))

    try:
        recommendations, unindexed = recommend_jobs(
            user_id=current_user.id,
            resume=resume,
            jobs=jobs,
            latest_analyses=latest_analyses,
            limit=limit,
        )
    except EmptyResumeError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error))
    except JobRecommendationError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error))
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vector search failed: {error}",
        )

    response = {
        "resume_id": resume.id,
        "recommendations": recommendations,
        "unindexed_job_ids": unindexed,
    }
    # A partial ranking (some jobs couldn't be indexed) is not cached, so a retry can complete it.
    if not unindexed:
        cache.set_json(cache_key, response, settings.CACHE_TTL_RECOMMENDATIONS_SECONDS)
    return response
