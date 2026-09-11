"""Auto-discovery of APIRouter instances in a Python package.

Contract for each module in the target package:

  - optional: `router: APIRouter` — the router to mount under api_prefix
  - optional: `prefix: str`       — module-local prefix, added to api_prefix

Modules whose name starts with `_` are skipped. Import errors are logged
as warnings and do not abort discovery.
"""

from __future__ import annotations

import importlib
import logging
import pkgutil
from collections.abc import Iterator

from fastapi import APIRouter

logger = logging.getLogger("fastbase.routes")


def discover_routers(package: str) -> Iterator[tuple[APIRouter, str]]:
    """Yield (router, prefix) for every module in `package` that exports `router`.

    `prefix` is the module-local prefix (empty string if absent).
    """
    try:
        pkg = importlib.import_module(package)
    except ImportError as e:
        logger.warning("Routes package '%s' not found: %s", package, e)
        return

    pkg_path = getattr(pkg, "__path__", None)
    if not pkg_path:
        logger.warning("'%s' is not a package (no __path__)", package)
        return

    for _, name, _ in pkgutil.iter_modules(pkg_path):
        if name.startswith("_"):
            continue

        full = f"{package}.{name}"
        try:
            module = importlib.import_module(full)
        except Exception as e:
            logger.warning("Failed to import '%s': %s", full, e)
            continue

        router = getattr(module, "router", None)
        if not isinstance(router, APIRouter):
            continue

        prefix = getattr(module, "prefix", "") or ""
        yield router, prefix