"""Tests for fastbase middleware and logging."""

import asyncio
import json
import logging
import uuid
from typing import Any

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from fastbase.logging_setup import (
    JsonFormatter,
    PlainFormatter,
    RequestIdFilter,
    configure_logging,
    get_request_id,
    reset_request_id,
    set_request_id,
)
from fastbase.middleware import AccessLogMiddleware, RequestIdMiddleware
from fastbase.settings import BaseAppSettings


# ---------------------------------------------------------------------------
# RequestIdMiddleware
# ---------------------------------------------------------------------------


def test_request_id_from_incoming_header() -> None:
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/")
    async def root(request: Request) -> dict:
        return {"rid": request.state.request_id}

    r = TestClient(app).get("/", headers={"X-Request-ID": "abc"})
    assert r.status_code == 200
    assert r.json()["rid"] == "abc"
    assert r.headers["X-Request-ID"] == "abc"


def test_request_id_generated_when_absent() -> None:
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/")
    async def root(request: Request) -> dict:
        return {"rid": request.state.request_id}

    r = TestClient(app).get("/")
    rid = r.json()["rid"]
    assert isinstance(rid, str)
    assert len(rid) == 32
    uuid.UUID(rid)  # valid hex
    assert r.headers["X-Request-ID"] == rid


def test_request_id_custom_header() -> None:
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware, header="X-Trace")

    @app.get("/")
    async def root(request: Request) -> dict:
        return {"rid": request.state.request_id}

    r = TestClient(app).get("/", headers={"X-Trace": "trace-1"})
    assert r.json()["rid"] == "trace-1"
    assert r.headers["X-Trace"] == "trace-1"
    assert "X-Request-ID" not in r.headers


def test_contextvar_propagates_to_endpoint() -> None:
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/")
    async def root() -> dict:
        return {"ctx": get_request_id()}

    r = TestClient(app).get("/", headers={"X-Request-ID": "ctx-1"})
    assert r.json()["ctx"] == "ctx-1"


def test_request_id_middleware_passes_through_non_http_scope() -> None:
    received: list[dict] = []

    async def downstream(scope, receive, send) -> None:
        await send({"type": "lifespan.startup.complete"})

    async def receive() -> dict:
        return {"type": "lifespan.startup"}

    async def send(message: dict) -> None:
        received.append(message)

    mw = RequestIdMiddleware(downstream)
    asyncio.run(mw({"type": "lifespan"}, receive, send))

    assert received == [{"type": "lifespan.startup.complete"}]


def test_request_id_truncates_long_header() -> None:
    """Request IDs longer than 128 chars are truncated."""
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/")
    async def root(request: Request) -> dict:
        return {"rid": request.state.request_id}

    long_id = "x" * 200
    r = TestClient(app).get("/", headers={"X-Request-ID": long_id})
    assert r.status_code == 200
    rid = r.json()["rid"]
    assert len(rid) == 128


def test_request_id_handles_malformed_header() -> None:
    """Latin-1 decode of header bytes — all byte values 0-255 are valid."""
    from fastbase.middleware.request_id import RequestIdMiddleware as RID

    async def noop(scope, receive, send):
        pass

    mw = RID(noop)
    # All byte values 0-255 are valid Latin-1, so decode always succeeds.
    # The try/except is a safety net for edge cases.
    scope = {
        "type": "http",
        "headers": [
            (b"x-request-id", b"\x00\x01\xff valid-id"),
        ],
    }
    state = {}
    scope["state"] = state

    async def receive():
        return {"type": "http.request", "body": b""}

    sent = []

    async def send(msg):
        sent.append(msg)

    asyncio.run(mw(scope, receive, send))
    rid = state.get("request_id", "")
    assert rid == "\x00\x01\xff valid-id"


# ---------------------------------------------------------------------------
# AccessLogMiddleware
# ---------------------------------------------------------------------------


def test_access_log_emits_line(caplog: pytest.LogCaptureFixture) -> None:
    app = FastAPI()
    app.add_middleware(AccessLogMiddleware)

    @app.get("/ping")
    async def ping() -> dict:
        return {"ok": True}

    with caplog.at_level(logging.INFO, logger="fastbase.access"):
        r = TestClient(app).get("/ping")

    assert r.status_code == 200
    lines = [
        rec.getMessage()
        for rec in caplog.records
        if rec.name == "fastbase.access"
    ]
    assert lines, "expected at least one access log line"
    msg = lines[-1]
    assert msg.startswith("GET /ping 200 ")
    assert "ms" in msg
    assert "request_id=" in msg


