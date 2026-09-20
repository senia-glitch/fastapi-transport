"""Tests for fastbase.integrations (core-package and event-infra)."""

from __future__ import annotations

import asyncio
import sys
import types

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fastbase.integrations import make_integrations_lifespan
from fastbase.settings import BaseAppSettings


# ============================================================
# make_integrations_lifespan
# ============================================================


def test_make_lifespan_empty_returns_none() -> None:
    assert make_integrations_lifespan(BaseAppSettings(), []) is None


def test_make_lifespan_full_returns_callable(monkeypatch) -> None:
    from fastbase.integrations import core_package as cp

    # Provide a stub module for imports inside core_event_lifespan
    fake_run_infra = types.ModuleType("run_infrastructure")
    fake_core = types.ModuleType("core")
    monkeypatch.setitem(sys.modules, "run_infrastructure", fake_run_infra)
    monkeypatch.setitem(sys.modules, "core", fake_core)

    lifespan = make_integrations_lifespan(
        BaseAppSettings(), ["core", "event-infra"]
    )
    assert callable(lifespan)


def test_make_lifespan_core_only_returns_none() -> None:
    """FAT_INTEGRATIONS=core → no lifespan (handlers installed separately)."""
    result = make_integrations_lifespan(BaseAppSettings(), ["core"])
    assert result is None


# ============================================================
# install_core_handlers
# ============================================================


def test_install_core_handlers_noop_when_core_missing(monkeypatch) -> None:
    """If 'core' module cannot be imported, install_core_handlers is a no-op."""
    # Make `import core` fail
    monkeypatch.setitem(sys.modules, "core", None)

    from fastbase.integrations.core_package import install_core_handlers

    app = FastAPI()
    initial_keys = set(app.exception_handlers.keys())
    install_core_handlers(app, BaseAppSettings())
    assert set(app.exception_handlers.keys()) == initial_keys


def test_install_core_handlers_registers_handler(monkeypatch) -> None:
    """With a fake core.exceptions.CoreError, a handler must be registered
    and must produce the unified error envelope."""

    class FakeCoreError(Exception):
        http_status = 404
        def __init__(self, message="not found", *, code=None):
            super().__init__(message)
            self.message = message
            self.code = code

    fake_exceptions = types.ModuleType("core.exceptions")
    fake_exceptions.CoreError = FakeCoreError
    fake_core = types.ModuleType("core")
    fake_core.exceptions = fake_exceptions

    monkeypatch.setitem(sys.modules, "core", fake_core)
    monkeypatch.setitem(sys.modules, "core.exceptions", fake_exceptions)

    from fastbase.integrations.core_package import install_core_handlers

    app = FastAPI()
    install_core_handlers(app, BaseAppSettings())
    assert FakeCoreError in app.exception_handlers

    @app.get("/boom")
    async def boom() -> None:
        raise FakeCoreError("custom msg", code=2001)

    r = TestClient(app).get("/boom")
    assert r.status_code == 404
    body = r.json()
    assert body["success"] is False
    assert body["error"]["code"] == 2001
    assert body["error"]["message"] == "custom msg"


def test_install_core_handlers_fallback_code(monkeypatch) -> None:
    class FakeCoreError(Exception):
        http_status = 500
        def __init__(self, message="x"):
            super().__init__(message)
            self.message = message
            self.code = None

    fake_exceptions = types.ModuleType("core.exceptions")
    fake_exceptions.CoreError = FakeCoreError
    fake_core = types.ModuleType("core")
    fake_core.exceptions = fake_exceptions
    monkeypatch.setitem(sys.modules, "core", fake_core)
    monkeypatch.setitem(sys.modules, "core.exceptions", fake_exceptions)

    from fastbase.integrations.core_package import install_core_handlers

    app = FastAPI()
    settings = BaseAppSettings(error_code_fallback=4242)
    install_core_handlers(app, settings)

    @app.get("/boom")
    async def boom() -> None:
        raise FakeCoreError("boom")

    r = TestClient(app).get("/boom")
    assert r.status_code == 500
    assert r.json()["error"]["code"] == 4242


