"""fastbase — thin infrastructure over FastAPI for a uniform API layer.

Public API is re-exported here. Importing this module has no side effects.
"""

from fastbase.app import create_app
from fastbase.errors import (
    BaseHTTPError,
    ConflictError,
    ForbiddenError,
    InternalError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
    install_exception_handlers,
)
from fastbase.middleware import AccessLogMiddleware, RequestIdMiddleware
from fastbase.routing import health_router
from fastbase.runner import run_api
from fastbase.settings import BaseAppSettings

__all__ = [
    "create_app",
    "BaseHTTPError",
    "NotFoundError",
    "ValidationError",
    "ConflictError",
    "UnauthorizedError",
    "ForbiddenError",
    "InternalError",
    "install_exception_handlers",
    "RequestIdMiddleware",
    "AccessLogMiddleware",
    "health_router",
    "run_api",
    "BaseAppSettings",
]

__version__ = "0.1.0"