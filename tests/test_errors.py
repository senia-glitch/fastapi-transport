"""Tests for the fastbase error module."""

import logging

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from fastbase.errors import (
    DEFAULT_ERROR_CODES,
    DEFAULT_FALLBACK_CODE,
    BaseHTTPError,
    ConflictError,
    ForbiddenError,
    InternalError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
    install_exception_handlers,
    merge_mappings,
    resolve_code,
)
from fastbase.settings import BaseAppSettings


# ---------------------------------------------------------------------------
# Exceptions hierarchy
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("cls", "status", "message"),
    [
        (BaseHTTPError, 500, "Internal server error"),
        (NotFoundError, 404, "Not found"),
        (ValidationError, 422, "Validation failed"),
        (ConflictError, 409, "Conflict"),
        (UnauthorizedError, 401, "Unauthorized"),
        (ForbiddenError, 403, "Forbidden"),
        (InternalError, 500, "Internal server error"),
    ],
)
def test_exception_defaults(cls, status, message) -> None:
    exc = cls()
    assert exc.http_status == status
    assert exc.message == message
    assert exc.details is None
    assert exc.code is None


def test_exception_overrides() -> None:
    exc = NotFoundError(message="User not found", details={"id": 5}, code=2001)
    assert exc.message == "User not found"
    assert exc.details == {"id": 5}
    assert exc.code == 2001
    assert str(exc) == "User not found"


def test_exception_empty_message_falls_back_to_class_default() -> None:
    exc = NotFoundError(message="")
    assert exc.message == "Not found"


# ---------------------------------------------------------------------------
# resolve_code
# ---------------------------------------------------------------------------


def test_resolve_explicit_code_wins() -> None:
    exc = NotFoundError(code=9999)
    assert resolve_code(exc, DEFAULT_ERROR_CODES, DEFAULT_FALLBACK_CODE) == 9999


def test_resolve_default_code_class_wins_over_mro() -> None:
    class Custom(NotFoundError):
        default_code = 7777

    assert resolve_code(Custom(), DEFAULT_ERROR_CODES, DEFAULT_FALLBACK_CODE) == 7777


def test_resolve_by_mro_inherits_parent_code() -> None:
    class UserNotFoundError(NotFoundError):
        message = "User not found"

    assert resolve_code(UserNotFoundError(), DEFAULT_ERROR_CODES, 3500) == 3001


def test_resolve_falls_back_when_no_match() -> None:
    class Weird(Exception):
        pass

    assert resolve_code(Weird(), DEFAULT_ERROR_CODES, 4242) == 4242


def test_resolve_explicit_none_code_falls_through() -> None:
    exc = NotFoundError(code=None)
    assert resolve_code(exc, DEFAULT_ERROR_CODES, 3500) == 3001


# ---------------------------------------------------------------------------
# merge_mappings
# ---------------------------------------------------------------------------


def test_merge_mappings_user_overrides_defaults() -> None:
    merged = merge_mappings({"NotFoundError": 2001})
    assert merged["NotFoundError"] == 2001
    assert merged["ValidationError"] == DEFAULT_ERROR_CODES["ValidationError"]
    assert merged["BaseHTTPError"] == DEFAULT_ERROR_CODES["BaseHTTPError"]


def test_merge_mappings_empty_user() -> None:
    assert merge_mappings({}) == DEFAULT_ERROR_CODES


def test_merge_mappings_adds_new_key() -> None:
    merged = merge_mappings({"UserNotFoundError": 2001})
    assert merged["UserNotFoundError"] == 2001


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


def _client(app: FastAPI, *, raise_server_exceptions: bool = True) -> TestClient:
    return TestClient(app, raise_server_exceptions=raise_server_exceptions)


def _app_with_handlers(settings: BaseAppSettings | None = None) -> FastAPI:
    app = FastAPI()
    install_exception_handlers(app, settings or BaseAppSettings())
    return app


def test_domain_error_envelope() -> None:
    app = _app_with_handlers()

    @app.get("/boom")
    async def boom() -> None:
        raise NotFoundError(message="User not found", details={"id": 5})

    r = _client(app).get("/boom")
    assert r.status_code == 404
    assert r.json() == {
        "success": False,
        "error": {
            "code": 3001,
            "message": "User not found",
            "details": {"id": 5},
        },
    }


