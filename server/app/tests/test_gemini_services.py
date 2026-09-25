from types import SimpleNamespace

import pytest
from google.genai import errors

from app.ai import gemini as gemini_module
from app.ai.gemini import candidate_models, generate_content_with_fallback
from app.ai.vector_store import upsert_chunks
from app.core.config import settings
from app.schemas.analysis import LLMMatchOutput, RequirementAssessment
from app.services import rag as rag_service
from app.services.matching import AnalysisServiceError, generate_match
from app.services.rag import NO_CONTEXT_ANSWER, RAGServiceError, ask_question, build_prompt
from app.tests.helpers import unit_vector


VALID_MATCH_JSON = (
    '{"requirements": [{"requirement": "Python", "category": "skill", "importance": "required", '
    '"status": "met", "evidence": "Python developer"}], '
    '"strengths": ["APIs"], "weaknesses": ["No cloud"], "recommendations": ["Add AWS"]}'
)


def api_error(code: int) -> errors.APIError:
    error_class = errors.ServerError if code >= 500 else errors.ClientError
    return error_class(code, {"error": {"code": code, "message": "test", "status": "TEST"}})


class FakeGenerateModels:
    def __init__(self, text, usage=None, error=None, errors_by_model=None):
        self.text = text
        self.usage = usage
        self.error = error
        self.errors_by_model = errors_by_model or {}
        self.calls = []

    def generate_content(self, *, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "config": config})
        if model in self.errors_by_model:
            raise self.errors_by_model[model]
        if self.error:
            raise self.error
        return SimpleNamespace(text=self.text, usage_metadata=self.usage)


@pytest.fixture
def use_models(monkeypatch):
    def install(models: FakeGenerateModels) -> FakeGenerateModels:
        monkeypatch.setattr(
            gemini_module, "get_gemini_client", lambda: SimpleNamespace(models=models)
        )
        return models

    return install


