"""Access-Log middleware (pure ASGI).

Emits one log line per HTTP request to the `fastbase.access` logger.

Format: METHOD PATH STATUS DURATION_MS request_id=<rid>
Example: GET /health 200 3ms request_id=0f8c...
"""

import logging
import time


class AccessLogMiddleware:
    """Emit one access-log line per request."""

    def __init__(self, app, *, logger_name: str = "fastbase.access") -> None:
        """Initialise the middleware.

        Parameters
        ----------
        app:
            The next ASGI application in the chain.
        logger_name:
            Name of the logger to emit access lines to.
        """
        self.app = app
        self.logger = logging.getLogger(logger_name)

    async def __call__(self, scope, receive, send) -> None:
        """ASGI callable — logs method, path, status, duration and request id."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()
        status_holder = {"status": 500}

        async def send_wrapper(message) -> None:
            if message["type"] == "http.response.start":
                status_holder["status"] = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = int((time.perf_counter() - start) * 1000)
            request_id = scope.get("state", {}).get("request_id", "-")
            method = scope.get("method", "-")
            path = scope.get("path", "-")
            status = status_holder["status"]
            self.logger.info(
                "%s %s %d %dms request_id=%s",
                method,
                path,
                status,
                duration_ms,
                request_id,
            )