def test_domain_error_custom_code_via_settings() -> None:
    settings = BaseAppSettings(error_codes={"UserNotFoundError": 2001})
    app = _app_with_handlers(settings)

    class UserNotFoundError(NotFoundError):
        message = "User not found"

    @app.get("/u")
    async def u() -> None:
        raise UserNotFoundError()

    r = _client(app).get("/u")
    assert r.status_code == 404
    body = r.json()
    assert body["error"]["code"] == 2001
    assert body["error"]["message"] == "User not found"


def test_validation_error_envelope() -> None:
    app = _app_with_handlers()

    class Item(BaseModel):
        n: int

    @app.post("/items")
    async def create(item: Item) -> dict:
        return {"n": item.n}

    r = _client(app).post("/items", json={"n": "not-an-int"})
    assert r.status_code == 422
    body = r.json()
    assert body["success"] is False
    assert body["error"]["code"] == 3002
    assert body["error"]["message"] == "Validation failed"
    assert isinstance(body["error"]["details"], list)
    assert body["error"]["details"], "details must contain validation errors"


@pytest.mark.parametrize(
    ("status", "expected_code"),
    [
        (404, 3001),
        (401, 3004),
        (403, 3005),
        (409, 3003),
        (500, 3000),
    ],
)
def test_http_exception_code_mapping(status: int, expected_code: int) -> None:
    app = _app_with_handlers()

    @app.get("/h")
    async def h() -> None:
        raise HTTPException(status_code=status, detail="nope")

    r = _client(app).get("/h")
    assert r.status_code == status
    body = r.json()
    assert body["success"] is False
    assert body["error"]["code"] == expected_code
    assert body["error"]["message"] == "nope"


def test_http_exception_preserves_headers() -> None:
    app = _app_with_handlers()

    @app.get("/auth")
    async def auth() -> None:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )

    r = _client(app).get("/auth")
    assert r.status_code == 401
    assert r.headers.get("WWW-Authenticate") == "Bearer"


def test_http_exception_with_dict_detail_does_not_crash() -> None:
    app = _app_with_handlers()

    @app.get("/d")
    async def d() -> None:
        raise HTTPException(status_code=400, detail={"reason": "bad"})

    r = _client(app).get("/d")
    assert r.status_code == 400
    body = r.json()
    assert body["success"] is False
    assert "reason" in body["error"]["message"]


def test_unhandled_exception_returns_500_and_hides_traceback(
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = _app_with_handlers()

    @app.get("/crash")
    async def crash() -> None:
        raise RuntimeError("boom-secret-marker")

    with caplog.at_level(logging.ERROR, logger="fastbase.errors"):
        r = _client(app, raise_server_exceptions=False).get("/crash")

    assert r.status_code == 500
    body = r.json()
    assert body["error"]["code"] == DEFAULT_FALLBACK_CODE
    assert body["error"]["message"] == "Internal server error"
    assert body["error"]["details"] is None
    assert "boom-secret-marker" not in r.text
    assert "RuntimeError" not in r.text
    assert any("Unhandled exception" in rec.message for rec in caplog.records)


def test_domain_error_details_serializable_via_jsonable_encoder() -> None:
    """`details` may contain datetime, set, Enum, pydantic — must not 500."""
    import enum
    from datetime import datetime

    from pydantic import BaseModel

    class Status(enum.Enum):
        ACTIVE = "active"

    class Payload(BaseModel):
        id: int

    app = _app_with_handlers()

    @app.get("/rich")
    async def rich() -> None:
        raise NotFoundError(
            message="Rich details",
            details={
                "when": datetime(2026, 1, 1, 12, 0, 0),
                "tags": {"a", "b"},
                "status": Status.ACTIVE,
                "payload": Payload(id=7),
            },
        )

    r = _client(app).get("/rich")
    assert r.status_code == 404
    body = r.json()
    assert body["success"] is False
    assert body["error"]["code"] == 3001
    # datetime → ISO string
    assert body["error"]["details"]["when"].startswith("2026-01-01")
    # set → list (order not guaranteed)
    assert sorted(body["error"]["details"]["tags"]) == ["a", "b"]
    # Enum → value
    assert body["error"]["details"]["status"] == "active"
    # pydantic → dict
    assert body["error"]["details"]["payload"] == {"id": 7}