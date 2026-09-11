"""Optional integrations with external packages (core-package, event-infra).

The package never imports these dependencies at module top-level.
They are pulled in lazily, only when FAT_INTEGRATIONS enables them.
"""

from __future__ import annotations

from collections.abc import Callable

from fastbase.settings import BaseAppSettings


def make_integrations_lifespan(
    settings: BaseAppSettings,
    integrations: list[str],
) -> Callable | None:
    """Return an async lifespan callable if integrations are enabled.

    Returns None when `integrations` is empty.
    Raises ValueError for unsupported combinations.
    """
    if not integrations:
        return None

    if set(integrations) == {"core", "event-infra"}:
        from fastbase.integrations.core_package import core_event_lifespan

        return core_event_lifespan(settings)

    # _validate_integrations already rejects this, but guard anyway.
    raise ValueError(
        f"Unsupported integrations combination: {integrations}. "
        f"Use empty or 'core,event-infra'."
    )