from app.ai.qdrant_client import get_collection_name
from app.ai.vector_store import (
    delete_document_chunks,
    point_id,
    search_chunks,
    upsert_chunks,
)
from app.tests.helpers import unit_vector


def _count(qdrant) -> int:
    return qdrant.count(collection_name=get_collection_name(), exact=True).count


def test_upsert_and_search(qdrant):
    upsert_chunks(
        user_id=1,
        document_type="resume",
        document_id=999,
        chunks=["Python FastAPI"],
        embeddings=[unit_vector(0)],
    )

    results = search_chunks(query_vector=unit_vector(0), user_id=1, limit=1)

    assert len(results) == 1
    assert results[0].payload["content"] == "Python FastAPI"


def test_point_ids_are_unique_per_user_type_document_and_chunk():
    ids = {
        point_id(1, "resume", 5, 0),
        point_id(1, "job", 5, 0),
        point_id(2, "resume", 5, 0),
        point_id(1, "resume", 5, 1),
        point_id(1, "resume", 6, 0),
    }
    assert len(ids) == 5
    assert point_id(1, "resume", 5, 0) == point_id(1, "resume", 5, 0)


def test_resume_and_job_with_same_id_do_not_overwrite_each_other(qdrant):
    upsert_chunks(
        user_id=1, document_type="resume", document_id=5,
        chunks=["resume text"], embeddings=[unit_vector(0)],
    )
    upsert_chunks(
        user_id=1, document_type="job", document_id=5,
        chunks=["job text"], embeddings=[unit_vector(1)],
    )
    upsert_chunks(
        user_id=2, document_type="resume", document_id=5,
        chunks=["other user's resume"], embeddings=[unit_vector(2)],
    )

    assert _count(qdrant) == 3
    contents = {hit.payload["content"] for hit in search_chunks(unit_vector(0), user_id=1, limit=10)}
    assert contents == {"resume text", "job text"}


def test_reindexing_a_shorter_document_removes_stale_chunks(qdrant):
    upsert_chunks(
        user_id=1, document_type="resume", document_id=7,
        chunks=["a", "b", "c"], embeddings=[unit_vector(0), unit_vector(1), unit_vector(2)],
    )
    upsert_chunks(
        user_id=1, document_type="resume", document_id=7,
        chunks=["new"], embeddings=[unit_vector(0)],
    )

    results = search_chunks(unit_vector(0), user_id=1, limit=10)
    assert [hit.payload["content"] for hit in results] == ["new"]


def test_search_filters_by_document_type_and_documents(qdrant):
    upsert_chunks(
        user_id=1, document_type="resume", document_id=1,
        chunks=["resume 1"], embeddings=[unit_vector(0)],
    )
    upsert_chunks(
        user_id=1, document_type="resume", document_id=2,
        chunks=["resume 2"], embeddings=[unit_vector(0)],
    )
    upsert_chunks(
        user_id=1, document_type="job", document_id=1,
        chunks=["job 1"], embeddings=[unit_vector(0)],
    )

    by_type = search_chunks(unit_vector(0), user_id=1, limit=10, document_type="job")
    assert [hit.payload["content"] for hit in by_type] == ["job 1"]

    scoped = search_chunks(
        unit_vector(0), user_id=1, limit=10, documents=[("resume", 2), ("job", 1)]
    )
    assert {hit.payload["content"] for hit in scoped} == {"resume 2", "job 1"}


def test_delete_document_chunks_only_removes_that_document(qdrant):
    upsert_chunks(
        user_id=1, document_type="job", document_id=3,
        chunks=["x", "y"], embeddings=[unit_vector(0), unit_vector(1)],
    )
    upsert_chunks(
        user_id=1, document_type="resume", document_id=3,
        chunks=["keep"], embeddings=[unit_vector(0)],
    )

    delete_document_chunks(1, "job", 3)

    results = search_chunks(unit_vector(0), user_id=1, limit=10)
    assert [hit.payload["content"] for hit in results] == ["keep"]
