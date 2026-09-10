"""Tests for fastbase.runner.run_api (uvicorn is mocked)."""

from unittest.mock import patch

import pytest

from fastbase.runner import run_api
from fastbase.settings import BaseAppSettings


def test_run_api_uses_argument_app_path() -> None:
    with patch("fastbase.runner.uvicorn.run") as m:
        run_api("my.module:app")
    assert m.call_count == 1
    assert m.call_args.args[0] == "my.module:app"


def test_run_api_falls_back_to_settings_app_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FAT_APP_PATH", "x.y:z")
    with patch("fastbase.runner.uvicorn.run") as m:
        run_api()
    assert m.call_args.args[0] == "x.y:z"


def test_run_api_forces_single_worker_on_reload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FAT_RELOAD", "true")
    monkeypatch.setenv("FAT_WORKERS", "4")
    with patch("fastbase.runner.uvicorn.run") as m:
        run_api()
    kwargs = m.call_args.kwargs
    assert kwargs["reload"] is True
    assert kwargs["workers"] == 1


def test_run_api_passes_all_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FAT_HOST", "0.0.0.0")
    monkeypatch.setenv("FAT_PORT", "9000")
    monkeypatch.setenv("FAT_BACKLOG", "1024")
    monkeypatch.setenv("FAT_TIMEOUT_KEEP_ALIVE", "10")
    monkeypatch.setenv("FAT_ROOT_PATH", "/base")
    monkeypatch.setenv("FAT_LOG_LEVEL", "debug")
    monkeypatch.setenv("FAT_WORKERS", "2")

    with patch("fastbase.runner.uvicorn.run") as m:
        run_api("a:b")

    kwargs = m.call_args.kwargs
    assert kwargs["host"] == "0.0.0.0"
    assert kwargs["port"] == 9000
    assert kwargs["backlog"] == 1024
    assert kwargs["timeout_keep_alive"] == 10
    assert kwargs["root_path"] == "/base"
    assert kwargs["log_level"] == "debug"
    assert kwargs["workers"] == 2
    assert kwargs["access_log"] is False
    assert kwargs["reload"] is False
    assert "env_file" not in kwargs


def test_run_api_passes_env_file_when_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FAT_ENV_FILE", ".env.custom")
    with patch("fastbase.runner.uvicorn.run") as m:
        run_api("a:b")
    assert m.call_args.kwargs["env_file"] == ".env.custom"