"""Logging configuration for the fastbase package.

Uses stdlib logging only. Root logger name: `fastbase`.
Supports two formats: `plain` and `json`.
Request-ID is injected into every log record via `RequestIdFilter`.

The request id is kept in a *private* ContextVar (implementation detail of
the logging layer). It is never exposed to endpoints — endpoints read it
from `request.state.request_id`.
"""

import json
import logging
from contextvars import ContextVar, Token
from datetime import datetime, timezone

from fastbase.settings import BaseAppSettings

_request_id_ctx: ContextVar[str | None] = ContextVar(
    "fastbase_request_id", default=None
)


def get_request_id() -> str | None:
    """Return the current request id, or None if outside a request."""
    return _request_id_ctx.get()


def set_request_id(request_id: str) -> Token:
    """Set request id in the current context. Returns a reset token."""
    return _request_id_ctx.set(request_id)


def reset_request_id(token: Token) -> None:
    """Restore the previous request id value using a token."""
    _request_id_ctx.reset(token)


class RequestIdFilter(logging.Filter):
    """Inject a `request_id` attribute into every log record.

    If the caller set `record.request_id` explicitly via `extra=`, that value
    wins. Otherwise the value comes from the ContextVar (set by
    RequestIdMiddleware). Falls back to "-".
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = _request_id_ctx.get() or "-"
        return True


class PlainFormatter(logging.Formatter):
    """Plain-text formatter.

    Example:
        2026-09-10 12:34:56 INFO  [req=0f8c...] fastbase.access: GET /health 200 3ms
    """

    def __init__(self) -> None:
        super().__init__(
            fmt=(
                "%(asctime)s %(levelname)-5s [req=%(request_id)s] "
                "%(name)s: %(message)s"
            ),
            datefmt="%Y-%m-%d %H:%M:%S",
        )


class JsonFormatter(logging.Formatter):
    """One JSON object per log record."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(settings: BaseAppSettings) -> None:
    """Configure the `fastbase` logger according to settings.

    Idempotent: replaces handlers on every call. Sets `propagate = False`
    so that package logs do not duplicate at the root logger.
    """
    level = logging.getLevelName(settings.log_level.upper())
    if not isinstance(level, int):
        level = logging.INFO

    logger = logging.getLogger("fastbase")
    logger.setLevel(level)
    logger.propagate = False

    for h in list(logger.handlers):
        logger.removeHandler(h)

    handler = logging.StreamHandler()
    handler.setLevel(level)
    if settings.log_format == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(PlainFormatter())
    handler.addFilter(RequestIdFilter())

    logger.addHandler(handler)