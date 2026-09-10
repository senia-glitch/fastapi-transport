"""create_app — build a FastAPI application with fastbase defaults."""

import logging
from collections.abc import Callable

from fastapi import FastAPI

from fastbase.errors import install_exception_handlers
from fastbase.logging_setup import configure_logging
from fastbase.middleware import AccessLogMiddleware, RequestIdMiddleware
from fastbase.settings import BaseAppSettings

logger = logging.getLogger("fastbase.app")


def create_app(
    settings: BaseAppSettings,
    routers: list,
    *,
    lifespan: Callable | None = None,
) -> FastAPI:
    """Create a FastAPI app wired with the fastbase conventions.

    Order of operations:
      1. configure logging;
      2. create the FastAPI app;
      3. add middlewares (AccessLog first, then RequestId — see below);
      4. install exception handlers;
      5. include every router under `settings.api_prefix`.

    Starlette applies middleware in reverse order of registration; the last
    added is the outermost. We add AccessLog first, RequestId last, so
    RequestId wraps AccessLog (request id is available inside access log and
    is set on the response even if access log fails).
    """
    configure_logging(settings)

    if settings.reload and settings.workers > 1:
        logger.warning(
            "FAT_RELOAD=true with FAT_WORKERS>1 — uvicorn will use 1 worker."
        )

    app = FastAPI(
        title=settings.title,
        version=settings.version,
        description=settings.description,
        docs_url=settings.docs_url,
        openapi_url=settings.openapi_url,
        redoc_url=settings.redoc_url,
        lifespan=lifespan,
    )

    if settings.access_log:
        app.add_middleware(AccessLogMiddleware)
    if settings.request_id_enabled:
        app.add_middleware(RequestIdMiddleware, header=settings.request_id_header)

    install_exception_handlers(app, settings)

    for router in routers:
        app.include_router(router, prefix=settings.api_prefix)

    return app