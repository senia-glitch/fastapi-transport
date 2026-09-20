"""CLI entry point for the fastapi-transport package.

Commands:
    fastapi-transport init [--path app] [--force]
    fastapi-transport check
    fastapi-transport upgrade [--check]
    fastapi-transport version
    fastapi-transport help

Aliases: `fastbase`, `fb`.
"""

import argparse
import sys

from fastbase.cli._check import main_check
from fastbase.cli._init import main_init
from fastbase.cli._upgrade import main_upgrade
from fastbase.cli._version import main_version

PROG = "fastapi-transport"
GITHUB_URL = "https://github.com/senia-glitch/fastapi-transport"
DESCRIPTION = "Thin infrastructure over FastAPI for a uniform transport (API) layer."
EPILOG = f"GitHub: {GITHUB_URL}"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG,
        description=DESCRIPTION,
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="Generate the canonical project skeleton.")
    p_init.add_argument(
        "--path",
        default="app",
        help="Target package directory (default: app).",
    )
    p_init.add_argument(
        "--force",
        action="store_true",
        help="Overwrite files that carry the '# fastbase: generated' marker.",
    )

    sub.add_parser("check", help="Check the project for common problems.")

    p_upgrade = sub.add_parser(
        "upgrade", help="Update fastbase to the latest version from GitHub."
    )
    p_upgrade.add_argument(
        "--check",
        action="store_true",
        help="Only check if an update is available; do not install.",
    )

    sub.add_parser("version", help="Print package version.")
    sub.add_parser("help", help="Show this help message and exit.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.cmd == "init":
        return main_init(path=args.path, force=args.force)
    if args.cmd == "check":
        return main_check()
    if args.cmd == "upgrade":
        return main_upgrade(check_only=args.check)
    if args.cmd == "version":
        return main_version()
    if args.cmd == "help":
        parser.print_help()
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())