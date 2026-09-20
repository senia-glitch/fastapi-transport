"""Optional integrations with external packages (core-package, event-infra).

The package never imports these dependencies at module top-level.
They are pulled in lazily, only when FAT_INTEGRATIONS enables them.

Supported combinations:
  - ``""``               — no integrations (default)
  - ``"core"``           — core-package exception handlers only (no lifespan)
  - ``"core,event-infra"`` — full stack: core-package + event-infra lifespan
"""

from __future__ import annotations

from collections.abc import Callable

from fastbase.settings import BaseAppSettings


def make_integrations_lifespan(
    settings: BaseAppSettings,
    integrations: list[str],
) -> Callable | None:
    """Return an async lifespan callable if integrations are enabled.

    Returns ``None`` when *integrations* is empty or contains only
    ``"core"`` (core handlers are installed separately in ``startup.py``).
    """
    if not integrations:
        return None

    if set(integrations) == {"core", "event-infra"}:
        from fastbase.integrations.core_package import core_event_lifespan

        return core_event_lifespan(settings)

    # "core" alone → no lifespan needed (handlers installed in startup.py).
    # "event-infra" alone → not supported (would need core).
    return None