@pytest.fixture
def model_chain(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_MODEL", "primary")
    monkeypatch.setattr(settings, "GEMINI_FALLBACK_MODELS", ["backup-1", "backup-2"])


def _match(**overrides):
    kwargs = {
        "resume_text": "Python developer",
        "job_title": "Backend Developer",
        "company": "Example",
        "job_description": "Python and AWS",
    }
    kwargs.update(overrides)
    return generate_match(**kwargs)


def test_candidate_models_puts_primary_first_and_removes_duplicates(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_MODEL", "b")
    monkeypatch.setattr(settings, "GEMINI_FALLBACK_MODELS", ["a", "b", "c", "a"])

    assert candidate_models() == ["b", "a", "c"]


def test_candidate_models_without_fallbacks(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_MODEL", "only")
    monkeypatch.setattr(settings, "GEMINI_FALLBACK_MODELS", [])

    assert candidate_models() == ["only"]


def test_primary_model_is_used_when_available(use_models, model_chain):
    models = use_models(FakeGenerateModels("ok"))

    response, model_used = generate_content_with_fallback(contents="hi", config=None)

    assert response.text == "ok"
    assert model_used == "primary"
    assert [call["model"] for call in models.calls] == ["primary"]


@pytest.mark.parametrize("code", [404, 429, 500, 503, 504])
def test_falls_back_on_unavailable_models(use_models, model_chain, code):
    models = use_models(
        FakeGenerateModels("ok", errors_by_model={"primary": api_error(code)})
    )

    _, model_used = generate_content_with_fallback(contents="hi", config=None)

    assert model_used == "backup-1"
    assert [call["model"] for call in models.calls] == ["primary", "backup-1"]


def test_tries_every_model_in_order(use_models, model_chain):
    models = use_models(
        FakeGenerateModels(
            "ok",
            errors_by_model={"primary": api_error(503), "backup-1": api_error(429)},
        )
    )

    _, model_used = generate_content_with_fallback(contents="hi", config=None)

    assert model_used == "backup-2"
    assert [call["model"] for call in models.calls] == ["primary", "backup-1", "backup-2"]


def test_raises_last_error_when_all_models_fail(use_models, model_chain):
    use_models(
        FakeGenerateModels(
            "ok",
            errors_by_model={
                "primary": api_error(503),
                "backup-1": api_error(503),
                "backup-2": api_error(429),
            },
        )
    )

    with pytest.raises(errors.APIError) as raised:
        generate_content_with_fallback(contents="hi", config=None)

    assert raised.value.code == 429


@pytest.mark.parametrize("code", [400, 401, 403])
def test_does_not_fall_back_on_request_errors(use_models, model_chain, code):
    models = use_models(
        FakeGenerateModels("ok", errors_by_model={"primary": api_error(code)})
    )

    with pytest.raises(errors.APIError):
        generate_content_with_fallback(contents="hi", config=None)

    assert [call["model"] for call in models.calls] == ["primary"]


def test_does_not_fall_back_on_non_api_errors(use_models, model_chain):
    models = use_models(FakeGenerateModels("ok", error=TimeoutError("timed out")))

    with pytest.raises(TimeoutError):
        generate_content_with_fallback(contents="hi", config=None)

    assert len(models.calls) == 1


def test_generate_match_parses_structured_output_and_token_usage(use_models):
    models = use_models(
        FakeGenerateModels(
            VALID_MATCH_JSON,
            usage=SimpleNamespace(prompt_token_count=120, candidates_token_count=45),
        )
    )

    passages = [{"chunk_index": 0, "content": "Retrieved passage about APIs", "score": 0.81}]
    result, input_tokens, output_tokens, model_used = _match(retrieved_passages=passages)

    assert result == LLMMatchOutput(
        requirements=[
            RequirementAssessment(
                requirement="Python", category="skill", importance="required",
                status="met", evidence="Python developer",
            )
        ],
        strengths=["APIs"],
        weaknesses=["No cloud"],
        recommendations=["Add AWS"],
    )
    assert (input_tokens, output_tokens) == (120, 45)
    assert model_used == settings.GEMINI_MODEL

    config = models.calls[0]["config"]
    assert config.response_mime_type == "application/json"
    assert config.response_json_schema == LLMMatchOutput.model_json_schema()
    contents = models.calls[0]["contents"]
    assert "Python developer" in contents
    assert '<passage similarity="0.81">\nRetrieved passage about APIs\n</passage>' in contents


def test_llm_schema_does_not_ask_the_model_for_a_score():
    assert "match_score" not in LLMMatchOutput.model_json_schema()["properties"]


def test_generate_match_rejects_invalid_requirement_values(use_models):
    use_models(
        FakeGenerateModels(
            '{"requirements": [{"requirement": "Python", "category": "hobby", "importance": "required", '
            '"status": "met", "evidence": ""}], "strengths": [], "weaknesses": [], "recommendations": []}'
        )
    )

    with pytest.raises(AnalysisServiceError, match="invalid structured output"):
        _match()


def test_generate_match_reports_the_fallback_model_used(use_models, model_chain):
    use_models(
        FakeGenerateModels(VALID_MATCH_JSON, errors_by_model={"primary": api_error(503)})
    )

    *_, model_used = _match()

    assert model_used == "backup-1"


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("not json", "invalid JSON"),
        ('{"match_score": 500}', "invalid structured output"),
        ("", "empty response"),
    ],
)
def test_generate_match_rejects_bad_output(use_models, text, message):
    use_models(FakeGenerateModels(text))

    with pytest.raises(AnalysisServiceError, match=message):
        _match()


def test_generate_match_wraps_api_errors(use_models, model_chain):
    use_models(FakeGenerateModels(None, error=api_error(503)))

    with pytest.raises(AnalysisServiceError, match="503"):
        _match()


def test_generate_match_requires_api_key():
    with pytest.raises(AnalysisServiceError, match="not configured"):
        _match()


def test_build_prompt_fills_context_and_question():
    hit = SimpleNamespace(
        payload={
            "document_type": "resume",
            "document_id": 3,
            "chunk_index": 0,
            "content": "Built APIs with {FastAPI}",
        }
    )

    prompt = build_prompt("What did I build?", [hit])

    assert "Built APIs with {FastAPI}" in prompt
    assert "<question>\nWhat did I build?\n</question>" in prompt
    assert "{retrieved_chunks}" not in prompt
    assert "{user_question}" not in prompt
    assert prompt.count("<context>") == 1


def test_build_prompt_labels_documents_by_name_not_id():
    hits = [
        SimpleNamespace(payload={"document_type": "resume", "document_id": 3, "chunk_index": 0, "content": "a"}),
        SimpleNamespace(payload={"document_type": "job", "document_id": 7, "chunk_index": 2, "content": "b"}),
        SimpleNamespace(payload={"document_type": "job", "document_id": 8, "chunk_index": 0, "content": "c"}),
    ]
    names = {("resume", 3): "Alex_Resume.pdf", ("job", 7): 'Senior "Python" Dev at Acme'}

    prompt = build_prompt("?", hits, names)

    assert '<document type="résumé" name="Alex_Resume.pdf">' in prompt
    assert '<document type="job description" name="Senior \'Python\' Dev at Acme">' in prompt
    assert '<document type="job description" name="job description">' in prompt
    assert 'id="' not in prompt and "chunk=" not in prompt


def test_ask_question_returns_fallback_without_calling_gemini_when_nothing_is_indexed(
    qdrant, monkeypatch
):
    monkeypatch.setattr(rag_service, "create_embeddings", lambda texts, task_type: ([unit_vector(0)], None))
    monkeypatch.setattr(
        gemini_module,
        "get_gemini_client",
        lambda: pytest.fail("Gemini must not be called without context"),
    )

    answer, sources = ask_question(question="Anything?", user_id=12345)

    assert answer == NO_CONTEXT_ANSWER
    assert sources == []


def test_ask_question_answers_from_scoped_context(qdrant, monkeypatch, use_models):
    upsert_chunks(
        user_id=77, document_type="resume", document_id=1,
        chunks=["Resume one: Python"], embeddings=[unit_vector(0)],
    )
    upsert_chunks(
        user_id=77, document_type="resume", document_id=2,
        chunks=["Resume two: Java"], embeddings=[unit_vector(0)],
    )

    captured = {}

    def fake_create_embeddings(texts, task_type):
        captured["task_type"] = task_type
        return [unit_vector(0)], None

    monkeypatch.setattr(rag_service, "create_embeddings", fake_create_embeddings)
    models = use_models(FakeGenerateModels("You know Java."))

    answer, sources = ask_question(
        question="Which language?", user_id=77, documents=[("resume", 2)]
    )

    assert answer == "You know Java."
    assert captured["task_type"] == "RETRIEVAL_QUERY"
    assert [(source["document_type"], source["document_id"]) for source in sources] == [("resume", 2)]
    assert "Resume two: Java" in models.calls[0]["contents"]
    assert "Resume one" not in models.calls[0]["contents"]
    assert models.calls[0]["config"].system_instruction == rag_service.SYSTEM_PROMPT


def test_ask_question_uses_fallback_model(qdrant, monkeypatch, use_models, model_chain):
    upsert_chunks(
        user_id=79, document_type="job", document_id=1,
        chunks=["Job text"], embeddings=[unit_vector(0)],
    )
    monkeypatch.setattr(rag_service, "create_embeddings", lambda texts, task_type: ([unit_vector(0)], None))
    models = use_models(
        FakeGenerateModels("answer", errors_by_model={"primary": api_error(503)})
    )

    answer, _ = ask_question(question="?", user_id=79)

    assert answer == "answer"
    assert [call["model"] for call in models.calls] == ["primary", "backup-1"]


def test_ask_question_wraps_gemini_errors(qdrant, monkeypatch, use_models):
    upsert_chunks(
        user_id=78, document_type="job", document_id=1,
        chunks=["Job text"], embeddings=[unit_vector(0)],
    )
    monkeypatch.setattr(rag_service, "create_embeddings", lambda texts, task_type: ([unit_vector(0)], None))
    use_models(FakeGenerateModels(None, error=RuntimeError("quota exceeded")))

    with pytest.raises(RAGServiceError, match="quota exceeded"):
        ask_question(question="?", user_id=78)
