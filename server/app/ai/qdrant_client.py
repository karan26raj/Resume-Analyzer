from functools import lru_cache

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PayloadSchemaType, VectorParams

from app.core.config import settings


PAYLOAD_INDEXES = {
    "user_id": PayloadSchemaType.INTEGER,
    "document_type": PayloadSchemaType.KEYWORD,
    "document_id": PayloadSchemaType.INTEGER,
    "chunk_index": PayloadSchemaType.INTEGER,
}


@lru_cache
def get_qdrant_client() -> QdrantClient:
    if settings.QDRANT_LOCATION:
        return QdrantClient(location=settings.QDRANT_LOCATION)

    if settings.QDRANT_URL:
        return QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)

    return QdrantClient(
        host=settings.QDRANT_HOST,
        port=settings.QDRANT_PORT
    )


def get_collection_name() -> str:
    return settings.QDRANT_COLLECTION_NAME


def ensure_collection() -> None:
    client = get_qdrant_client()
    collection_name = get_collection_name()

    if not client.collection_exists(collection_name):
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=settings.EMBEDDING_DIMENSIONS,
                distance=Distance.COSINE
            )
        )
    else:
        configured_size = client.get_collection(collection_name).config.params.vectors.size
        if configured_size != settings.EMBEDDING_DIMENSIONS:
            raise RuntimeError(
                f"Qdrant collection '{collection_name}' stores {configured_size}-dimension vectors "
                f"but EMBEDDING_DIMENSIONS is {settings.EMBEDDING_DIMENSIONS}"
            )

    for field_name, field_schema in PAYLOAD_INDEXES.items():
        client.create_payload_index(
            collection_name=collection_name,
            field_name=field_name,
            field_schema=field_schema,
        )
