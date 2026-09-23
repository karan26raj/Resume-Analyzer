import math

from google import genai

from app.core.config import settings


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
) -> tuple[list[list[float]], None]:

    if not settings.GEMINI_API_KEY:
        raise EmbeddingServiceError(
            "Gemini API is not configured"
        )

    try:
        client = genai.Client(
            api_key=settings.GEMINI_API_KEY
        )

        vectors = []

        for text in texts:
            response = client.models.embed_content(
                model=settings.GEMINI_EMBEDDING_MODEL,
                contents=text,
            )

            vectors.append(
                response.embeddings[0].values
            )

        return vectors, None

    except Exception as error:
        raise EmbeddingServiceError(
            f"Gemini embedding failed: {str(error)}"
        )


def cosine_similarity(
    left: list[float],
    right: list[float]
) -> float:

    if len(left) != len(right) or not left:
        return 0.0

    denominator = (
        math.sqrt(sum(x * x for x in left))
        *
        math.sqrt(sum(x * x for x in right))
    )

    if denominator == 0:
        return 0.0

    return (
        sum(a * b for a, b in zip(left, right))
        / denominator
    )