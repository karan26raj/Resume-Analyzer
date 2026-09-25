from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.services import embeddings as embeddings_service
from app.services.embeddings import (
    DOCUMENT_TASK_TYPE,
    QUERY_TASK_TYPE,
    EmbeddingServiceError,
    chunk_text,
    create_embeddings,
)


class FakeModels:
    def __init__(self, drop_last: bool = False):
        self.calls = []
        self.drop_last = drop_last

    def embed_content(self, *, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "config": config})
        embeddings = [SimpleNamespace(values=[float(len(text))]) for text in contents]
        if self.drop_last:
            embeddings = embeddings[:-1]
        return SimpleNamespace(embeddings=embeddings)


def _use_fake_client(monkeypatch, models: FakeModels) -> None:
    monkeypatch.setattr(
        embeddings_service,
        "get_gemini_client",
        lambda: SimpleNamespace(models=models),
    )


def test_chunking(monkeypatch):
    monkeypatch.setattr(settings, "EMBEDDING_CHUNK_SIZE_WORDS", 3)
    monkeypatch.setattr(settings, "EMBEDDING_CHUNK_OVERLAP_WORDS", 1)
    assert chunk_text("one two three four five") == ["one two three", "three four five", "five"]
    assert chunk_text("   ") == []


def test_create_embeddings_batches_requests_and_sets_task_type(monkeypatch):
    models = FakeModels()
    _use_fake_client(monkeypatch, models)
    texts = [f"text {index}" for index in range(150)]

    vectors, tokens = create_embeddings(texts)

    assert len(vectors) == 150
    assert tokens is None
    assert [len(call["contents"]) for call in models.calls] == [100, 50]
    assert all(call["config"].task_type == DOCUMENT_TASK_TYPE for call in models.calls)
    assert models.calls[0]["config"].output_dimensionality == settings.EMBEDDING_DIMENSIONS


def test_create_embeddings_supports_query_task_type(monkeypatch):
    models = FakeModels()
    _use_fake_client(monkeypatch, models)

    create_embeddings(["what skills am I missing?"], task_type=QUERY_TASK_TYPE)

    assert models.calls[0]["config"].task_type == QUERY_TASK_TYPE


def test_create_embeddings_rejects_incomplete_response(monkeypatch):
    _use_fake_client(monkeypatch, FakeModels(drop_last=True))

    with pytest.raises(EmbeddingServiceError, match="incomplete"):
        create_embeddings(["a", "b"])


def test_create_embeddings_requires_api_key():
    # conftest clears GEMINI_API_KEY, so the real client cannot be created.
    with pytest.raises(EmbeddingServiceError, match="not configured"):
        create_embeddings(["a"])
