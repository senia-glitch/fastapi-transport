"""Tests for fastbase CLI upgrade command."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from fastbase import __version__


def mock_eof_input(_: str = "") -> str:
    raise EOFError
from fastbase.cli.__main__ import main as cli_main
from fastbase.cli._upgrade import (
    _fetch_remote_version_info,
    _find_pip,
    _is_python_compatible,
    _parse_version,
    _VersionInfo,
    main_upgrade,
)


# ---------------------------------------------------------------------------
# _parse_version
# ---------------------------------------------------------------------------


class TestParseVersion:
    def test_simple_version(self) -> None:
        assert _parse_version("0.2.0") == (0, 2, 0)

    def test_version_with_prefix(self) -> None:
        assert _parse_version("v1.2.3") == (1, 2, 3)

    def test_single_number(self) -> None:
        assert _parse_version("42") == (42,)

    def test_version_with_prerelease(self) -> None:
        # "rc1" has digits, so regex includes the trailing 1
        assert _parse_version("1.0.0rc1") == (1, 0, 0, 1)

    def test_comparison(self) -> None:
        assert _parse_version("0.2.0") < _parse_version("0.3.0")
        assert _parse_version("0.2.0") < _parse_version("1.0.0")
        assert _parse_version("0.2.0") == _parse_version("0.2.0")
        assert _parse_version("0.2.1") > _parse_version("0.2.0")


# ---------------------------------------------------------------------------
# _is_python_compatible
# ---------------------------------------------------------------------------


class TestIsPythonCompatible:
    def test_empty_spec(self) -> None:
        assert _is_python_compatible("") is True

    def test_ge_match(self) -> None:
        # Current Python should satisfy >=3.x where x <= current minor
        spec = f">={sys.version_info.major}.{sys.version_info.minor}"
        assert _is_python_compatible(spec) is True

    def test_no_ge_specifier(self) -> None:
        """Requires-python without >= always returns True."""
        assert _is_python_compatible("<3.14") is True
        assert _is_python_compatible("!=3.10") is True

    def test_ge_no_match(self) -> None:
        # A far-future version should not be satisfied
        assert _is_python_compatible(">=99.0") is False

    def test_ge_with_upper_bound_match(self) -> None:
        spec = f">={sys.version_info.major}.{sys.version_info.minor},<{sys.version_info.major + 10}"
        assert _is_python_compatible(spec) is True

    def test_ge_with_upper_bound_no_match(self) -> None:
        # <{current}.{current} means "must be less than current" — always fails
        current = f"{sys.version_info.major}.{sys.version_info.minor}"
        spec = f">={current},<{current}"
        assert _is_python_compatible(spec) is False


# ---------------------------------------------------------------------------
# _fetch_remote_version_info
# ---------------------------------------------------------------------------


class TestFetchRemoteVersionInfo:
    def test_success(self) -> None:
        fake_toml = '[project]\nversion = "1.2.3"\nrequires-python = ">=3.11"\n'
        mock_resp = MagicMock()
        mock_resp.read.return_value = fake_toml.encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("fastbase.cli._upgrade.urllib.request.urlopen", return_value=mock_resp):
            result = _fetch_remote_version_info()

        assert result is not None
        assert result.version == "1.2.3"
        assert result.requires_python == ">=3.11"

    def test_no_requires_python(self) -> None:
        fake_toml = '[project]\nversion = "2.0.0"\n'
        mock_resp = MagicMock()
        mock_resp.read.return_value = fake_toml.encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("fastbase.cli._upgrade.urllib.request.urlopen", return_value=mock_resp):
            result = _fetch_remote_version_info()

        assert result is not None
        assert result.version == "2.0.0"
        assert result.requires_python == ""

    def test_network_error(self) -> None:
        import urllib.error

        with patch(
            "fastbase.cli._upgrade.urllib.request.urlopen",
            side_effect=urllib.error.URLError("no network"),
        ):
            result = _fetch_remote_version_info()

        assert result is None

    def test_invalid_toml_no_version(self) -> None:
        fake_toml = '[project]\nname = "fastbase"\n'
        mock_resp = MagicMock()
        mock_resp.read.return_value = fake_toml.encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("fastbase.cli._upgrade.urllib.request.urlopen", return_value=mock_resp):
            result = _fetch_remote_version_info()

        assert result is None


# ---------------------------------------------------------------------------
# _find_pip
# ---------------------------------------------------------------------------


class TestFindPip:
    def test_finds_pip_in_path(self) -> None:
        with patch("shutil.which", return_value="/usr/bin/pip"):
            result = _find_pip()
        assert result == ["/usr/bin/pip"]

    def test_finds_python_m_pip(self) -> None:
        with patch("shutil.which", return_value=None), \
             patch("fastbase.cli._upgrade.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = _find_pip()
        assert result == [sys.executable, "-m", "pip"]

    def test_finds_python_in_path_fallback(self) -> None:
        """When pip not found and sys.executable fails, try python in PATH."""
        call_count = 0

        def fake_which(name):
            if name == "pip":
                return None
            if name == "python":
                return "/usr/bin/python"
            return None

        def fake_run(cmd, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call: sys.executable -m pip fails
                raise FileNotFoundError
            # Second call: /usr/bin/python -m pip succeeds
            return MagicMock(returncode=0)

        with patch("shutil.which", side_effect=fake_which), \
             patch("fastbase.cli._upgrade.subprocess.run", side_effect=fake_run):
            result = _find_pip()
        assert result == ["/usr/bin/python", "-m", "pip"]

    def test_raises_when_pip_not_found(self) -> None:
        with patch("shutil.which", return_value=None), \
             patch("fastbase.cli._upgrade.subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(RuntimeError, match="pip not found"):
                _find_pip()


# ---------------------------------------------------------------------------
# main_upgrade — behaviour
# ---------------------------------------------------------------------------


class TestMainUpgrade:
    def test_already_up_to_date(self, capsys: pytest.CaptureFixture) -> None:
        remote = _VersionInfo(version=__version__, requires_python="")
        with patch("fastbase.cli._upgrade._fetch_remote_version_info", return_value=remote):
            rc = main_upgrade()

        assert rc == 0
        out = capsys.readouterr().out
        assert "already up to date" in out

    def test_check_only_when_update_available(self, capsys: pytest.CaptureFixture) -> None:
        remote = _VersionInfo(version="99.0.0", requires_python="")
        with patch("fastbase.cli._upgrade._fetch_remote_version_info", return_value=remote):
            rc = main_upgrade(check_only=True)

        assert rc == 0
        out = capsys.readouterr().out
        assert "update available" in out
        assert "99.0.0" in out

    def test_check_only_when_up_to_date(self, capsys: pytest.CaptureFixture) -> None:
        remote = _VersionInfo(version=__version__, requires_python="")
        with patch("fastbase.cli._upgrade._fetch_remote_version_info", return_value=remote):
            rc = main_upgrade(check_only=True)

        assert rc == 0
        assert "already up to date" in capsys.readouterr().out

    def test_fetch_fails(self, capsys: pytest.CaptureFixture) -> None:
        with patch("fastbase.cli._upgrade._fetch_remote_version_info", return_value=None):
            rc = main_upgrade()

        assert rc == 1
        assert "could not determine" in capsys.readouterr().out

    def test_pip_not_found(self, capsys: pytest.CaptureFixture) -> None:
        remote = _VersionInfo(version="99.0.0", requires_python="")
        with patch("fastbase.cli._upgrade._fetch_remote_version_info", return_value=remote), \
             patch("fastbase.cli._upgrade._find_pip", side_effect=RuntimeError("pip not found")):
            rc = main_upgrade()

        assert rc == 1
        assert "pip not found" in capsys.readouterr().out

    def test_upgrade_runs_pip(self, capsys: pytest.CaptureFixture) -> None:
        remote = _VersionInfo(version="99.0.0", requires_python="")
        mock_proc = MagicMock(returncode=0)
        with patch("fastbase.cli._upgrade._fetch_remote_version_info", return_value=remote), \
             patch("fastbase.cli._upgrade._find_pip", return_value=["/usr/bin/pip"]), \
             patch("fastbase.cli._upgrade.subprocess.run", return_value=mock_proc) as mock_run:
            rc = main_upgrade()

        assert rc == 0
        out = capsys.readouterr().out
        assert "updating" in out
        assert "done" in out
        # Verify pip was called with correct args
        call_args = mock_run.call_args[0][0]
        assert "install" in call_args
        assert "--upgrade" in call_args
        assert "git+" in call_args[-1]

    def test_pip_fails(self, capsys: pytest.CaptureFixture) -> None:
        remote = _VersionInfo(version="99.0.0", requires_python="")
        mock_proc = MagicMock(returncode=1)
        with patch("fastbase.cli._upgrade._fetch_remote_version_info", return_value=remote), \
             patch("fastbase.cli._upgrade._find_pip", return_value=["/usr/bin/pip"]), \
             patch("fastbase.cli._upgrade.subprocess.run", return_value=mock_proc):
            rc = main_upgrade()

        assert rc == 1
        assert "update failed" in capsys.readouterr().out

    def test_python_incompatible_user_confirms(
        self, capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        remote = _VersionInfo(version="99.0.0", requires_python=">=99.0")
        mock_proc = MagicMock(returncode=0)

        monkeypatch.setattr("builtins.input", lambda _: "y")

        with patch("fastbase.cli._upgrade._fetch_remote_version_info", return_value=remote), \
             patch("fastbase.cli._upgrade._find_pip", return_value=["/usr/bin/pip"]), \
             patch("fastbase.cli._upgrade.subprocess.run", return_value=mock_proc):
            rc = main_upgrade()

        assert rc == 0
        out = capsys.readouterr().out
        assert "warning" in out

    def test_python_incompatible_user_declines(
        self, capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        remote = _VersionInfo(version="99.0.0", requires_python=">=99.0")

        monkeypatch.setattr("builtins.input", lambda _: "n")

        with patch("fastbase.cli._upgrade._fetch_remote_version_info", return_value=remote):
            rc = main_upgrade()

        assert rc == 0
        out = capsys.readouterr().out
        assert "aborted" in out

    def test_python_incompatible_eof_aborts(
        self, capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        remote = _VersionInfo(version="99.0.0", requires_python=">=99.0")

        monkeypatch.setattr("builtins.input", mock_eof_input)

        with patch("fastbase.cli._upgrade._fetch_remote_version_info", return_value=remote):
            rc = main_upgrade()

        assert rc == 1
        assert "aborted" in capsys.readouterr().out

    def test_pip_timeout(self, capsys: pytest.CaptureFixture) -> None:
        remote = _VersionInfo(version="99.0.0", requires_python="")
        with patch("fastbase.cli._upgrade._fetch_remote_version_info", return_value=remote), \
             patch("fastbase.cli._upgrade._find_pip", return_value=["/usr/bin/pip"]), \
             patch("fastbase.cli._upgrade.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="pip", timeout=120)):
            rc = main_upgrade()

        assert rc == 1
        assert "timed out" in capsys.readouterr().out

    def test_pip_command_not_found(self, capsys: pytest.CaptureFixture) -> None:
        remote = _VersionInfo(version="99.0.0", requires_python="")
        with patch("fastbase.cli._upgrade._fetch_remote_version_info", return_value=remote), \
             patch("fastbase.cli._upgrade._find_pip", return_value=["/nonexistent/pip"]), \
             patch("fastbase.cli._upgrade.subprocess.run", side_effect=FileNotFoundError):
            rc = main_upgrade()

        assert rc == 1
        assert "command not found" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# CLI dispatcher
# ---------------------------------------------------------------------------


class TestCliUpgradeDispatch:
    def test_cli_upgrade(self, capsys: pytest.CaptureFixture) -> None:
        remote = _VersionInfo(version=__version__, requires_python="")
        with patch("fastbase.cli._upgrade._fetch_remote_version_info", return_value=remote):
            rc = cli_main(["upgrade"])
        assert rc == 0

    def test_cli_upgrade_check(self, capsys: pytest.CaptureFixture) -> None:
        remote = _VersionInfo(version="99.0.0", requires_python="")
        with patch("fastbase.cli._upgrade._fetch_remote_version_info", return_value=remote):
            rc = cli_main(["upgrade", "--check"])
        assert rc == 0
        assert "update available" in capsys.readouterr().out
