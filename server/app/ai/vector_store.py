import uuid

from qdrant_client.models import (
    FieldCondition,
    Filter,
    FilterSelector,
    MatchValue,
    PointStruct,
)

from app.ai.qdrant_client import get_collection_name, get_qdrant_client


# Fixed namespace so the same chunk always maps to the same point ID.
POINT_ID_NAMESPACE = uuid.UUID("5b0f8a52-3c1e-4d7a-9f2b-6e4c1a9d8b70")


def point_id(user_id: int, document_type: str, document_id: int, chunk_index: int) -> str:
    """Point IDs are unique per user, document type, document and chunk, so documents never collide."""
    return str(
        uuid.uuid5(
            POINT_ID_NAMESPACE,
            f"{user_id}:{document_type}:{document_id}:{chunk_index}",
        )
    )


def _match(key: str, value) -> FieldCondition:
    return FieldCondition(key=key, match=MatchValue(value=value))


def _document_filter(user_id: int, document_type: str, document_id: int) -> Filter:
    return Filter(
        must=[
            _match("user_id", user_id),
            _match("document_type", document_type),
            _match("document_id", document_id),
        ]
    )


def delete_document_chunks(user_id: int, document_type: str, document_id: int) -> None:
    get_qdrant_client().delete(
        collection_name=get_collection_name(),
        points_selector=FilterSelector(
            filter=_document_filter(user_id, document_type, document_id)
        ),
    )


def upsert_chunks(
    user_id: int,
    document_type: str,
    document_id: int,
    chunks: list[str],
    embeddings: list[list[float]]
):
    if len(chunks) != len(embeddings):
        raise ValueError("Each chunk must have exactly one embedding")

    points = [
        PointStruct(
            id=point_id(user_id, document_type, document_id, index),
            vector=vector,
            payload={
                "user_id": user_id,
                "document_type": document_type,
                "document_id": document_id,
                "chunk_index": index,
                "content": chunk
            }
        )
        for index, (chunk, vector) in enumerate(zip(chunks, embeddings))
    ]

    # Remove the previous version first so re-indexing a shorter document leaves no stale chunks.
    delete_document_chunks(user_id, document_type, document_id)

    get_qdrant_client().upsert(
        collection_name=get_collection_name(),
        points=points
    )


def get_document_points(user_id: int, document_type: str, document_id: int, with_vectors: bool = True):
    """All stored chunks of one document, in chunk order (vectors included by default)."""
    points, _ = get_qdrant_client().scroll(
        collection_name=get_collection_name(),
        scroll_filter=_document_filter(user_id, document_type, document_id),
        limit=1000,
        with_payload=True,
        with_vectors=with_vectors,
    )
    return sorted(points, key=lambda point: point.payload["chunk_index"])


def indexed_document_ids(user_id: int, document_type: str) -> set[int]:
    """IDs of this user's documents of one type that have at least one chunk in the index."""
    ids: set[int] = set()
    offset = None
    while True:
        points, offset = get_qdrant_client().scroll(
            collection_name=get_collection_name(),
            scroll_filter=Filter(
                must=[
                    _match("user_id", user_id),
                    _match("document_type", document_type),
                    _match("chunk_index", 0),
                ]
            ),
            limit=500,
            offset=offset,
            with_payload=["document_id"],
            with_vectors=False,
        )
        ids.update(point.payload["document_id"] for point in points)
        if offset is None:
            return ids


def search_chunks(
    query_vector: list[float],
    user_id: int,
    limit: int = 5,
    document_type: str | None = None,
    documents: list[tuple[str, int]] | None = None,
):
    """Search a user's chunks, optionally restricted to a document type or to specific documents."""
    must = [_match("user_id", user_id)]

    if document_type is not None:
        must.append(_match("document_type", document_type))

    should = None
    if documents:
        should = [
            Filter(
                must=[
                    _match("document_type", doc_type),
                    _match("document_id", doc_id),
                ]
            )
            for doc_type, doc_id in documents
        ]

    response = get_qdrant_client().query_points(
        collection_name=get_collection_name(),
        query=query_vector,
        limit=limit,
        query_filter=Filter(must=must, should=should),
        with_payload=True,
    )

    return response.points
