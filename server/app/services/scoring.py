"""Explainable match score computed in code: skills 40%, experience 25%, education 10%, semantic 25%.

A component that can't be measured is dropped and its weight shared proportionally by the rest.
"""
from app.core.config import settings


STATUS_CREDIT = {"met": 1.0, "partial": 0.5, "missing": 0.0}
# Required requirements count twice as much as preferred ones.
IMPORTANCE_WEIGHT = {"required": 2.0, "preferred": 1.0}

CATEGORY_COMPONENTS = (("skills", "skill"), ("experience", "experience"), ("education", "education"))


class ScoringError(Exception):
    pass


def component_weights() -> dict[str, float]:
    return {
        "skills": settings.SCORE_WEIGHT_SKILLS,
        "experience": settings.SCORE_WEIGHT_EXPERIENCE,
        "education": settings.SCORE_WEIGHT_EDUCATION,
        "semantic": settings.SCORE_WEIGHT_SEMANTIC,
    }


def category_score(requirements: list[dict], category: str) -> tuple[float | None, str]:
    """Importance-weighted share of requirements met (partial counts half). None if there are none."""
    relevant = [item for item in requirements if item["category"] == category]
    if not relevant:
        return None, f"No {category} requirements identified"

    total = sum(IMPORTANCE_WEIGHT[item["importance"]] for item in relevant)
    earned = sum(IMPORTANCE_WEIGHT[item["importance"]] * STATUS_CREDIT[item["status"]] for item in relevant)
    met = sum(1 for item in relevant if item["status"] == "met")
    partial = sum(1 for item in relevant if item["status"] == "partial")

    detail = f"{met} met, {partial} partial of {len(relevant)} {category} requirement{'s' if len(relevant) != 1 else ''}"
    return round(100 * earned / total, 1), detail


def semantic_score(
    similarity: float | None,
    floor: float | None = None,
    ceiling: float | None = None,
) -> tuple[float | None, str]:
    """Map cosine similarity onto 0-100 using a floor/ceiling calibration (defaults: analysis settings)."""
    if similarity is None:
        return None, "Semantic retrieval unavailable"

    floor = settings.SEMANTIC_SIMILARITY_FLOOR if floor is None else floor
    ceiling = settings.SEMANTIC_SIMILARITY_CEILING if ceiling is None else ceiling
    scaled = (similarity - floor) / (ceiling - floor)
    score = round(100 * min(1.0, max(0.0, scaled)), 1)
    return score, f"Resume-to-job similarity {similarity:.3f}"


def compute_match_score(requirements: list[dict], similarity: float | None) -> tuple[int, dict]:
    """Returns (score 0-100, breakdown). Raises ScoringError when nothing can be measured."""
    weights = component_weights()

    raw: list[tuple[str, float | None, str]] = [
        (name, *category_score(requirements, category)) for name, category in CATEGORY_COMPONENTS
    ]
    raw.append(("semantic", *semantic_score(similarity)))

    available_weight = sum(weights[name] for name, score, _ in raw if score is not None)
    if available_weight <= 0:
        raise ScoringError("No requirements could be identified and semantic similarity is unavailable")

    components = []
    total = 0.0
    for name, score, detail in raw:
        effective = weights[name] / available_weight if score is not None else 0.0
        if score is not None:
            total += score * effective
        components.append(
            {
                "name": name,
                "score": score,
                "weight": weights[name],
                "effective_weight": round(effective, 4),
                "detail": detail,
            }
        )

    weight_text = ", ".join(f"{name} {weights[name] * 100:g}%" for name in weights)
    breakdown = {
        "method": f"Weighted: {weight_text} (unavailable parts re-weighted)",
        "components": components,
    }
    return int(round(total)), breakdown