def test_access_log_includes_request_id_when_inner_to_request_id(
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = FastAPI()
    # Same order as create_app: AccessLog first, RequestId second (outer).
    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(RequestIdMiddleware)

    @app.get("/ok")
    async def ok() -> dict:
        return {"ok": True}

    with caplog.at_level(logging.INFO, logger="fastbase.access"):
        r = TestClient(app).get("/ok", headers={"X-Request-ID": "trace-x"})

    assert r.status_code == 200
    lines = [
        rec.getMessage()
        for rec in caplog.records
        if rec.name == "fastbase.access"
    ]
    assert any("request_id=trace-x" in m for m in lines)


def test_middleware_order_request_id_is_outermost() -> None:
    app = FastAPI()
    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(RequestIdMiddleware)

    # user_middleware[0] is applied last == outermost.
    names = [m.cls.__name__ for m in app.user_middleware]
    assert names[0] == "RequestIdMiddleware"
    assert names[-1] == "AccessLogMiddleware"


def test_access_log_middleware_passes_through_non_http_scope(
    caplog: pytest.LogCaptureFixture,
) -> None:
    received: list[dict] = []

    async def downstream(scope, receive, send) -> None:
        await send({"type": "lifespan.startup.complete"})

    async def receive() -> dict:
        return {}

    async def send(message: dict) -> None:
        received.append(message)

    mw = AccessLogMiddleware(downstream)
    with caplog.at_level(logging.INFO, logger="fastbase.access"):
        asyncio.run(mw({"type": "lifespan"}, receive, send))

    assert received == [{"type": "lifespan.startup.complete"}]
    assert not any(r.name == "fastbase.access" for r in caplog.records)


# ---------------------------------------------------------------------------
# Formatters & filter
# ---------------------------------------------------------------------------


def _record(msg: str = "hello", **extra: Any) -> logging.LogRecord:
    rec = logging.LogRecord(
        name="fastbase.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=msg,
        args=(),
        exc_info=None,
    )
    for k, v in extra.items():
        setattr(rec, k, v)
    return rec


def test_plain_formatter_format() -> None:
    fmt = PlainFormatter()
    rec = _record("GET /health 200 3ms", request_id="abc123")
    out = fmt.format(rec)
    assert " INFO  " in out
    assert "[req=abc123]" in out
    assert "fastbase.test: GET /health 200 3ms" in out


def test_json_formatter_format() -> None:
    fmt = JsonFormatter()
    rec = _record("GET /health 200 3ms", request_id="abc123")
    out = fmt.format(rec)
    data = json.loads(out)
    assert data["level"] == "INFO"
    assert data["logger"] == "fastbase.test"
    assert data["msg"] == "GET /health 200 3ms"
    assert data["request_id"] == "abc123"
    assert data["ts"].endswith("Z")


def test_request_id_filter_sets_default() -> None:
    f = RequestIdFilter()
    rec = _record("x")
    f.filter(rec)
    assert rec.request_id == "-"


def test_request_id_filter_keeps_explicit() -> None:
    f = RequestIdFilter()
    rec = _record("x", request_id="xyz")
    f.filter(rec)
    assert rec.request_id == "xyz"


def test_request_id_filter_reads_contextvar() -> None:
    f = RequestIdFilter()
    token = set_request_id("from-ctx")
    try:
        rec = _record("x")
        f.filter(rec)
        assert rec.request_id == "from-ctx"
    finally:
        reset_request_id(token)


# ---------------------------------------------------------------------------
# configure_logging
# ---------------------------------------------------------------------------


def test_configure_logging_is_idempotent() -> None:
    settings = BaseAppSettings()
    configure_logging(settings)
    n1 = len(logging.getLogger("fastbase").handlers)
    configure_logging(settings)
    n2 = len(logging.getLogger("fastbase").handlers)
    assert n1 == n2 == 1


def test_configure_logging_sets_level_and_format() -> None:
    settings = BaseAppSettings(log_format="json", log_level="debug")
    configure_logging(settings)
    logger = logging.getLogger("fastbase")
    assert logger.level == logging.DEBUG
    assert logger.propagate is False
    assert len(logger.handlers) == 1
    handler = logger.handlers[0]
    assert isinstance(handler.formatter, JsonFormatter)
    assert any(isinstance(f, RequestIdFilter) for f in handler.filters)


def test_configure_logging_plain_format() -> None:
    settings = BaseAppSettings(log_format="plain", log_level="warning")
    configure_logging(settings)
    logger = logging.getLogger("fastbase")
    assert logger.level == logging.WARNING
    assert isinstance(logger.handlers[0].formatter, PlainFormatter)


def test_configure_logging_invalid_level_warns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = BaseAppSettings(log_level="INVALID_LEVEL")
    with pytest.warns(UserWarning, match="Invalid FAT_LOG_LEVEL"):
        configure_logging(settings)
    logger = logging.getLogger("fastbase")
    assert logger.level == logging.INFO  # fallback