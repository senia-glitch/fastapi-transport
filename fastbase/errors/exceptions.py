"""Domain exception hierarchy.

Every exception carries:
  - http_status: int   — the HTTP status code to emit.
  - message: str       — default human-readable message.
  - default_code: int | None — optional explicit numeric code.

The constructor allows overriding message, details and numeric code per instance.
"""

from typing import Any


class BaseHTTPError(Exception):
    """Base class for all fastbase domain exceptions."""

    http_status: int = 500
    message: str = "Internal server error"
    default_code: int | None = None

    def __init__(
        self,
        message: str | None = None,
        details: Any | None = None,
        code: int | None = None,
    ) -> None:
        self.message = message or self.message
        self.details = details
        self.code = code
        super().__init__(self.message)


class NotFoundError(BaseHTTPError):
    http_status = 404
    message = "Not found"


class ValidationError(BaseHTTPError):
    http_status = 422
    message = "Validation failed"


class ConflictError(BaseHTTPError):
    http_status = 409
    message = "Conflict"


class UnauthorizedError(BaseHTTPError):
    http_status = 401
    message = "Unauthorized"


class ForbiddenError(BaseHTTPError):
    http_status = 403
    message = "Forbidden"


class InternalError(BaseHTTPError):
    http_status = 500
    message = "Internal server error"