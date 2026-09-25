import logging
from functools import lru_cache

from google import genai
from google.genai import errors, types

from app.core.config import settings


logger = logging.getLogger(__name__)

FALLBACK_STATUS_CODES = {404, 429, 500, 502, 503, 504}


class GeminiNotConfiguredError(Exception):
    pass


@lru_cache
def get_gemini_client() -> genai.Client:
    if not settings.GEMINI_API_KEY:
        raise GeminiNotConfiguredError("Gemini API is not configured")

    return genai.Client(
        api_key=settings.GEMINI_API_KEY,
        http_options=types.HttpOptions(
            timeout=settings.GEMINI_TIMEOUT_SECONDS * 1000,
            retry_options=types.HttpRetryOptions(
                attempts=settings.GEMINI_MAX_RETRIES,
                http_status_codes=[429, 500, 502, 503, 504],
            ),
        ),
    )


def candidate_models() -> list[str]:
    return list(dict.fromkeys([settings.GEMINI_MODEL, *settings.GEMINI_FALLBACK_MODELS]))


def generate_content_with_fallback(
    *,
    contents: str,
    config: types.GenerateContentConfig,
) -> tuple[types.GenerateContentResponse, str]:
    client = get_gemini_client()
    models = candidate_models()

    for index, model in enumerate(models):
        try:
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
            return response, model
        except errors.APIError as error:
            is_last = index == len(models) - 1
            if is_last or error.code not in FALLBACK_STATUS_CODES:
                raise
            logger.warning(
                "Gemini model %s failed with %s; falling back to %s",
                model,
                error.code,
                models[index + 1],
            )

    raise AssertionError("unreachable: candidate_models() is never empty")
