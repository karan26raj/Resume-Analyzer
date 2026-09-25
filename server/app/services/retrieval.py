import logging
from dataclasses import dataclass, field

from app.ai.vector_store import search_chunks
from app.core.config import settings
from app.services.embeddings import QUERY_TASK_TYPE, create_embeddings
from app.services.indexing import EmptyDocumentError, index_document


logger = logging.getLogger(__name__)

TOP_K_FOR_SIMILARITY = 3


class RetrievalError(Exception):
    pass


@dataclass
class RetrievedEvidence:
    passages: list[dict] = field(default_factory=list)
    similarity: float | None = None


def retrieve_resume_evidence(
    *,
    user_id: int,
    resume_id: int,
    resume_text: str,
    job_text: str,
    limit: int | None = None,
) -> RetrievedEvidence:
    limit = limit or settings.ANALYSIS_EVIDENCE_CHUNKS
    query = job_text[: settings.MAX_QUERY_EMBED_CHARACTERS]

    try:
        query_vectors, _ = create_embeddings([query], task_type=QUERY_TASK_TYPE)
        documents = [("resume", resume_id)]

        hits = search_chunks(query_vectors[0], user_id=user_id, limit=limit, documents=documents)
        if not hits:
            index_document(
                user_id=user_id,
                document_type="resume",
                document_id=resume_id,
                text=resume_text,
            )
            hits = search_chunks(query_vectors[0], user_id=user_id, limit=limit, documents=documents)
    except EmptyDocumentError:
        return RetrievedEvidence()
    except Exception as error:
        raise RetrievalError(str(error)) from error

    passages = [
        {
            "chunk_index": hit.payload["chunk_index"],
            "content": hit.payload["content"],
            "score": round(float(hit.score), 4),
        }
        for hit in hits
    ]

    top_scores = [passage["score"] for passage in passages[:TOP_K_FOR_SIMILARITY]]
    similarity = round(sum(top_scores) / len(top_scores), 4) if top_scores else None

    return RetrievedEvidence(passages=passages, similarity=similarity)
