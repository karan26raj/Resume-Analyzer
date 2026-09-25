"""Logging shared by the API and the worker; every record carries the current request ID."""
import json
import logging
import sys
from contextvars import ContextVar


request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

TEXT_FORMAT = "%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s"

_original_factory = logging.getLogRecordFactory()


def _record_factory(*args, **kwargs) -> logging.LogRecord:
    record = _original_factory(*args, **kwargs)
    record.request_id = request_id_var.get()
    return record


# Installed at import so every record (including ones captured by pytest) has request_id.
logging.setLogRecordFactory(_record_factory)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", "-"),
            "message": record.getMessage(),
        }
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False)


_HANDLER_NAME = "resume-analyzer"


def configure_logging(level: str = "INFO", json_format: bool = False) -> None:
    """Send application logs to stderr. Safe to call more than once."""
    root = logging.getLogger()
    root.setLevel(level.upper())

    handler = next((h for h in root.handlers if h.get_name() == _HANDLER_NAME), None)
    if handler is None:
        handler = logging.StreamHandler(sys.stderr)
        handler.set_name(_HANDLER_NAME)
        root.addHandler(handler)
    handler.setFormatter(JsonFormatter() if json_format else logging.Formatter(TEXT_FORMAT))

    for name in ("httpx", "httpcore", "google_genai", "urllib3"):
        logging.getLogger(name).setLevel(logging.WARNING)
