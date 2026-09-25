import logging

import httpx
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from google.genai import errors as genai_errors
from qdrant_client.http.exceptions import ApiException as QdrantApiException
from sqlalchemy.exc import DBAPIError, OperationalError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.ai.gemini import GeminiNotConfiguredError
from app.core.logging import request_id_var


logger = logging.getLogger("app.errors")

ERROR_CODES = {
    400: "bad_request",
    401: "not_authenticated",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    413: "payload_too_large",
    422: "validation_error",
    429: "rate_limited",
    500: "internal_error",
    502: "upstream_error",
    503: "service_unavailable",
}

INTERNAL_ERROR_MESSAGE = "Something went wrong on our side. Please try again."


class ServiceFailure(Exception):
    def __init__(self, status_code: int, code: str, message: str, retry_after: int | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.retry_after = retry_after


def current_request_id(request: Request | None = None) -> str:
    if request is not None:
        request_id = getattr(request.state, "request_id", None)
        if request_id:
            return request_id
    return request_id_var.get()


def error_response(
    request: Request | None,
    status_code: int,
    detail,
    *,
    code: str | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    request_id = current_request_id(request)
    return JSONResponse(
        status_code=status_code,
        content={
            "detail": detail,
            "code": code or ERROR_CODES.get(status_code, "error"),
            "request_id": request_id,
        },
        headers={**(headers or {}), "X-Request-ID": request_id},
    )


def _causes(error: BaseException):
    seen = set()
    while error is not None and id(error) not in seen:
        seen.add(id(error))
        yield error
        error = error.__cause__ or error.__context__


def classify_failure(error: BaseException) -> ServiceFailure:
    for cause in _causes(error):
        if isinstance(cause, ServiceFailure):
            return cause
        if isinstance(cause, GeminiNotConfiguredError):
            return ServiceFailure(503, "ai_not_configured", "AI features are not configured on this server.")
        if isinstance(cause, genai_errors.APIError):
            if cause.code == 429:
                return ServiceFailure(
                    503, "ai_rate_limited", "The AI service is busy right now. Please try again in a minute.", 60
                )
            if cause.code and cause.code >= 500:
                return ServiceFailure(
                    503, "ai_unavailable", "The AI service is temporarily unavailable. Please try again shortly.", 30
                )
            break
        if isinstance(cause, httpx.TimeoutException):
            return ServiceFailure(503, "ai_unavailable", "The AI service took too long to respond. Please try again.", 30)
        if isinstance(cause, QdrantApiException):
            return ServiceFailure(
                503, "vector_store_unavailable", "Search is temporarily unavailable. Please try again shortly.", 30
            )
        if isinstance(cause, httpx.TransportError):
            return ServiceFailure(503, "service_unavailable", "A required service is unreachable. Please try again.", 30)

    if all(type(cause).__module__.startswith("app.") for cause in _causes(error)):
        return ServiceFailure(502, "upstream_error", str(error))
    return ServiceFailure(502, "upstream_error", "The AI service returned an unexpected response. Please try again.")


def upstream_failure(error: BaseException) -> ServiceFailure:
    failure = classify_failure(error)
    logger.warning("External service failure (%s): %s", failure.code, error, exc_info=error)
    return failure


async def _service_failure_handler(request: Request, exc: ServiceFailure) -> JSONResponse:
    headers = {"Retry-After": str(exc.retry_after)} if exc.retry_after else None
    return error_response(request, exc.status_code, exc.message, code=exc.code, headers=headers)


async def _http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return error_response(request, exc.status_code, exc.detail, headers=exc.headers)


async def _validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [{"loc": list(error["loc"]), "msg": error["msg"], "type": error["type"]} for error in exc.errors()]
    return error_response(request, status.HTTP_422_UNPROCESSABLE_CONTENT, errors)


async def _unavailable_handler(request: Request, exc: Exception) -> JSONResponse:
    return await _service_failure_handler(request, upstream_failure(exc))


async def _database_handler(request: Request, exc: DBAPIError) -> JSONResponse:
    if isinstance(exc, OperationalError) or exc.connection_invalidated:
        logger.error("Database unavailable: %s", exc, exc_info=exc)
        return error_response(
            request,
            503,
            "The database is temporarily unavailable. Please try again shortly.",
            code="database_unavailable",
            headers={"Retry-After": "30"},
        )
    logger.error("Database error", exc_info=exc)
    return error_response(request, 500, INTERNAL_ERROR_MESSAGE)


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ServiceFailure, _service_failure_handler)
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_handler)
    app.add_exception_handler(QdrantApiException, _unavailable_handler)
    app.add_exception_handler(httpx.TransportError, _unavailable_handler)
    app.add_exception_handler(DBAPIError, _database_handler)
