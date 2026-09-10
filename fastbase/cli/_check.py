"""`fastbase check` — read-only project sanity checks.

Prints one line per check with a level: ok / warn / fail.
Exit code: 1 if any fail, 0 otherwise (ok or warn).
"""

import importlib
import re
import sys
from pathlib import Path

from fastbase.settings import BaseAppSettings

REQUIRED_FILES = [
    "app/main.py",
    "app/core/config.py",
    "app/api/v1/routes/health.py",
    ".env.fastbase",
]


def _clear_app_modules() -> None:
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]


def main_check() -> int:
    cwd = Path.cwd()
    results: list[tuple[str, str]] = []
    settings: BaseAppSettings | None = None

    # 1. required files
    missing = [p for p in REQUIRED_FILES if not (cwd / p).exists()]
    if missing:
        results.append(("fail", f"missing files: {', '.join(missing)}"))
    else:
        results.append(("ok", "required files present"))

    # 2. settings load
    try:
        settings = BaseAppSettings()
        results.append(("ok", "BaseAppSettings loaded"))
    except Exception as e:  # pragma: no cover - defensive
        results.append(("fail", f"BaseAppSettings: {e}"))

    # 3. app.main:app import
    if (cwd / "app" / "main.py").exists():
        sys.path.insert(0, str(cwd))
        _clear_app_modules()
        try:
            mod = importlib.import_module("app.main")
            if getattr(mod, "app", None) is None:
                results.append(("fail", "app.main has no 'app' attribute"))
            else:
                results.append(("ok", "app.main:app imports"))
        except Exception as e:
            results.append(("fail", f"app.main:app import: {e}"))
        finally:
            try:
                sys.path.remove(str(cwd))
            except ValueError:
                pass
            _clear_app_modules()

    # 4. routers declared but not referenced in main.py
    main_py = cwd / "app" / "main.py"
    routes_dir = cwd / "app" / "api" / "v1" / "routes"
    if main_py.exists() and routes_dir.exists():
        main_src = main_py.read_text(encoding="utf-8")
        for f in sorted(routes_dir.glob("*.py")):
            if f.name == "__init__.py":
                continue
            text = f.read_text(encoding="utf-8")
            if "router" not in text:
                continue
            if f.stem not in main_src:
                results.append(
                    ("warn", f"router '{f.stem}' not referenced in main.py")
                )

    # 5. duplicate prefixes in main.py
    if main_py.exists():
        main_src = main_py.read_text(encoding="utf-8")
        prefixes = re.findall(r"prefix\s*=\s*['\"]([^'\"]+)['\"]", main_src)
        seen: set[str] = set()
        for p in prefixes:
            if p in seen:
                results.append(("warn", f"duplicate prefix: {p}"))
            seen.add(p)

    # 6. reload + workers conflict
    if settings is not None and settings.reload and settings.workers > 1:
        results.append(
            (
                "warn",
                f"FAT_RELOAD=true with FAT_WORKERS={settings.workers} "
                "(uvicorn will use 1 worker)",
            )
        )

    has_fail = False
    for level, msg in results:
        print(f"{level}: {msg}")
        if level == "fail":
            has_fail = True
    return 1 if has_fail else 0