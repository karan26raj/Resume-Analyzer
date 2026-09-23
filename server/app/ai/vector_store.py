from qdrant_client.models import (
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue
)

from app.ai.qdrant_client import (
    client,
    COLLECTION_NAME
)


def upsert_chunks(
    user_id: int,
    document_type: str,
    document_id: int,
    chunks: list[str],
    embeddings: list[list[float]]
):

    points = []

    for index, (chunk, vector) in enumerate(
        zip(chunks, embeddings)
    ):
        points.append(
            PointStruct(
                id=document_id * 1000 + index,
                vector=vector,
                payload={
                    "user_id": user_id,
                    "document_type": document_type,
                    "document_id": document_id,
                    "chunk_index": index,
                    "content": chunk
                }
            )
        )

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points
    )


def search_chunks(
    query_vector: list[float],
    user_id: int,
    limit: int = 5
):

    response = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=limit,
        query_filter=Filter(
            must=[
                FieldCondition(
                    key="user_id",
                    match=MatchValue(value=user_id)
                )
            ]
        )
    )

    return response.points