from google.genai import types

from app.ai.gemini import GeminiNotConfiguredError, get_gemini_client
from app.core.config import settings


EMBEDDING_BATCH_SIZE = 100

DOCUMENT_TASK_TYPE = "RETRIEVAL_DOCUMENT"
QUERY_TASK_TYPE = "RETRIEVAL_QUERY"


class EmbeddingServiceError(Exception):
    pass


def chunk_text(text: str) -> list[str]:
    words = text.split()

    size = settings.EMBEDDING_CHUNK_SIZE_WORDS
    overlap = settings.EMBEDDING_CHUNK_OVERLAP_WORDS

    if not words:
        return []

    if size <= 0 or overlap < 0 or overlap >= size:
        raise EmbeddingServiceError(
            "Invalid embedding chunk configuration"
        )

    chunks = [
        " ".join(words[start:start + size])
        for start in range(
            0,
            len(words),
            size - overlap
        )
    ]

    return chunks[:settings.MAX_EMBEDDING_CHUNKS]


def create_embeddings(
    texts: list[str],
    task_type: str = DOCUMENT_TASK_TYPE,
) -> tuple[list[list[float]], None]:
    try:
        client = get_gemini_client()
    except GeminiNotConfiguredError as error:
        raise EmbeddingServiceError(str(error))

    vectors: list[list[float]] = []

    try:
        for start in range(0, len(texts), EMBEDDING_BATCH_SIZE):
            batch = texts[start:start + EMBEDDING_BATCH_SIZE]

            response = client.models.embed_content(
                model=settings.GEMINI_EMBEDDING_MODEL,
                contents=batch,
                config=types.EmbedContentConfig(
                    task_type=task_type,
                    output_dimensionality=settings.EMBEDDING_DIMENSIONS,
                ),
            )

            vectors.extend(
                embedding.values
                for embedding in response.embeddings or []
            )

    except Exception as error:
        raise EmbeddingServiceError(
            f"Gemini embedding failed: {str(error)}"
        )

    if len(vectors) != len(texts):
        raise EmbeddingServiceError(
            "Gemini returned incomplete embeddings"
        )

    return vectors, None
