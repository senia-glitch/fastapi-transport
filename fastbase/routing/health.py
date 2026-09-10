"""Health-check router.

Exposed as `health_router`. Mounted under the configured api_prefix by
create_app; consumers can include it manually if needed.
"""

from fastapi import APIRouter

health_router = APIRouter(tags=["health"])


@health_router.get("/health", summary="Health check")
async def health() -> dict[str, str]:
    return {"status": "ok"}