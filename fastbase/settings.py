"""Package settings loaded via pydantic-settings.

Env prefix: FAT_.
Env file: .env.fastbase.
Real env vars take precedence over the env file.
"""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseAppSettings(BaseSettings):
    """Base settings for the fastbase package and its consumers.

    Consumer applications subclass this and add their own fields.
    The package itself never reads consumer-specific fields.
    """

    model_config = SettingsConfigDict(
        env_prefix="FAT_",
        env_file=".env.fastbase",
        extra="ignore",
    )

    # --- API ---
    title: str = "API"
    version: str = "0.0.0"
    description: str = ""
    api_prefix: str = "/api/v1"

    # --- Routes ---
    routes_package: str = "app.api.v1.routes"

    # --- Integrations ---
    # ""                 — only fastbase
    # "core,event-infra" — full stack
    integrations: str = ""
    core_discover: str | None = None

    # --- Docs ---
    docs_url: str | None = "/docs"
    openapi_url: str | None = "/openapi.json"
    redoc_url: str | None = "/redoc"
    openapi_tags: list[dict[str, str]] = []

    # --- Request-ID ---
    request_id_enabled: bool = True
    request_id_header: str = "X-Request-ID"

    # --- Logging ---
    log_level: str = "info"
    log_format: Literal["plain", "json"] = "plain"
    access_log: bool = True

    # --- Error codes ---
    error_codes: dict[str, int] = {}
    error_code_fallback: int = 3500

    # --- Uvicorn ---
    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = False
    workers: int = 1
    backlog: int = 2048
    timeout_keep_alive: int = 5
    root_path: str = ""
    app_path: str = "app.main:app"
    env_file: str | None = None

    @property
    def integrations_list(self) -> list[str]:
        """Parse FAT_INTEGRATIONS into a sorted list of names."""
        raw = (self.integrations or "").strip()
        if not raw:
            return []
        return [x.strip() for x in raw.split(",") if x.strip()]