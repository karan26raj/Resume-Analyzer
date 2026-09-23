from qdrant_client import QdrantClient


def test_qdrant_connection():

    client = QdrantClient(
        host="localhost",
        port=6333
    )

    collections = client.get_collections()

    assert collections is not None