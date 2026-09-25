"""Unit tests for the match analysis pipeline (phases 9, 10 and 13)."""
from types import SimpleNamespace

import pytest

from app.ai.vector_store import upsert_chunks
from app.schemas.analysis import LLMMatchOutput, RequirementAssessment
from app.services import analysis as analysis_service
from app.services import retrieval as retrieval_service
from app.services.analysis import run_match_analysis, skill_lists, verify_requirements
from app.services.retrieval import RetrievalError, retrieve_resume_evidence
from app.tests.helpers import unit_vector


RESUME = "Software engineer at Northwind. Built FastAPI services in Python. Led a team of 4 engineers."


def requirement(name, status, evidence="", category="skill", importance="required"):
    return {
        "requirement": name,
        "category": category,
        "importance": importance,
        "status": status,
        "evidence": evidence,
    }


# --- evidence verification (phase 13) --------------------------------------------------


def test_verified_evidence_keeps_status():
    [item] = verify_requirements([requirement("Python", "met", "Built FastAPI services in Python")], RESUME)

    assert item["status"] == "met"
    assert item["evidence_verified"] is True
    assert item["model_status"] == "met"


def test_unsupported_met_claim_is_downgraded_to_partial():
    [item] = verify_requirements([requirement("Kubernetes", "met", "Deployed services on Kubernetes clusters")], RESUME)

    assert item["status"] == "partial"
    assert item["model_status"] == "met"
    assert item["evidence_verified"] is False


def test_unsupported_partial_claim_is_downgraded_to_missing():
    [item] = verify_requirements([requirement("AWS", "partial", "Used AWS Lambda")], RESUME)

    assert item["status"] == "missing"


def test_met_claim_without_evidence_is_downgraded():
    [item] = verify_requirements([requirement("Python", "met", "")], RESUME)

    assert item["status"] == "partial"


def test_missing_requirement_has_empty_evidence():
    [item] = verify_requirements([requirement("Go", "missing", "irrelevant text")], RESUME)

    assert item["status"] == "missing"
    assert item["evidence"] == ""
    assert item["evidence_verified"] is False


def test_skill_lists_only_include_skills():
    items = [
        requirement("Python", "met"),
        requirement("Docker", "partial"),
        requirement("Rust", "missing"),
        requirement("5 years backend", "missing", category="experience"),
    ]

    assert skill_lists(items) == (["Python", "Docker"], ["Rust"])


# --- retrieval (phase 9) ----------------------------------------------------------------


def test_retrieval_returns_only_this_resumes_passages(qdrant, monkeypatch):
    upsert_chunks(user_id=5, document_type="resume", document_id=1, chunks=["mine a", "mine b"],
                  embeddings=[unit_vector(0), unit_vector(1)])
    upsert_chunks(user_id=5, document_type="resume", document_id=2, chunks=["other resume"],
                  embeddings=[unit_vector(0)])
    upsert_chunks(user_id=5, document_type="job", document_id=1, chunks=["a job"], embeddings=[unit_vector(0)])
    captured = {}

    def fake_embed(texts, task_type):
        captured["task_type"] = task_type
        captured["text"] = texts[0]
        return [unit_vector(0)], None

    monkeypatch.setattr(retrieval_service, "create_embeddings", fake_embed)

    result = retrieve_resume_evidence(user_id=5, resume_id=1, resume_text="mine", job_text="Job " * 5000)

    assert [passage["content"] for passage in result.passages] == ["mine a", "mine b"]
    assert result.passages[0]["score"] == pytest.approx(1.0)
    # Mean of the top passages: (1.0 + 0.0) / 2
    assert result.similarity == pytest.approx(0.5)
    assert captured["task_type"] == "RETRIEVAL_QUERY"
    assert len(captured["text"]) == 6000  # long job descriptions are trimmed before embedding


