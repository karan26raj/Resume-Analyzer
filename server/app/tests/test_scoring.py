import pytest

from app.core.config import settings
from app.services.scoring import ScoringError, category_score, compute_match_score, semantic_score


def req(category, status, importance="required"):
    return {"requirement": "x", "category": category, "importance": importance, "status": status, "evidence": ""}


def components(breakdown):
    return {item["name"]: item for item in breakdown["components"]}


def test_category_score_weights_importance_and_partial_credit():
    items = [
        req("skill", "met"),
        req("skill", "partial"),
        req("skill", "missing", "preferred"),
        req("experience", "met"),
    ]

    score, detail = category_score(items, "skill")

    assert score == pytest.approx(60.0)
    assert detail == "1 met, 1 partial of 3 skill requirements"


def test_category_without_requirements_is_unavailable():
    assert category_score([req("skill", "met")], "education") == (None, "No education requirements identified")


@pytest.mark.parametrize(
    ("similarity", "expected"),
    [(0.30, 0.0), (0.45, 0.0), (0.65, 50.0), (0.85, 100.0), (0.95, 100.0)],
)
def test_semantic_score_calibration(similarity, expected):
    score, _ = semantic_score(similarity)
    assert score == pytest.approx(expected)


def test_semantic_score_custom_calibration():
    assert semantic_score(0.775, floor=0.70, ceiling=0.85)[0] == pytest.approx(50.0)
    assert semantic_score(0.74, floor=0.70, ceiling=0.85)[0] == pytest.approx(26.7)


def test_semantic_score_unavailable():
    assert semantic_score(None)[0] is None


def test_all_components_use_the_roadmap_weights():
    items = [
        req("skill", "met"),
        req("experience", "partial"),
        req("education", "missing"),
    ]

    score, breakdown = compute_match_score(items, similarity=0.85)

    assert score == 78
    parts = components(breakdown)
    assert {name: part["effective_weight"] for name, part in parts.items()} == {
        "skills": 0.4, "experience": 0.25, "education": 0.1, "semantic": 0.25,
    }
    assert "skills 40%" in breakdown["method"]


def test_missing_components_are_reweighted():
    score, breakdown = compute_match_score([req("skill", "met")], similarity=0.40)

    parts = components(breakdown)
    assert parts["experience"]["score"] is None
    assert parts["experience"]["effective_weight"] == 0
    assert parts["skills"]["effective_weight"] == pytest.approx(0.6154, abs=1e-4)
    assert score == round(100 * 0.40 / 0.65)


def test_score_without_semantic_similarity():
    score, breakdown = compute_match_score([req("skill", "met"), req("skill", "missing")], similarity=None)

    assert score == 50
    assert components(breakdown)["semantic"]["detail"] == "Semantic retrieval unavailable"


def test_nothing_measurable_raises():
    with pytest.raises(ScoringError):
        compute_match_score([], similarity=None)


def test_weights_are_configurable(monkeypatch):
    monkeypatch.setattr(settings, "SCORE_WEIGHT_SKILLS", 1.0)
    monkeypatch.setattr(settings, "SCORE_WEIGHT_SEMANTIC", 0.0)

    score, breakdown = compute_match_score([req("skill", "partial")], similarity=0.85)

    assert score == 50
    assert "skills 100%" in breakdown["method"]


def test_score_is_always_between_0_and_100():
    best, _ = compute_match_score([req(c, "met") for c in ("skill", "experience", "education")], similarity=1.0)
    worst, _ = compute_match_score([req(c, "missing") for c in ("skill", "experience", "education")], similarity=0.0)

    assert (best, worst) == (100, 0)
