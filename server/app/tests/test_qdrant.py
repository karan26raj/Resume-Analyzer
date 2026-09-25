import pytest

from app.ai.qdrant_client import ensure_collection, get_collection_name
from app.core.config import settings


def test_ensure_collection_is_idempotent(qdrant):
    ensure_collection()
    ensure_collection()

    info = qdrant.get_collection(get_collection_name())
    assert info.config.params.vectors.size == settings.EMBEDDING_DIMENSIONS


def test_ensure_collection_rejects_dimension_mismatch(qdrant, monkeypatch):
    monkeypatch.setattr(settings, "EMBEDDING_DIMENSIONS", 768)

    with pytest.raises(RuntimeError, match="768"):
        ensure_collection()
