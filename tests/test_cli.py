"""Tests for fastbase CLI (init / check / version)."""

import sys
from pathlib import Path

import pytest

from fastbase import __version__
from fastbase.cli.__main__ import main as cli_main
from fastbase.cli._check import main_check
from fastbase.cli._init import main_init
from fastbase.cli._version import main_version

EXPECTED_FILES = [
    "app/main.py",
    "app/core/config.py",
    "app/core/exceptions.py",
    "app/core/env.py",
    "app/api/v1/routes/health.py",
    "app/api/v1/dependencies.py",
    "app/api/handlers.py",
    "app/schemas/example.py",
    ".env.fastbase",
    "pyproject.toml",
]


def _clear_app_modules() -> None:
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]


# ---------------------------------------------------------------------------
# version
# ---------------------------------------------------------------------------


def test_version_prints_version(
    capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    rc = main_version()
    assert rc == 0
    assert capsys.readouterr().out.strip() == __version__


# ---------------------------------------------------------------------------
# argparse dispatcher (fastbase.cli.__main__:main)
# ---------------------------------------------------------------------------


def test_cli_dispatches_version(
    capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    rc = cli_main(["version"])
    assert rc == 0
    assert capsys.readouterr().out.strip() == __version__


def test_cli_dispatches_init(
    capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    rc = cli_main(["init"])
    assert rc == 0
    assert (tmp_path / "app" / "main.py").exists()
    assert "Next steps:" in capsys.readouterr().out


def test_cli_dispatches_init_with_path_and_force(
    capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    rc = cli_main(["init", "--path", "svc", "--force"])
    assert rc == 0
    assert (tmp_path / "svc" / "main.py").exists()
    assert (tmp_path / ".env.fastbase").exists()


def test_cli_dispatches_check(
    capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    _clear_app_modules()
    rc = cli_main(["check"])
    # empty dir → fail → rc=1
    assert rc == 1
    assert "fail:" in capsys.readouterr().out


def test_cli_requires_subcommand(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit):
        cli_main([])

def test_cli_dispatches_help(capsys: pytest.CaptureFixture) -> None:
    rc = cli_main(["help"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "init" in out
    assert "check" in out
    assert "version" in out
    assert "help" in out
    assert "https://github.com/senia-glitch/fastapi-transport" in out


def test_cli_help_flag_shows_github(capsys: pytest.CaptureFixture) -> None:
    with pytest.raises(SystemExit) as ei:
        cli_main(["--help"])
    assert ei.value.code == 0
    out = capsys.readouterr().out
    assert "https://github.com/senia-glitch/fastapi-transport" in out
    assert "init" in out
# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------

def test_init_creates_docs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """`fb init` создаёт четыре файла документации в docs/."""
    monkeypatch.chdir(tmp_path)
    rc = main_init()
    assert rc == 0

    docs = tmp_path / "docs"
    assert docs.is_dir()
    for name in ["event-infra.md", "core-package.md", "fastbase.md", "full-stack.md"]:
        assert (docs / name).exists(), name

def test_init_creates_all_files(
    capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    rc = main_init()
    assert rc == 0
    out = capsys.readouterr().out

    for rel in EXPECTED_FILES:
        assert (tmp_path / rel).exists(), rel
        assert "created:" in out
    assert "Next steps:" in out

    # every generated file carries the marker on line 1
    for rel in EXPECTED_FILES:
        first = (tmp_path / rel).read_text(encoding="utf-8").splitlines()[0]
        assert first.startswith("# fastbase: generated"), rel


def test_init_idempotent_without_force(
    capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    main_init()
    capsys.readouterr()
    rc = main_init()
    assert rc == 0
    out = capsys.readouterr().out
    assert out.count("skip:") >= 8
    assert "overwrite:" not in out


def test_init_force_overwrites_generated(
    capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    main_init()
    p = tmp_path / "app" / "main.py"
    p.write_text("# fastbase: generated\n# changed\n", encoding="utf-8")
    capsys.readouterr()
    rc = main_init(force=True)
    assert rc == 0
    out = capsys.readouterr().out
    assert "overwrite:" in out
    assert "make_app" in p.read_text(encoding="utf-8")


def test_init_does_not_touch_user_code(
    capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "app").mkdir()
    p = tmp_path / "app" / "main.py"
    p.write_text("# user code\n", encoding="utf-8")
    rc = main_init(force=True)
    assert rc == 0
    out = capsys.readouterr().out
    assert "skip (user code):" in out
    assert p.read_text(encoding="utf-8") == "# user code\n"


def test_init_path_is_file_error(
    capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "afile"
    f.write_text("x", encoding="utf-8")
    rc = main_init(path=str(f))
    assert rc == 1
    assert "error:" in capsys.readouterr().out


def test_init_does_not_touch_existing_pyproject(
    capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    existing = '[project]\nname = "custom"\n'
    (tmp_path / "pyproject.toml").write_text(existing, encoding="utf-8")
    rc = main_init()
    assert rc == 0
    assert (tmp_path / "pyproject.toml").read_text(encoding="utf-8") == existing


# ---------------------------------------------------------------------------
# check
# ---------------------------------------------------------------------------


def test_check_empty_dir_fail(
    capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    _clear_app_modules()
    rc = main_check()
    assert rc == 1
    out = capsys.readouterr().out
    assert "fail:" in out


def test_check_after_init_ok(
    capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    main_init()
    capsys.readouterr()
    _clear_app_modules()
    rc = main_check()
    out = capsys.readouterr().out
    assert rc == 0, out
    assert "fail:" not in out


def test_check_warns_duplicate_prefix(
    capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    main_init()
    (tmp_path / "app" / "main.py").write_text(
        "# fastbase: generated\n"
        "from fastapi import APIRouter\n"
        "router1 = APIRouter(prefix='/x')\n"
        "router2 = APIRouter(prefix='/x')\n",
        encoding="utf-8",
    )
    capsys.readouterr()
    _clear_app_modules()
    main_check()
    out = capsys.readouterr().out
    assert "duplicate prefix" in out


def test_check_warns_reload_workers(
    capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    main_init()
    (tmp_path / ".env.fastbase").write_text(
        "FAT_RELOAD=true\nFAT_WORKERS=2\n", encoding="utf-8"
    )
    capsys.readouterr()
    _clear_app_modules()
    main_check()
    out = capsys.readouterr().out
    assert "FAT_RELOAD" in out and "FAT_WORKERS" in out


def test_check_fails_when_app_main_import_raises(
    capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    main_init()
    (tmp_path / "app" / "main.py").write_text(
        "# fastbase: generated\nraise RuntimeError('boom')\n",
        encoding="utf-8",
    )
    capsys.readouterr()
    _clear_app_modules()
    rc = main_check()
    out = capsys.readouterr().out
    assert rc == 1
    assert "app.main:app import" in out


def test_check_fails_when_app_attribute_missing(
    capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    main_init()
    (tmp_path / "app" / "main.py").write_text(
        "# fastbase: generated\nx = 1\n",
        encoding="utf-8",
    )
    capsys.readouterr()
    _clear_app_modules()
    rc = main_check()
    out = capsys.readouterr().out
    assert rc == 1
    assert "no 'app' attribute" in out


def test_check_fails_when_routes_package_missing(
    capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    main_init()
    (tmp_path / ".env.fastbase").write_text(
        "FAT_ROUTES_PACKAGE=does.not.exist\n", encoding="utf-8"
    )
    capsys.readouterr()
    _clear_app_modules()
    rc = main_check()
    out = capsys.readouterr().out
    assert rc == 1
    assert "FAT_ROUTES_PACKAGE" in out


def test_init_recognizes_marker_with_bom(
    capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A file starting with a UTF-8 BOM must still be recognized as generated."""
    monkeypatch.chdir(tmp_path)
    main_init()
    p = tmp_path / "app" / "main.py"
    p.write_text(
        "\ufeff# fastbase: generated\n# placeholder\n",
        encoding="utf-8",
    )
    capsys.readouterr()
    rc = main_init(force=True)
    assert rc == 0
    out = capsys.readouterr().out
    assert "overwrite:" in out
    assert "make_app" in p.read_text(encoding="utf-8-sig")