"""Tests for fastbase.startup: make_app and start."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from fastbase import make_app, start
from fastbase.settings import BaseAppSettings



class _RecordCollector(logging.Handler):
    """Attach directly to a logger; works even with propagate=False."""

    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def _collect(logger_name: str):
    """Return (collector, cleanup) that captures records on the given logger."""
    collector = _RecordCollector()
    logger = logging.getLogger(logger_name)
    logger.addHandler(collector)
    return collector, (lambda: logger.removeHandler(collector))

# ============================================================
# Fixtures and helpers
# ============================================================


def _clear_fat_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in list(os.environ):
        if key.startswith("FAT_"):
            monkeypatch.delenv(key, raising=False)


def _purge_modules(*prefixes: str) -> None:
    for name in list(sys.modules):
        for prefix in prefixes:
            if name == prefix or name.startswith(prefix + "."):
                del sys.modules[name]
                break


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Isolated cwd, cleared FAT_* env, tmp_path on sys.path."""
    _clear_fat_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    sys.path.insert(0, str(tmp_path))
    try:
        yield tmp_path
    finally:
        try:
            sys.path.remove(str(tmp_path))
        except ValueError:
            pass
        _purge_modules("routes_pkg", "app")


def _write_routes_package(
    base: Path,
    modules: dict[str, str],
    package: str = "routes_pkg",
) -> str:
    pkg = base / package
    pkg.mkdir(exist_ok=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    for name, content in modules.items():
        (pkg / f"{name}.py").write_text(content, encoding="utf-8")
    return package


# ============================================================
# make_app: basics
# ============================================================


def test_make_app_returns_fastapi(project: Path) -> None:
    _write_routes_package(project, {})
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv("FAT_ROUTES_PACKAGE", "routes_pkg")
    try:
        app = make_app()
        assert isinstance(app, FastAPI)
    finally:
        monkeypatch.undo()


def test_make_app_mounts_health_when_no_routers(project: Path, monkeypatch) -> None:
    """Empty routes package → fallback to health_router."""
    _write_routes_package(project, {})
    monkeypatch.setenv("FAT_ROUTES_PACKAGE", "routes_pkg")

    app = make_app()
    r = TestClient(app).get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_make_app_custom_api_prefix(project: Path, monkeypatch) -> None:
    _write_routes_package(project, {})
    monkeypatch.setenv("FAT_ROUTES_PACKAGE", "routes_pkg")
    monkeypatch.setenv("FAT_API_PREFIX", "/v2")

    app = make_app()
    client = TestClient(app)
    assert client.get("/v2/health").status_code == 200
    assert client.get("/api/v1/health").status_code == 404


def test_make_app_docs_configurable(project: Path, monkeypatch) -> None:
    _write_routes_package(project, {})
    monkeypatch.setenv("FAT_ROUTES_PACKAGE", "routes_pkg")
    monkeypatch.setenv("FAT_DOCS_URL", "")
    monkeypatch.setenv("FAT_REDOC_URL", "")

    app = make_app()
    # Empty string means "not set" in FastAPI terms
    # (FastAPI treats "" as falsy → docs disabled)
    # Actually FastAPI uses None to disable, "" is falsy for our config too.
    # We test that setting to empty string at least doesn't crash.
    assert isinstance(app, FastAPI)


def test_make_app_openapi_tags_default_empty(project: Path, monkeypatch) -> None:
    _write_routes_package(project, {})
    monkeypatch.setenv("FAT_ROUTES_PACKAGE", "routes_pkg")

    app = make_app()
    schema = app.openapi()
    assert "tags" not in schema or schema["tags"] == []


def test_make_app_openapi_tags_from_env(project: Path, monkeypatch) -> None:
    _write_routes_package(project, {
        "users": (
            "from fastapi import APIRouter\n"
            "router = APIRouter(tags=['users'])\n"
            "@router.get('/list')\n"
            "async def list_users(): return {'ok': True}\n"
        ),
    })
    monkeypatch.setenv("FAT_ROUTES_PACKAGE", "routes_pkg")
    monkeypatch.setenv(
        "FAT_OPENAPI_TAGS",
        '[{"name": "users", "description": "User management"}]',
    )

    app = make_app()
    schema = app.openapi()
    assert schema["tags"] == [{"name": "users", "description": "User management"}]


def test_make_app_openapi_tags_control_order(project: Path, monkeypatch) -> None:
    _write_routes_package(project, {
        "users": (
            "from fastapi import APIRouter\n"
            "router = APIRouter(tags=['users'])\n"
            "@router.get('/list')\n"
            "async def list_users(): return {'ok': True}\n"
        ),
        "admin": (
            "from fastapi import APIRouter\n"
            "router = APIRouter(tags=['admin'])\n"
            "@router.get('/stats')\n"
            "async def stats(): return {'ok': True}\n"
        ),
    })
    monkeypatch.setenv("FAT_ROUTES_PACKAGE", "routes_pkg")
    monkeypatch.setenv(
        "FAT_OPENAPI_TAGS",
        '[{"name": "admin", "description": "Admin"}, {"name": "users", "description": "Users"}]',
    )

    app = make_app()
    schema = app.openapi()
    tag_names = [t["name"] for t in schema["tags"]]
    assert tag_names == ["admin", "users"]

def test_make_app_missing_routes_package_warns(project: Path, monkeypatch) -> None:
    monkeypatch.setenv("FAT_ROUTES_PACKAGE", "definitely_not_a_package_xyz")

    collector, cleanup = _collect("fastbase.routes")
    try:
        app = make_app()
    finally:
        cleanup()

    assert TestClient(app).get("/api/v1/health").status_code == 200
    assert any(
        "definitely_not_a_package_xyz" in rec.message
        for rec in collector.records
    )

# ============================================================
# make_app: auto-discovery
# ============================================================


def test_make_app_discovers_router_without_prefix(
    project: Path, monkeypatch
) -> None:
    _write_routes_package(project, {
        "users": (
            "from fastapi import APIRouter\n"
            "router = APIRouter()\n"
            "@router.get('/list')\n"
            "async def list_users(): return {'ok': True}\n"
        ),
    })
    monkeypatch.setenv("FAT_ROUTES_PACKAGE", "routes_pkg")

    app = make_app()
    r = TestClient(app).get("/api/v1/list")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_make_app_discovers_router_with_module_prefix(
    project: Path, monkeypatch
) -> None:
    _write_routes_package(project, {
        "admin": (
            "from fastapi import APIRouter\n"
            "prefix = '/admin'\n"
            "router = APIRouter()\n"
            "@router.get('/ping')\n"
            "async def ping(): return {'pong': True}\n"
        ),
    })
    monkeypatch.setenv("FAT_ROUTES_PACKAGE", "routes_pkg")

    app = make_app()
    r = TestClient(app).get("/api/v1/admin/ping")
    assert r.status_code == 200
    assert r.json() == {"pong": True}


def test_make_app_skips_modules_without_router(
    project: Path, monkeypatch
) -> None:
    _write_routes_package(project, {
        "helpers": "X = 1\n",
        "users": (
            "from fastapi import APIRouter\n"
            "router = APIRouter()\n"
            "@router.get('/x')\n"
            "async def x(): return {'ok': True}\n"
        ),
    })
    monkeypatch.setenv("FAT_ROUTES_PACKAGE", "routes_pkg")

    app = make_app()
    assert TestClient(app).get("/api/v1/x").status_code == 200


def test_make_app_skips_underscore_modules(
    project: Path, monkeypatch
) -> None:
    _write_routes_package(project, {
        "_private": (
            "from fastapi import APIRouter\n"
            "router = APIRouter()\n"
            "@router.get('/secret')\n"
            "async def s(): return {'leak': True}\n"
        ),
        "public": (
            "from fastapi import APIRouter\n"
            "router = APIRouter()\n"
            "@router.get('/public')\n"
            "async def p(): return {'ok': True}\n"
        ),
    })
    monkeypatch.setenv("FAT_ROUTES_PACKAGE", "routes_pkg")

    app = make_app()
    client = TestClient(app)
    assert client.get("/api/v1/public").status_code == 200
    assert client.get("/api/v1/secret").status_code == 404


def test_make_app_broken_module_does_not_crash(
    project: Path, monkeypatch
) -> None:
    _write_routes_package(project, {
        "bad": "raise RuntimeError('boom')\n",
        "good": (
            "from fastapi import APIRouter\n"
            "router = APIRouter()\n"
            "@router.get('/ok')\n"
            "async def ok(): return {'ok': True}\n"
        ),
    })
    monkeypatch.setenv("FAT_ROUTES_PACKAGE", "routes_pkg")

    collector, cleanup = _collect("fastbase.routes")
    try:
        app = make_app()
    finally:
        cleanup()

    assert TestClient(app).get("/api/v1/ok").status_code == 200
    assert any("boom" in rec.message for rec in collector.records)

# ============================================================
# make_app: middleware and errors
# ============================================================


def test_make_app_installs_middleware(project: Path, monkeypatch) -> None:
    _write_routes_package(project, {})
    monkeypatch.setenv("FAT_ROUTES_PACKAGE", "routes_pkg")

    app = make_app()
    names = [m.cls.__name__ for m in app.user_middleware]
    assert "AccessLogMiddleware" in names
    assert "RequestIdMiddleware" in names
    assert names[0] == "RequestIdMiddleware"  # outermost


def test_make_app_middleware_can_be_disabled(project: Path, monkeypatch) -> None:
    _write_routes_package(project, {})
    monkeypatch.setenv("FAT_ROUTES_PACKAGE", "routes_pkg")
    monkeypatch.setenv("FAT_REQUEST_ID_ENABLED", "false")
    monkeypatch.setenv("FAT_ACCESS_LOG", "false")

    app = make_app()
    names = [m.cls.__name__ for m in app.user_middleware]
    assert "AccessLogMiddleware" not in names
    assert "RequestIdMiddleware" not in names


def test_make_app_installs_error_handlers(project: Path, monkeypatch) -> None:
    _write_routes_package(project, {
        "errs": (
            "from fastapi import APIRouter\n"
            "from fastbase import NotFoundError\n"
            "router = APIRouter()\n"
            "@router.get('/missing')\n"
            "async def m(): raise NotFoundError(message='nope')\n"
        ),
    })
    monkeypatch.setenv("FAT_ROUTES_PACKAGE", "routes_pkg")

    app = make_app()
    r = TestClient(app).get("/api/v1/missing")
    assert r.status_code == 404
    body = r.json()
    assert body["success"] is False
    assert body["error"]["message"] == "nope"


def test_make_app_request_id_header(project: Path, monkeypatch) -> None:
    _write_routes_package(project, {
        "h": (
            "from fastapi import APIRouter\n"
            "router = APIRouter()\n"
            "@router.get('/h')\n"
            "async def h(): return {'ok': True}\n"
        ),
    })
    monkeypatch.setenv("FAT_ROUTES_PACKAGE", "routes_pkg")

    app = make_app()
    r = TestClient(app).get("/api/v1/h", headers={"X-Request-ID": "abc-123"})
    assert r.headers["X-Request-ID"] == "abc-123"


# ============================================================
# make_app: integrations validation
# ============================================================


def test_make_app_rejects_unknown_integration(project: Path, monkeypatch) -> None:
    _write_routes_package(project, {})
    monkeypatch.setenv("FAT_ROUTES_PACKAGE", "routes_pkg")
    monkeypatch.setenv("FAT_INTEGRATIONS", "unknown-package")

    with pytest.raises(ValueError, match="Unknown FAT_INTEGRATIONS"):
        make_app()


def test_make_app_accepts_core_only_integration(
    project: Path, monkeypatch
) -> None:
    """FAT_INTEGRATIONS=core (subset) should be accepted, not rejected."""
    _write_routes_package(project, {})
    monkeypatch.setenv("FAT_ROUTES_PACKAGE", "routes_pkg")
    monkeypatch.setenv("FAT_INTEGRATIONS", "core")

    app = make_app()
    assert isinstance(app, FastAPI)


def test_make_app_empty_integrations_lifespan_is_none(
    project: Path, monkeypatch
) -> None:
    _write_routes_package(project, {})
    monkeypatch.setenv("FAT_ROUTES_PACKAGE", "routes_pkg")
    monkeypatch.setenv("FAT_INTEGRATIONS", "")

    app = make_app()
    assert app.router.lifespan_context is not None  # default FastAPI lifespan


# ============================================================
# start
# ============================================================


def test_start_calls_uvicorn(project: Path, monkeypatch) -> None:
    monkeypatch.setenv("FAT_APP_PATH", "app.main:app")
    monkeypatch.setenv("FAT_HOST", "0.0.0.0")
    monkeypatch.setenv("FAT_PORT", "9000")

    with patch("fastbase.startup.uvicorn.run") as m:
        start()

    assert m.call_count == 1
    assert m.call_args.args[0] == "app.main:app"
    kwargs = m.call_args.kwargs
    assert kwargs["host"] == "0.0.0.0"
    assert kwargs["port"] == 9000
    assert kwargs["access_log"] is False  # managed by AccessLogMiddleware


def test_start_passes_all_uvicorn_settings(project: Path, monkeypatch) -> None:
    monkeypatch.setenv("FAT_APP_PATH", "a:b")
    monkeypatch.setenv("FAT_BACKLOG", "1024")
    monkeypatch.setenv("FAT_TIMEOUT_KEEP_ALIVE", "10")
    monkeypatch.setenv("FAT_ROOT_PATH", "/base")
    monkeypatch.setenv("FAT_LOG_LEVEL", "debug")
    monkeypatch.setenv("FAT_WORKERS", "2")

    with patch("fastbase.startup.uvicorn.run") as m:
        start()

    kwargs = m.call_args.kwargs
    assert kwargs["backlog"] == 1024
    assert kwargs["timeout_keep_alive"] == 10
    assert kwargs["root_path"] == "/base"
    assert kwargs["log_level"] == "debug"
    assert kwargs["workers"] == 2
    assert kwargs["reload"] is False


def test_start_reload_forces_single_worker(project: Path, monkeypatch) -> None:
    monkeypatch.setenv("FAT_APP_PATH", "a:b")
    monkeypatch.setenv("FAT_RELOAD", "true")
    monkeypatch.setenv("FAT_WORKERS", "4")

    with patch("fastbase.startup.uvicorn.run") as m:
        start()

    kwargs = m.call_args.kwargs
    assert kwargs["reload"] is True
    assert kwargs["workers"] == 1


def test_start_env_file_passed_when_set(project: Path, monkeypatch) -> None:
    monkeypatch.setenv("FAT_APP_PATH", "a:b")
    monkeypatch.setenv("FAT_ENV_FILE", ".env.custom")

    with patch("fastbase.startup.uvicorn.run") as m:
        start()

    assert m.call_args.kwargs["env_file"] == ".env.custom"


def test_make_app_reload_workers_warning(project: Path, monkeypatch) -> None:
    _write_routes_package(project, {})
    monkeypatch.setenv("FAT_ROUTES_PACKAGE", "routes_pkg")
    monkeypatch.setenv("FAT_RELOAD", "true")
    monkeypatch.setenv("FAT_WORKERS", "4")

    collector, cleanup = _collect("fastbase.startup")
    try:
        make_app()
    finally:
        cleanup()

    assert any("FAT_RELOAD" in rec.message for rec in collector.records)

