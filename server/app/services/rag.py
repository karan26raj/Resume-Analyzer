import textwrap

from google import genai

from app.core.config import settings
from app.services.embeddings import (
    create_embeddings,
    EmbeddingServiceError,
)
from app.ai.vector_store import search_chunks


class RAGServiceError(Exception):
    pass

SYSTEM_PROMPT = """You are an AI Career Assistant embedded in a résumé/job-matching platform. You help users understand their résumé, job descriptions, and career documents using ONLY the retrieved context provided to you.

## Core Rules

1. **Grounding**: Answer using ONLY the information in the <context> below. Never use outside knowledge about companies, salaries, or job market trends unless it appears in the context.
2. **No hallucination**: If the context is insufficient, partial, or ambiguous, say so explicitly rather than filling gaps with assumptions.
3. **Partial answers are allowed**: If the context answers part of the question, answer that part and clearly state what's missing — don't refuse the whole thing just because one sub-part is unanswerable.
4. **Cite your source**: When possible, reference which document/section the answer came from (e.g., "Based on your résumé's Experience section..." or "According to the JD you uploaded...").
5. **No fabricated specifics**: Never invent company names, dates, metrics, or skills not present in the context.

## Response Format

- Be concise and structured (use bullet points for lists like skills/gaps).
- For ATS/keyword-gap style questions, separate findings into: **Present**, **Missing**, **Suggested phrasing**.
- If asked something outside your scope (e.g., legal advice, unrelated general knowledge), redirect the user politely.

## Fallback Behavior

If the answer cannot be found in the context at all, respond with:
"I couldn't find that in your uploaded documents. You may want to upload [specific missing document type] or rephrase your question."

Never say generic phrases like "I don't know" without guidance on what to do next.

## Context

<context>
{retrieved_chunks}
</context>

## Conversation

<question>
{user_question}
</question>
"""

def ask_question(
    *,
    question: str,
    user_id: int,
    limit: int = 5,
):
    try:
        query_vectors, _ = create_embeddings(
            [question]
        )

        results = search_chunks(
            query_vector=query_vectors[0],
            user_id=user_id,
            limit=limit
        )

    except EmbeddingServiceError as error:
        raise RAGServiceError(str(error))

    except Exception as error:
        raise RAGServiceError(
            f"Vector search failed: {str(error)}"
        )

    context_parts = []

    for hit in results:

        payload = hit.payload

        context_parts.append(
            textwrap.dedent(
                f"""
                Document Type: {payload["document_type"]}
                Document ID: {payload["document_id"]}
                Chunk Index: {payload["chunk_index"]}

                Content:
                {payload["content"]}
                """
            )
        )

    context = "\n\n".join(context_parts)

    if not settings.GEMINI_API_KEY:
        raise RAGServiceError(
            "Gemini API is not configured"
        )

    try:
        client = genai.Client(
            api_key=settings.GEMINI_API_KEY
        )

        prompt = f"""
{SYSTEM_PROMPT}

CONTEXT:

{context}

QUESTION:

{question}
"""

        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt
        )

        answer = response.text.strip()

        sources = []

        for hit in results:

            payload = hit.payload

            sources.append(
                {
                    "document_type": payload["document_type"],
                    "document_id": payload["document_id"],
                    "chunk_index": payload["chunk_index"]
                }
            )

        return answer, sources

    except Exception as error:
        raise RAGServiceError(
            f"Gemini response failed: {str(error)}"
        )