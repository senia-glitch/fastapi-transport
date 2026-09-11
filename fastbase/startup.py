"""make_app and start — the single entry point for a fastbase project.

Usage (from a user's app/main.py):

    from fastbase import make_app, start

    app = make_app()

    if __name__ == "__main__":
        start()

All behaviour is driven by env settings (prefix FAT_, file .env.fastbase).
"""

from __future__ import annotations

import logging
from typing import Any

import uvicorn
from fastapi import FastAPI

from fastbase.errors import install_exception_handlers
from fastbase.integrations import make_integrations_lifespan
from fastbase.logging_setup import configure_logging
from fastbase.middleware import AccessLogMiddleware, RequestIdMiddleware
from fastbase.routes_discovery import discover_routers
from fastbase.routing import health_router
from fastbase.settings import BaseAppSettings

logger = logging.getLogger("fastbase.startup")

_ALLOWED_INTEGRATIONS = {"core", "event-infra"}


def make_app() -> FastAPI:
    """Build the FastAPI application from environment settings.

    Reads:
      FAT_TITLE, FAT_VERSION, FAT_DESCRIPTION, FAT_API_PREFIX,
      FAT_DOCS_URL, FAT_OPENAPI_URL, FAT_REDOC_URL,
      FAT_REQUEST_ID_ENABLED, FAT_REQUEST_ID_HEADER,
      FAT_LOG_LEVEL, FAT_LOG_FORMAT, FAT_ACCESS_LOG,
      FAT_ERROR_CODES, FAT_ERROR_CODE_FALLBACK,
      FAT_ROUTES_PACKAGE, FAT_INTEGRATIONS, FAT_CORE_DISCOVER.

    Returns a fully wired FastAPI app:
      - middleware (access-log + request-id)
      - exception handlers (uniform error envelope)
      - core-package exception handler (if integrations enabled)
      - health router
      - auto-discovered routers from FAT_ROUTES_PACKAGE
      - async lifespan with integrations startup/shutdown
    """
    settings = BaseAppSettings()
    return _build_app(settings)


def start() -> None:
    """Run uvicorn using settings from the environment.

    Reads:
      FAT_APP_PATH, FAT_HOST, FAT_PORT, FAT_RELOAD, FAT_WORKERS,
      FAT_BACKLOG, FAT_TIMEOUT_KEEP_ALIVE, FAT_ROOT_PATH,
      FAT_LOG_LEVEL, FAT_ENV_FILE.

    Blocks the current process.
    """
    settings = BaseAppSettings()
    _run_uvicorn(settings)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_app(settings: BaseAppSettings) -> FastAPI:
    configure_logging(settings)

    if settings.reload and settings.workers > 1:
        logger.warning(
            "FAT_RELOAD=true with FAT_WORKERS>1 — uvicorn will use 1 worker."
        )

    integrations = settings.integrations_list
    _validate_integrations(integrations)

    lifespan = make_integrations_lifespan(settings, integrations)

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
        app.add_middleware(
            RequestIdMiddleware, header=settings.request_id_header
        )

    install_exception_handlers(app, settings)

    if "core" in integrations:
        # Lazy import: the module only exists if core-package is installed.
        from fastbase.integrations.core_package import install_core_handlers

        install_core_handlers(app, settings)

    # Auto-discover routers. If discovery yields nothing (empty package,
    # missing package, or all modules skipped), fall back to health_router
    # so the app is never empty.
    discovered = (
        list(discover_routers(settings.routes_package))
        if settings.routes_package
        else []
    )

    if discovered:
        for router, module_prefix in discovered:
            full_prefix = settings.api_prefix + (module_prefix or "")
            app.include_router(router, prefix=full_prefix)
    else:
        app.include_router(health_router, prefix=settings.api_prefix)
        if settings.routes_package:
            logger.warning(
                "No routers discovered in %r — mounted health_router only.",
                settings.routes_package,
            )

    return app


def _validate_integrations(integrations: list[str]) -> None:
    unknown = set(integrations) - _ALLOWED_INTEGRATIONS
    if unknown:
        raise ValueError(
            f"Unknown FAT_INTEGRATIONS values: {sorted(unknown)}. "
            f"Allowed: {sorted(_ALLOWED_INTEGRATIONS)} or empty string."
        )
    if integrations and set(integrations) != _ALLOWED_INTEGRATIONS:
        raise ValueError(
            f"FAT_INTEGRATIONS must be either empty or "
            f"'core,event-infra' (got {integrations})."
        )


def _run_uvicorn(settings: BaseAppSettings) -> None:
    kwargs: dict[str, Any] = dict(
        host=settings.host,
        port=settings.port,
        backlog=settings.backlog,
        timeout_keep_alive=settings.timeout_keep_alive,
        root_path=settings.root_path,
        log_level=settings.log_level,
        access_log=False,  # handled by AccessLogMiddleware
        reload=settings.reload,
        workers=settings.workers if not settings.reload else 1,
    )
    if settings.env_file:
        kwargs["env_file"] = settings.env_file

    uvicorn.run(settings.app_path, **kwargs)