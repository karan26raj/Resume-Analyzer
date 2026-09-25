"""Request IDs, access logging and a safety net for unhandled errors.

A plain ASGI middleware (not BaseHTTPMiddleware) so the request ID context variable reaches the
endpoint, its dependencies and its background tasks.
"""
import logging
import re
import time
import uuid

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.errors import INTERNAL_ERROR_MESSAGE, error_response
from app.core.logging import request_id_var


access_logger = logging.getLogger("app.access")
error_logger = logging.getLogger("app.errors")

REQUEST_ID_HEADER = b"x-request-id"
# Accept a caller's ID (e.g. from a proxy or the frontend) only if it is short and log-safe.
VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
QUIET_PATHS = {"/health"}


def _incoming_request_id(scope: Scope) -> str:
    for name, value in scope.get("headers", []):
        if name == REQUEST_ID_HEADER:
            candidate = value.decode("latin-1")
            if VALID_REQUEST_ID.match(candidate):
                return candidate
            break
    return uuid.uuid4().hex


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = _incoming_request_id(scope)
        # request.state.request_id, readable even after this middleware has returned.
        scope.setdefault("state", {})["request_id"] = request_id
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        status_code = 500
        response_started = False

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code, response_started
            if message["type"] == "http.response.start":
                response_started = True
                status_code = message["status"]
                headers = [(k, v) for k, v in message.get("headers", []) if k.lower() != REQUEST_ID_HEADER]
                message = {**message, "headers": [*headers, (REQUEST_ID_HEADER, request_id.encode())]}
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        except Exception:
            error_logger.exception("Unhandled error on %s %s", scope["method"], scope["path"])
            if not response_started:
                response = error_response(None, 500, INTERNAL_ERROR_MESSAGE)
                await response(scope, receive, send)
                status_code = 500
        finally:
            duration_ms = (time.perf_counter() - started) * 1000
            level = logging.DEBUG if scope["path"] in QUIET_PATHS else logging.INFO
            access_logger.log(level, "%s %s %s %.0fms", scope["method"], scope["path"], status_code, duration_ms)
            request_id_var.reset(token)
