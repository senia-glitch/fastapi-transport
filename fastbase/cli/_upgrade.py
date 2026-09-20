"""`fastbase upgrade` — update the package via pip from GitHub.

The command NEVER touches project files (app/, .env.fastbase, pyproject.toml).
It only updates the package in site-packages.

Commands:
    fb upgrade          — check + install if newer version exists
    fb upgrade --check  — only print whether an update is available
"""

from __future__ import annotations

import re
import subprocess
import sys
import urllib.request
import urllib.error
from typing import NamedTuple

from fastbase import __version__

GITHUB_REPO_RAW = (
    "https://raw.githubusercontent.com/senia-glitch/fastapi-transport/main/pyproject.toml"
)
GITHUB_REPO_URL = "https://github.com/senia-glitch/fastapi-transport"
INSTALL_TARGET = "fastbase"


class _VersionInfo(NamedTuple):
    version: str
    requires_python: str


def _fetch_remote_version_info() -> _VersionInfo | None:
    """Fetch version and requires-python from GitHub pyproject.toml.

    Returns None if the fetch fails (network error, parse error, etc.).
    """
    try:
        req = urllib.request.Request(
            GITHUB_REPO_RAW,
            headers={"User-Agent": f"fastbase/{__version__}"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            text = resp.read().decode("utf-8")
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        print(f"warning: failed to fetch from GitHub: {exc}")
        return None

    version_match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not version_match:
        print("warning: could not parse version from remote pyproject.toml")
        return None

    rp_match = re.search(r'^requires-python\s*=\s*"([^"]+)"', text, re.MULTILINE)
    requires_python = rp_match.group(1) if rp_match else ""

    return _VersionInfo(
        version=version_match.group(1),
        requires_python=requires_python,
    )


def _parse_python_version_upper_bound(spec: str) -> tuple[int, ...] | None:
    """Extract the upper bound from requires-python specifier.

    Examples:
        ">=3.11"          -> None  (no upper bound)
        ">=3.11,<4"       -> (4,)
        ">=3.11,<3.14"    -> (3, 14)
        ">=3.11,<3.14.0"  -> (3, 14, 0)
    """
    parts = [s.strip() for s in spec.split(",")]
    for part in parts:
        m = re.match(r"^<\s*(\d+(?:\.\d+)*)$", part)
        if m:
            return tuple(int(x) for x in m.group(1).split("."))
    return None


def _is_python_compatible(requires_python: str) -> bool:
    """Check if current Python version satisfies requires-python."""
    if not requires_python:
        return True

    m = re.search(r">=\s*(\d+(?:\.\d+)*)", requires_python)
    if not m:
        return True

    min_version = tuple(int(x) for x in m.group(1).split("."))
    current = sys.version_info[:len(min_version)]

    if current < min_version:
        return False

    upper = _parse_python_version_upper_bound(requires_python)
    if upper is not None:
        current_full = sys.version_info[:len(upper)]
        if current_full >= upper:
            return False

    return True


def _parse_version(v: str) -> tuple[int, ...]:
    """Parse a version string into a comparable tuple of ints."""
    parts = re.split(r"[^0-9]+", v.strip())
    return tuple(int(p) for p in parts if p)


def _find_pip() -> list[str]:
    """Find the pip command.

    Tries: pip, python -m pip, sys.executable -m pip.
    Returns the command as a list, or raises RuntimeError.
    """
    import shutil

    # 1. Try pip directly
    pip_path = shutil.which("pip")
    if pip_path:
        return [pip_path]

    # 2. Try python -m pip
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "--version"],
            capture_output=True,
            check=True,
            timeout=10,
        )
        return [sys.executable, "-m", "pip"]
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        pass

    # 3. Try just "python" in PATH
    python_path = shutil.which("python")
    if python_path and python_path != sys.executable:
        try:
            subprocess.run(
                [python_path, "-m", "pip", "--version"],
                capture_output=True,
                check=True,
                timeout=10,
            )
            return [python_path, "-m", "pip"]
        except (subprocess.CalledProcessError, FileNotFoundError, OSError):
            pass

    raise RuntimeError(
        "pip not found. Install pip: https://pip.pypa.io/en/stable/installation/"
    )


def _run_upgrade(pip_cmd: list[str]) -> bool:
    """Run pip install --upgrade. Returns True on success."""
    cmd = pip_cmd + ["install", "--upgrade", f"git+{GITHUB_REPO_URL}.git"]
    print(f"running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, timeout=120)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("error: pip install timed out after 120 seconds")
        return False
    except FileNotFoundError:
        print(f"error: command not found: {cmd[0]}")
        return False


def main_upgrade(*, check_only: bool = False) -> int:
    """Entry point for `fb upgrade`."""
    current = __version__
    print(f"current version: {current}")
    print(f"checking {GITHUB_REPO_URL} ...")

    remote = _fetch_remote_version_info()
    if remote is None:
        print("error: could not determine remote version")
        return 1

    print(f"remote version:  {remote.version}")

    if _parse_version(remote.version) <= _parse_version(current):
        print("already up to date.")
        return 0

    if check_only:
        print(f"update available: {current} -> {remote.version}")
        return 0

    # Python compatibility check
    if remote.requires_python and not _is_python_compatible(remote.requires_python):
        print(
            f"\nwarning: remote version requires Python {remote.requires_python}, "
            f"but you have {sys.version_info.major}.{sys.version_info.minor}."
        )
        try:
            answer = input("continue anyway? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\naborted.")
            return 1
        if answer not in ("y", "yes"):
            print("aborted.")
            return 0

    # Find pip
    try:
        pip_cmd = _find_pip()
    except RuntimeError as exc:
        print(f"error: {exc}")
        return 1

    # Run upgrade
    print(f"\nupdating {INSTALL_TARGET} {current} -> {remote.version} ...")
    if _run_upgrade(pip_cmd):
        print("done. restart your application to use the new version.")
        return 0
    else:
        print("error: update failed")
        return 1