def test_retrieval_indexes_an_unindexed_resume_first(qdrant, monkeypatch):
    monkeypatch.setattr(retrieval_service, "create_embeddings", lambda texts, task_type: ([unit_vector(3)], None))
    indexed = {}

    def fake_index(**kwargs):
        indexed.update(kwargs)
        upsert_chunks(user_id=kwargs["user_id"], document_type="resume", document_id=kwargs["document_id"],
                      chunks=[kwargs["text"]], embeddings=[unit_vector(3)])
        return 1, None

    monkeypatch.setattr(retrieval_service, "index_document", fake_index)

    result = retrieve_resume_evidence(user_id=6, resume_id=9, resume_text="fresh resume", job_text="job")

    assert indexed["document_id"] == 9
    assert [passage["content"] for passage in result.passages] == ["fresh resume"]


def test_retrieval_wraps_failures(qdrant, monkeypatch):
    def failing_embed(texts, task_type):
        raise RuntimeError("embedding quota")

    monkeypatch.setattr(retrieval_service, "create_embeddings", failing_embed)

    with pytest.raises(RetrievalError, match="embedding quota"):
        retrieve_resume_evidence(user_id=1, resume_id=1, resume_text="x", job_text="y")


# --- full pipeline ------------------------------------------------------------------------


def _resume_and_job():
    resume = SimpleNamespace(id=1, raw_text=RESUME)
    job = SimpleNamespace(id=2, title="Backend Engineer", company="Acme", description="Python, Kubernetes")
    return resume, job


def _assessment():
    return LLMMatchOutput(
        requirements=[
            RequirementAssessment(requirement="Python", category="skill", importance="required",
                                  status="met", evidence="Built FastAPI services in Python"),
            RequirementAssessment(requirement="Kubernetes", category="skill", importance="required",
                                  status="met", evidence="Ran Kubernetes in production"),
        ],
        strengths=["s"], weaknesses=["w"], recommendations=["r"],
    )


def test_pipeline_passes_retrieved_passages_to_the_model(monkeypatch):
    passages = [{"chunk_index": 0, "content": "Built FastAPI services in Python.", "score": 0.8}]
    monkeypatch.setattr(
        analysis_service,
        "retrieve_resume_evidence",
        lambda **kwargs: retrieval_service.RetrievedEvidence(passages=passages, similarity=0.8),
    )
    captured = {}

    def fake_generate(**kwargs):
        captured.update(kwargs)
        return _assessment(), 10, 5, "model-x"

    monkeypatch.setattr(analysis_service, "generate_match", fake_generate)
    resume, job = _resume_and_job()

    result = run_match_analysis(user_id=1, resume=resume, job=job)

    assert captured["retrieved_passages"] == passages
    assert result["retrieved_evidence"] == passages
    assert result["semantic_similarity"] == 0.8
    # The invented Kubernetes quote was downgraded, so it counts as partial, not met.
    statuses = {item["requirement"]: item["status"] for item in result["requirements"]}
    assert statuses == {"Python": "met", "Kubernetes": "partial"}


def test_pipeline_continues_without_retrieval(monkeypatch):
    def failing_retrieval(**kwargs):
        raise RetrievalError("qdrant down")

    monkeypatch.setattr(analysis_service, "retrieve_resume_evidence", failing_retrieval)
    captured = {}

    def fake_generate(**kwargs):
        captured.update(kwargs)
        return _assessment(), None, None, "model-x"

    monkeypatch.setattr(analysis_service, "generate_match", fake_generate)
    resume, job = _resume_and_job()

    result = run_match_analysis(user_id=1, resume=resume, job=job)

    assert captured["retrieved_passages"] == []
    assert result["semantic_similarity"] is None
    semantic = next(item for item in result["score_breakdown"]["components"] if item["name"] == "semantic")
    assert semantic["score"] is None
    assert semantic["effective_weight"] == 0
    # Only skills remain: Python met (2) + Kubernetes partial (1) of 4 -> 75
    assert result["match_score"] == 75
