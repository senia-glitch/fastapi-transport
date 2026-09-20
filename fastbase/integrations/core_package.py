"""Integration with core-package and event-infra.

Provides:
  - install_core_handlers: register an exception handler for CoreError.
  - core_event_lifespan:   async lifespan that starts event-infra and core-package.

All imports of `core` and `run_infrastructure` are lazy, inside functions.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from fastbase.errors.codes import merge_mappings
from fastbase.settings import BaseAppSettings

logger = logging.getLogger("fastbase.integrations.core")


def install_core_handlers(app: FastAPI, settings: BaseAppSettings) -> None:
    """Register an exception handler for core.exceptions.CoreError.

    Does nothing if core-package is not installed.
    """
    try:
        from core.exceptions import CoreError
    except ImportError:
        return

    mapping = merge_mappings(settings.error_codes)
    fallback = settings.error_code_fallback

    @app.exception_handler(CoreError)
    async def _core_error_handler(
        request: Request, exc: CoreError
    ) -> JSONResponse:
        status = getattr(exc, "http_status", None)
        if status is None:
            status = 500

        code = getattr(exc, "code", None)
        if code is None:
            for cls in type(exc).__mro__:
                if cls.__name__ in mapping:
                    code = mapping[cls.__name__]
                    break
        if code is None:
            code = fallback

        return JSONResponse(
            status_code=status,
            content=jsonable_encoder(
                {
                    "success": False,
                    "error": {
                        "code": code,
                        "message": str(exc),
                        "details": None,
                    },
                }
            ),
        )


def core_event_lifespan(settings: BaseAppSettings) -> Any:
    """Return an asynccontextmanager that starts event-infra then core-package.

    Order on startup:
      1. start_infrastructure() -> EventRouter
      2. start_core(router=router, discover=settings.core_discover)

    Order on shutdown:
      1. reset_core()
      2. router.shutdown()
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            from run_infrastructure import start_infrastructure
        except ImportError as e:
            raise ImportError(
                "FAT_INTEGRATIONS=core,event-infra requires event-infra. "
                "Install with: pip install 'fastbase[full]'"
            ) from e

        try:
            from core import reset_core, start_core
        except ImportError as e:
            raise ImportError(
                "FAT_INTEGRATIONS=core,event-infra requires core-package. "
                "Install with: pip install 'fastbase[full]'"
            ) from e

        logger.info("Starting event-infra...")
        router = await start_infrastructure()

        discover = settings.core_discover or None
        if not discover:
            logger.warning(
                "FAT_CORE_DISCOVER is empty — scenarios must be "
                "registered manually before the first run()."
            )

        logger.info("Starting core-package (discover=%r)...", discover)
        await start_core(router=router, discover=discover)

        logger.info("Integrations started.")

        try:
            yield
        finally:
            logger.info("Shutting down integrations...")
            try:
                reset_core()
            except Exception as e:
                logger.error("reset_core failed: %s", e)
            try:
                await router.shutdown()
            except Exception as e:
                logger.error("router.shutdown failed: %s", e)
            logger.info("Integrations shut down.")

    return lifespan