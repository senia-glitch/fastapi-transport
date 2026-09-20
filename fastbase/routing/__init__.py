"""fastbase.routing — package-provided routers."""

from fastbase.routing.health import health_router
from fastbase.routing.scenario_route import scenario_route

__all__ = ["health_router", "scenario_route"]