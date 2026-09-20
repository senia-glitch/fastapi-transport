"""Decorator for routes with automatic response_model from core-package scenarios.

Usage::

    from fastbase.routing import scenario_route

    router = APIRouter(tags=["users"])

    @scenario_route(router, "/users", method="post", scenario="register_user")
    async def create_user(dto: CreateUserDTO):
        ...

The decorator queries core-package's scenario registry for the Response class
and sets it as ``response_model`` on the route.  If core-package is not
installed or the scenario is not found, a warning is logged and the route
has no explicit ``response_model`` (FastAPI will return raw JSON).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

logger = logging.getLogger("fastbase.routing.scenario")


def _resolve_response_model(scenario_name: str) -> Any:
    """Try to get the Response model for *scenario_name* from core-package.

    Returns the model class, or ``None`` if core-package is not installed,
    does not expose a registry, or the scenario was not found.
    """
    try:
        from core.registry import get_scenario  # type: ignore[import-untyped]
    except ImportError:
        logger.debug(
            "core-package is not installed — cannot resolve response model "
            "for scenario '%s'.",
            scenario_name,
        )
        return None

    try:
        scenario = get_scenario(scenario_name)
    except (KeyError, AttributeError) as exc:
        logger.warning(
            "Scenario '%s' not found in core-package registry: %s",
            scenario_name,
            exc,
        )
        return None

    response_model = getattr(scenario, "response_model", None)
    if response_model is None:
        logger.warning(
            "Scenario '%s' exists but has no response_model attribute.",
            scenario_name,
        )
    return response_model


def scenario_route(
    router: APIRouter,
    path: str,
    *,
    scenario: str,
    method: str = "post",
    **route_kwargs: Any,
) -> Any:
    """Register a route with ``response_model`` resolved from core-package.

    Parameters
    ----------
    router:
        The ``APIRouter`` to add the route to.
    path:
        URL path (e.g. ``"/users"``).
    scenario:
        Name of the core-package scenario whose ``response_model`` should
        be used.
    method:
        HTTP method (``"get"``, ``"post"``, ``"put"``, ``"delete"``,
        ``"patch"``).  Default ``"post"``.
    **route_kwargs:
        Extra keyword arguments forwarded to the router method
        (``summary``, ``status_code``, ``dependencies``, …).

    Returns
    -------
    A decorator that registers the endpoint function.
    """
    response_model = _resolve_response_model(scenario)

    if response_model is None:
        logger.warning(
            "Route %s %s (scenario=%s) will have no response_model. "
            "OpenAPI schema may be incomplete.",
            method.upper(),
            path,
            scenario,
        )
    else:
        route_kwargs.setdefault("response_model", response_model)

    method_name = method.lower()
    add_route = getattr(router, method_name, None)
    if add_route is None:
        raise ValueError(f"Unsupported HTTP method: {method!r}")

    def decorator(func: Any) -> Any:
        add_route(path, **route_kwargs)(func)
        return func

    return decorator
