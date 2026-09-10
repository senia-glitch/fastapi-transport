"""Request-ID middleware (pure ASGI).

Behaviour:
  - Reads the configured header from the incoming request if present.
  - Falls back to uuid4().hex.
  - Stores the value in scope["state"]["request_id"]
    (visible as request.state.request_id in endpoints).
  - Echoes the value in the response header.
  - Sets a private ContextVar so that logging can pick it up.
"""

import uuid

from fastbase.logging_setup import reset_request_id, set_request_id


class RequestIdMiddleware:
    """Attach a request id to every HTTP request."""

    def __init__(self, app, *, header: str = "X-Request-ID") -> None:
        self.app = app
        self.header = header
        self.header_lower = header.lower().encode("latin-1")

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming: str | None = None
        for name, value in scope.get("headers") or []:
            if name == self.header_lower:
                incoming = value.decode("latin-1")
                break

        request_id = incoming or uuid.uuid4().hex

        scope.setdefault("state", {})
        scope["state"]["request_id"] = request_id

        header_name = self.header.encode("latin-1")
        header_value = request_id.encode("latin-1")

        async def send_wrapper(message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers") or [])
                headers.append((header_name, header_value))
                message["headers"] = headers
            await send(message)

        token = set_request_id(request_id)
        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            reset_request_id(token)