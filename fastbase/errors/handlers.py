"""FastAPI exception handlers producing the unified error envelope.

Envelope:

    {
      "success": false,
      "error": {
        "code": <int>,
        "message": <str>,
        "details": <null | any JSON>
      }
    }
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from fastbase.errors.codes import merge_mappings, resolve_code
from fastbase.errors.exceptions import BaseHTTPError
from fastbase.settings import BaseAppSettings

logger = logging.getLogger("fastbase.errors")


def _error_response(
    status: int,
    code: int,
    message: str,
    details: Any,
    *,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content=jsonable_encoder(
            {
                "success": False,
                "error": {
                    "code": code,
                    "message": message,
                    "details": details,
                },
            }
        ),
        headers=headers,
    )


def _code_for_http_status(
    status: int,
    mapping: dict[str, int],
    fallback: int,
) -> int:
    if status == 404:
        return mapping.get("NotFoundError", fallback)
    if status == 401:
        return mapping.get("UnauthorizedError", fallback)
    if status == 403:
        return mapping.get("ForbiddenError", fallback)
    if status == 409:
        return mapping.get("ConflictError", fallback)
    return mapping.get("BaseHTTPError", fallback)


def install_exception_handlers(
    app: FastAPI,
    settings: BaseAppSettings,
) -> None:
    """Register package exception handlers on a FastAPI app.

    Note: we register the handler for ``starlette.exceptions.HTTPException``
    (the base class), not ``fastapi.exceptions.HTTPException`` (the subclass).
    Starlette raises the base class when no route matches; FastAPI raises the
    subclass from endpoints. Registering the base class catches both.
    """
    mapping = merge_mappings(settings.error_codes)
    fallback = settings.error_code_fallback

    @app.exception_handler(BaseHTTPError)
    async def _domain(request: Request, exc: BaseHTTPError) -> JSONResponse:
        code = resolve_code(exc, mapping, fallback)
        return _error_response(exc.http_status, code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def _validation(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        code = mapping.get("ValidationError", fallback)
        details = jsonable_encoder(exc.errors())
        return _error_response(422, code, "Validation failed", details)

    @app.exception_handler(StarletteHTTPException)
    async def _http(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        code = _code_for_http_status(exc.status_code, mapping, fallback)
        return _error_response(
            exc.status_code,
            code,
            str(exc.detail),
            None,
            headers=exc.headers,
        )

    # Design note: this catch-all is intentional.  The uniform envelope
    # guarantees that *every* HTTP response has ``{"success": false, ...}``
    # shape.  ``BaseException`` subclasses (KeyboardInterrupt, SystemExit)
    # are NOT caught here — Starlette never routes them to this handler.
    # ``MemoryError`` and other fatal ``Exception`` subclasses ARE caught;
    # returning 500 is preferable to crashing the ASGI worker.
    @app.exception_handler(Exception)
    async def _internal(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception")
        return _error_response(500, fallback, "Internal server error", None)