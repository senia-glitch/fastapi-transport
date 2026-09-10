"""run_api — start uvicorn from the package settings."""

import uvicorn

from fastbase.settings import BaseAppSettings


def run_api(app_path: str | None = None) -> None:
    """Start uvicorn.

    app_path — import string "module:attr". If None, taken from
    FAT_APP_PATH (default "app.main:app"). Blocks the process.
    """
    settings = BaseAppSettings()
    path = app_path or settings.app_path

    kwargs: dict = dict(
        host=settings.host,
        port=settings.port,
        backlog=settings.backlog,
        timeout_keep_alive=settings.timeout_keep_alive,
        root_path=settings.root_path,
        log_level=settings.log_level,
        access_log=False,
        reload=settings.reload,
        workers=settings.workers if not settings.reload else 1,
    )
    if settings.env_file:
        kwargs["env_file"] = settings.env_file

    uvicorn.run(path, **kwargs)