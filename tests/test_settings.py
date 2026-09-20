"""Tests for fastbase.settings.BaseAppSettings."""

import json
import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from fastbase.settings import BaseAppSettings


def _clear_fat_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in list(os.environ):
        if key.startswith("FAT_"):
            monkeypatch.delenv(key, raising=False)


def test_defaults(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _clear_fat_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    s = BaseAppSettings()
    assert s.title == "API"
    assert s.version == "0.0.0"
    assert s.description == ""
    assert s.api_prefix == "/api/v1"
    assert s.docs_url == "/docs"
    assert s.openapi_url == "/openapi.json"
    assert s.redoc_url == "/redoc"
    assert s.request_id_enabled is True
    assert s.request_id_header == "X-Request-ID"
    assert s.log_level == "info"
    assert s.log_format == "plain"
    assert s.access_log is True
    assert s.error_codes == {}
    assert s.error_code_fallback == 3500
    assert s.host == "127.0.0.1"
    assert s.port == 8000
    assert s.reload is False
    assert s.workers == 1
    assert s.backlog == 2048
    assert s.timeout_keep_alive == 5
    assert s.root_path == ""
    assert s.app_path == "app.main:app"
    assert s.env_file is None


def test_env_overrides_defaults(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _clear_fat_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FAT_TITLE", "My API")
    monkeypatch.setenv("FAT_PORT", "9999")
    monkeypatch.setenv("FAT_RELOAD", "true")
    s = BaseAppSettings()
    assert s.title == "My API"
    assert s.port == 9999
    assert s.reload is True


def test_env_file_is_read(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _clear_fat_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env.fastbase").write_text(
        "FAT_TITLE=FromFile\nFAT_PORT=7001\n", encoding="utf-8"
    )
    s = BaseAppSettings()
    assert s.title == "FromFile"
    assert s.port == 7001


def test_env_var_beats_env_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _clear_fat_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env.fastbase").write_text("FAT_TITLE=FromFile\n", encoding="utf-8")
    monkeypatch.setenv("FAT_TITLE", "FromEnv")
    s = BaseAppSettings()
    assert s.title == "FromEnv"


def test_invalid_type_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _clear_fat_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FAT_PORT", "not-a-number")
    with pytest.raises(ValidationError):
        BaseAppSettings()


def test_error_codes_parsed_from_json_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _clear_fat_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    payload = {"UserNotFoundError": 2001, "PaymentFailed": 2002}
    monkeypatch.setenv("FAT_ERROR_CODES", json.dumps(payload))
    s = BaseAppSettings()
    assert s.error_codes == payload


def test_subclass_with_extra_fields(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _clear_fat_env(monkeypatch)
    monkeypatch.chdir(tmp_path)

    class Settings(BaseAppSettings):
        database_url: str = ""
        jwt_secret: str = ""

    monkeypatch.setenv("FAT_DATABASE_URL", "postgres://x")
    s = Settings()
    assert s.database_url == "postgres://x"
    assert s.jwt_secret == ""


def test_log_format_literal_validation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _clear_fat_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FAT_LOG_FORMAT", "xml")
    with pytest.raises(ValidationError):
        BaseAppSettings()


# ---------------------------------------------------------------------------
# New fields: routes_package / integrations / core_discover
# ---------------------------------------------------------------------------


def test_routes_package_default(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _clear_fat_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    s = BaseAppSettings()
    assert s.routes_package == "app.api.v1.routes"


def test_routes_package_from_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _clear_fat_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FAT_ROUTES_PACKAGE", "svc.routes")
    s = BaseAppSettings()
    assert s.routes_package == "svc.routes"


def test_integrations_default_empty(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _clear_fat_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    s = BaseAppSettings()
    assert s.integrations == ""
    assert s.integrations_list == []


def test_integrations_from_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _clear_fat_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FAT_INTEGRATIONS", "core,event-infra")
    s = BaseAppSettings()
    assert s.integrations_list == ["core", "event-infra"]


def test_integrations_list_tolerates_spaces(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _clear_fat_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FAT_INTEGRATIONS", " core , event-infra ")
    s = BaseAppSettings()
    assert s.integrations_list == ["core", "event-infra"]


def test_integrations_list_empty_string(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _clear_fat_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FAT_INTEGRATIONS", "")
    s = BaseAppSettings()
    assert s.integrations_list == []


def test_core_discover_default_none(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _clear_fat_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    s = BaseAppSettings()
    assert s.core_discover is None


def test_core_discover_from_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _clear_fat_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FAT_CORE_DISCOVER", "myapp.scenarios")
    s = BaseAppSettings()
    assert s.core_discover == "myapp.scenarios"


# ---------------------------------------------------------------------------
# openapi_tags
# ---------------------------------------------------------------------------


def test_openapi_tags_default_empty(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _clear_fat_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    s = BaseAppSettings()
    assert s.openapi_tags == []


def test_openapi_tags_from_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _clear_fat_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    tags = [{"name": "users", "description": "User management"}]
    monkeypatch.setenv("FAT_OPENAPI_TAGS", json.dumps(tags))
    s = BaseAppSettings()
    assert s.openapi_tags == tags