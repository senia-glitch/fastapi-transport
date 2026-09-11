"""fastbase — thin infrastructure over FastAPI for a uniform API layer.

Public API:
  - make_app / start      — single entry point for the project.
  - BaseAppSettings       — settings model (subclass to add your own fields).
  - exception classes     — subclass to define domain errors.
  - install_exception_handlers — for those building FastAPI by hand.
  - AccessLogMiddleware, RequestIdMiddleware, health_router — building blocks.

Importing this module has no side effects.
"""

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
from fastbase.settings import BaseAppSettings
from fastbase.startup import make_app, start

__all__ = [
    # entry point
    "make_app",
    "start",
    # settings
    "BaseAppSettings",
    # exceptions
    "BaseHTTPError",
    "NotFoundError",
    "ValidationError",
    "ConflictError",
    "UnauthorizedError",
    "ForbiddenError",
    "InternalError",
    "install_exception_handlers",
    # building blocks
    "AccessLogMiddleware",
    "RequestIdMiddleware",
    "health_router",
]

__version__ = "0.2.0"