def test_install_core_handlers_uses_error_codes_mapping(monkeypatch) -> None:
    class CustomCoreError(Exception):
        http_status = 404
        def __init__(self, message="x"):
            super().__init__(message)
            self.message = message
            self.code = None

    fake_exceptions = types.ModuleType("core.exceptions")
    fake_exceptions.CoreError = CustomCoreError
    fake_core = types.ModuleType("core")
    fake_core.exceptions = fake_exceptions
    monkeypatch.setitem(sys.modules, "core", fake_core)
    monkeypatch.setitem(sys.modules, "core.exceptions", fake_exceptions)

    from fastbase.integrations.core_package import install_core_handlers

    app = FastAPI()
    settings = BaseAppSettings(error_codes={"CustomCoreError": 7777})
    install_core_handlers(app, settings)

    @app.get("/boom")
    async def boom() -> None:
        raise CustomCoreError("custom")

    r = TestClient(app).get("/boom")
    assert r.json()["error"]["code"] == 7777


# ============================================================
# core_event_lifespan
# ============================================================


def _install_fakes(monkeypatch, *, start_infrastructure, start_core, reset_core):
    """Install fake run_infrastructure and core modules into sys.modules."""
    fake_run_infra = types.ModuleType("run_infrastructure")
    fake_run_infra.start_infrastructure = start_infrastructure

    fake_core = types.ModuleType("core")
    fake_core.start_core = start_core
    fake_core.reset_core = reset_core

    monkeypatch.setitem(sys.modules, "run_infrastructure", fake_run_infra)
    monkeypatch.setitem(sys.modules, "core", fake_core)


def test_core_event_lifespan_starts_and_stops_in_order(monkeypatch) -> None:
    calls: list[str] = []

    class FakeRouter:
        async def shutdown(self):
            calls.append("router.shutdown")

    fake_router = FakeRouter()

    async def fake_start_infra():
        calls.append("start_infrastructure")
        return fake_router

    async def fake_start_core(router=None, discover=None):
        calls.append(f"start_core(router={router is fake_router}, discover={discover})")

    def fake_reset_core():
        calls.append("reset_core")

    _install_fakes(
        monkeypatch,
        start_infrastructure=fake_start_infra,
        start_core=fake_start_core,
        reset_core=fake_reset_core,
    )

    from fastbase.integrations.core_package import core_event_lifespan

    settings = BaseAppSettings(core_discover="app.scenarios")
    lifespan = core_event_lifespan(settings)

    async def _run():
        async with lifespan(None):
            calls.append("inside")

    asyncio.run(_run())

    assert calls == [
        "start_infrastructure",
        "start_core(router=True, discover=app.scenarios)",
        "inside",
        "reset_core",
        "router.shutdown",
    ]


def test_core_event_lifespan_warns_when_discover_empty(
    monkeypatch, caplog
) -> None:
    class FakeRouter:
        async def shutdown(self):
            pass

    async def fake_start_infra():
        return FakeRouter()

    async def fake_start_core(router=None, discover=None):
        assert discover is None

    def fake_reset_core():
        pass

    _install_fakes(
        monkeypatch,
        start_infrastructure=fake_start_infra,
        start_core=fake_start_core,
        reset_core=fake_reset_core,
    )

    from fastbase.integrations.core_package import core_event_lifespan

    settings = BaseAppSettings(core_discover=None)
    lifespan = core_event_lifespan(settings)

    async def _run():
        async with lifespan(None):
            pass

    import logging
    with caplog.at_level(logging.WARNING, logger="fastbase.integrations.core"):
        asyncio.run(_run())

    assert any("FAT_CORE_DISCOVER" in rec.message for rec in caplog.records)


def test_core_event_lifespan_raises_without_event_infra(monkeypatch) -> None:
    """When run_infrastructure is missing, entering the lifespan raises."""
    monkeypatch.setitem(sys.modules, "run_infrastructure", None)

    from fastbase.integrations.core_package import core_event_lifespan
    lifespan = core_event_lifespan(BaseAppSettings())

    async def _run():
        async with lifespan(None):
            pass

    with pytest.raises(ImportError, match="event-infra"):
        asyncio.run(_run())


def test_core_event_lifespan_raises_without_core(monkeypatch) -> None:
    """run_infrastructure есть, core отсутствует → ошибка про core-package."""
    fake_run_infra = types.ModuleType("run_infrastructure")
    fake_run_infra.start_infrastructure = object
    monkeypatch.setitem(sys.modules, "run_infrastructure", fake_run_infra)
    monkeypatch.setitem(sys.modules, "core", None)

    from fastbase.integrations.core_package import core_event_lifespan
    lifespan = core_event_lifespan(BaseAppSettings())

    async def _run():
        async with lifespan(None):
            pass

    with pytest.raises(ImportError, match="core-package"):
        asyncio.run(_run())