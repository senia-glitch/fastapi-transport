"""Tests for fastbase.app.create_app."""

import logging

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from fastbase import NotFoundError, create_app, health_router
from fastbase.settings import BaseAppSettings


def test_create_app_returns_fastapi() -> None:
    app = create_app(BaseAppSettings(), [])
    assert isinstance(app, FastAPI)


def test_health_router_is_mounted_under_prefix() -> None:
    app = create_app(BaseAppSettings(), [health_router])
    r = TestClient(app).get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_custom_api_prefix() -> None:
    settings = BaseAppSettings(api_prefix="/api/v2")
    app = create_app(settings, [health_router])
    r = TestClient(app).get("/api/v2/health")
    assert r.status_code == 200
    assert TestClient(app).get("/api/v1/health").status_code == 404


def test_domain_error_flows_through_create_app() -> None:
    router = APIRouter()

    @router.get("/boom")
    async def boom() -> None:
        raise NotFoundError(message="User not found")

    app = create_app(BaseAppSettings(), [router])
    r = TestClient(app).get("/api/v1/boom")
    assert r.status_code == 404
    body = r.json()
    assert body["success"] is False
    assert body["error"]["message"] == "User not found"


def test_docs_url_configurable() -> None:
    settings = BaseAppSettings(docs_url=None, redoc_url=None)
    app = create_app(settings, [])
    assert TestClient(app).get("/docs").status_code == 404
    assert TestClient(app).get("/redoc").status_code == 404


def test_lifespan_startup_and_shutdown_called() -> None:
    events: list[str] = []

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        events.append("start")
        yield
        events.append("stop")

    app = create_app(BaseAppSettings(), [], lifespan=lifespan)
    with TestClient(app) as client:
        assert client.get("/openapi.json").status_code == 200
        assert events == ["start"]
    assert events == ["start", "stop"]


def test_middleware_installed_by_default() -> None:
    app = create_app(BaseAppSettings(), [])
    names = [m.cls.__name__ for m in app.user_middleware]
    assert "AccessLogMiddleware" in names
    assert "RequestIdMiddleware" in names
    # RequestId must be the outermost (index 0).
    assert names[0] == "RequestIdMiddleware"


def test_middleware_can_be_disabled() -> None:
    settings = BaseAppSettings(
        access_log=False, request_id_enabled=False
    )
    app = create_app(settings, [])
    names = [m.cls.__name__ for m in app.user_middleware]
    assert "AccessLogMiddleware" not in names
    assert "RequestIdMiddleware" not in names


def test_request_id_header_present_on_response() -> None:
    app = create_app(BaseAppSettings(), [health_router])
    r = TestClient(app).get("/api/v1/health")
    assert "X-Request-ID" in r.headers


def test_custom_request_id_header() -> None:
    settings = BaseAppSettings(request_id_header="X-Trace-ID")
    app = create_app(settings, [health_router])
    r = TestClient(app).get("/api/v1/health")
    assert "X-Trace-ID" in r.headers
    assert "X-Request-ID" not in r.headers


def test_reload_with_workers_logs_warning() -> None:
    """The warning is emitted on the `fastbase.app` logger.

    `configure_logging` sets `propagate = False` on the `fastbase` logger,
    so pytest's `caplog` (which relies on propagation to the root logger)
    will not see these records. We attach a collector to the child logger
    `fastbase.app` directly; `configure_logging` only touches `fastbase`.
    """
    settings = BaseAppSettings(reload=True, workers=4)

    records: list[logging.LogRecord] = []

    class _Collector(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    collector = _Collector()
    child = logging.getLogger("fastbase.app")
    child.addHandler(collector)
    try:
        create_app(settings, [])
    finally:
        child.removeHandler(collector)

    assert any("FAT_RELOAD" in rec.message for rec in records)


def test_handlers_installed_before_routers() -> None:
    """A route that raises a domain error must be caught by package handler."""
    router = APIRouter()

    @router.get("/x")
    async def x() -> None:
        raise NotFoundError()

    app = create_app(BaseAppSettings(), [router])
    r = TestClient(app).get("/api/v1/x")
    assert r.status_code == 404
    assert r.json()["success"] is False


def test_openapi_includes_package_routes() -> None:
    app = create_app(BaseAppSettings(), [health_router])
    spec = TestClient(app).get("/openapi.json").json()
    paths = spec["paths"]
    assert "/api/v1/health" in paths
    assert "get" in paths["/api/v1/health"]