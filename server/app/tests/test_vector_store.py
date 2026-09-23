from app.ai.vector_store import (
    upsert_chunks,
    search_chunks
)


def test_upsert_and_search():

    vector = [0.1] * 3072

    upsert_chunks(
        user_id=1,
        document_type="resume",
        document_id=999,
        chunks=["Python FastAPI"],
        embeddings=[vector]
    )

    results = search_chunks(
        query_vector=vector,
        user_id=1,
        limit=1
    )

    assert len(results) >= 1