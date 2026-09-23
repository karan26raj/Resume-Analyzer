from app.services.embeddings import chunk_text, cosine_similarity
from app.core.config import settings


def test_cosine_similarity_and_chunking(monkeypatch):
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0
    monkeypatch.setattr(settings, "EMBEDDING_CHUNK_SIZE_WORDS", 3)
    monkeypatch.setattr(settings, "EMBEDDING_CHUNK_OVERLAP_WORDS", 1)
    assert chunk_text("one two three four five") == ["one two three", "three four five", "five"]
