"""Tests for fastbase.routes_discovery."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from fastbase.routes_discovery import discover_routers


@pytest.fixture
def cleanup_modules():
    yield
    for name in list(sys.modules):
        if name.startswith("scan_pkg"):
            del sys.modules[name]


def _make_pkg(base: Path, modules: dict[str, str], name: str = "scan_pkg") -> str:
    pkg = base / name
    pkg.mkdir(exist_ok=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    for mod_name, content in modules.items():
        (pkg / f"{mod_name}.py").write_text(content, encoding="utf-8")
    return name


@pytest.fixture
def on_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cleanup_modules):
    monkeypatch.chdir(tmp_path)
    sys.path.insert(0, str(tmp_path))
    try:
        yield tmp_path
    finally:
        try:
            sys.path.remove(str(tmp_path))
        except ValueError:
            pass


def test_missing_package_yields_nothing(on_path, caplog) -> None:
    with caplog.at_level("WARNING", logger="fastbase.routes"):
        result = list(discover_routers("not_a_real_package_xyz"))
    assert result == []
    assert any("not_a_real_package_xyz" in rec.message for rec in caplog.records)


def test_empty_package_yields_nothing(on_path) -> None:
    _make_pkg(on_path, {})
    assert list(discover_routers("scan_pkg")) == []


def test_discovers_router(on_path) -> None:
    _make_pkg(on_path, {
        "users": (
            "from fastapi import APIRouter\n"
            "router = APIRouter()\n"
        ),
    })
    result = list(discover_routers("scan_pkg"))
    assert len(result) == 1
    router, prefix = result[0]
    assert prefix == ""
    from fastapi import APIRouter
    assert isinstance(router, APIRouter)


def test_discovers_router_with_prefix(on_path) -> None:
    _make_pkg(on_path, {
        "admin": (
            "from fastapi import APIRouter\n"
            "prefix = '/admin'\n"
            "router = APIRouter()\n"
        ),
    })
    result = list(discover_routers("scan_pkg"))
    assert len(result) == 1
    _, prefix = result[0]
    assert prefix == "/admin"


def test_skips_modules_without_router(on_path) -> None:
    _make_pkg(on_path, {
        "no_router": "X = 1\n",
        "yes_router": (
            "from fastapi import APIRouter\n"
            "router = APIRouter()\n"
        ),
    })
    result = list(discover_routers("scan_pkg"))
    assert len(result) == 1


def test_skips_underscore_modules(on_path) -> None:
    _make_pkg(on_path, {
        "_private": (
            "from fastapi import APIRouter\n"
            "router = APIRouter()\n"
        ),
        "public": (
            "from fastapi import APIRouter\n"
            "router = APIRouter()\n"
        ),
    })
    result = list(discover_routers("scan_pkg"))
    assert len(result) == 1


def test_broken_module_warns_and_continues(on_path, caplog) -> None:
    _make_pkg(on_path, {
        "bad": "raise RuntimeError('kaboom')\n",
        "good": (
            "from fastapi import APIRouter\n"
            "router = APIRouter()\n"
        ),
    })
    with caplog.at_level("WARNING", logger="fastbase.routes"):
        result = list(discover_routers("scan_pkg"))
    assert len(result) == 1
    assert any("kaboom" in rec.message for rec in caplog.records)


def test_non_package_yields_nothing(on_path, caplog) -> None:
    """If the name resolves to a module (not a package), warn and stop."""
    (on_path / "not_a_pkg.py").write_text("X = 1\n", encoding="utf-8")
    with caplog.at_level("WARNING", logger="fastbase.routes"):
        result = list(discover_routers("not_a_pkg"))
    assert result == []
    assert any("not a package" in rec.message for rec in caplog.records)