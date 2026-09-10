"""fastbase.errors — domain exceptions, numeric codes, and FastAPI handlers."""

from fastbase.errors.codes import (
    DEFAULT_ERROR_CODES,
    DEFAULT_FALLBACK_CODE,
    merge_mappings,
    resolve_code,
)
from fastbase.errors.exceptions import (
    BaseHTTPError,
    ConflictError,
    ForbiddenError,
    InternalError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from fastbase.errors.handlers import install_exception_handlers

__all__ = [
    "BaseHTTPError",
    "NotFoundError",
    "ValidationError",
    "ConflictError",
    "UnauthorizedError",
    "ForbiddenError",
    "InternalError",
    "DEFAULT_ERROR_CODES",
    "DEFAULT_FALLBACK_CODE",
    "merge_mappings",
    "resolve_code",
    "install_exception_handlers",
]