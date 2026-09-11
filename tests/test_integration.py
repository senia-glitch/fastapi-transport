"""End-to-end integration tests: init → import → TestClient."""

import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fastbase.cli._init import main_init


def _purge_app_modules() -> None:
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Create a fresh fastbase project in tmp_path and import its app."""
    monkeypatch.chdir(tmp_path)
    _purge_app_modules()
    rc = main_init()
    assert rc == 0
    sys.path.insert(0, str(tmp_path))
    try:
        yield tmp_path
    finally:
        try:
            sys.path.remove(str(tmp_path))
        except ValueError:
            pass
        _purge_app_modules()


def test_generated_project_serves_health(project: Path) -> None:
    from app.main import app as user_app

    with TestClient(user_app) as client:
        r = client.get("/api/v1/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


def test_generated_project_openapi_and_docs(project: Path) -> None:
    from app.main import app as user_app

    with TestClient(user_app) as client:
        assert client.get("/docs").status_code == 200
        assert client.get("/redoc").status_code == 200
        spec = client.get("/openapi.json").json()
        assert "/api/v1/health" in spec["paths"]


def test_generated_project_request_id_header(project: Path) -> None:
    from app.main import app as user_app

    with TestClient(user_app) as client:
        r = client.get("/api/v1/health", headers={"X-Request-ID": "it-1"})
        assert r.headers["X-Request-ID"] == "it-1"


def test_generated_project_unknown_route_uses_envelope(project: Path) -> None:
    from app.main import app as user_app

    with TestClient(user_app) as client:
        r = client.get("/api/v1/definitely-not-a-route")
        assert r.status_code == 404
        body = r.json()
        assert body["success"] is False
        assert body["error"]["code"] == 3001


def test_generated_project_settings_subclass(project: Path) -> None:
    from app.core.config import Settings, settings

    assert isinstance(settings, Settings)
    assert settings.api_prefix == "/api/v1"


def test_generated_main_uses_make_app(project: Path) -> None:
    """The generated main.py must use make_app / start, not create_app / run_api."""
    src = (project / "app" / "main.py").read_text(encoding="utf-8")
    assert "make_app" in src
    assert "start" in src
    assert "create_app" not in src
    assert "run_api" not in src


# ---------------------------------------------------------------------------
# Escape hatch: bare FastAPI still works
# ---------------------------------------------------------------------------


def test_escape_hatch_plain_fastapi_with_health_router() -> None:
    from fastbase import health_router

    raw = FastAPI()
    raw.include_router(health_router, prefix="/api/v1")
    with TestClient(raw) as client:
        r = client.get("/api/v1/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


def test_escape_hatch_plain_fastapi_only() -> None:
    raw = FastAPI()

    @raw.get("/ping")
    async def ping() -> dict:
        return {"pong": True}

    with TestClient(raw) as client:
        assert client.get("/ping").json() == {"pong": True}