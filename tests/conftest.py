"""Shared fixtures for fastbase tests."""

import logging

import pytest


@pytest.fixture(autouse=True)
def _reset_fastbase_logging():
    """Reset the fastbase logger state after every test.

    ``configure_logging()`` sets ``propagate = False`` and installs a
    permanent handler on the ``fastbase`` logger.  Once any test calls
    ``make_app()``, every subsequent test that relies on ``caplog`` to
    capture records from child loggers (``fastbase.errors``,
    ``fastbase.routes``, ``fastbase.access``, …) fails because the
    records no longer reach the root logger.

    This fixture removes all handlers and restores ``propagate = True``
    so that each test starts with a clean logging state.
    """
    yield
    logger = logging.getLogger("fastbase")
    for h in list(logger.handlers):
        logger.removeHandler(h)
    logger.propagate = True
