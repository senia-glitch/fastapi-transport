"""`fastbase version` — print the package version."""

from fastbase import __version__


def main_version() -> int:
    print(__version__)
    return 0