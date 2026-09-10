"""CLI entry point: `fastbase` and alias `fb`.

Commands:
    fastbase init [--path app] [--force]
    fastbase check
    fastbase version
"""

import argparse
import sys

from fastbase.cli._check import main_check
from fastbase.cli._init import main_init
from fastbase.cli._version import main_version


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="fastbase",
        description="fastbase — thin infrastructure over FastAPI.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="Generate project skeleton.")
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
    sub.add_parser("version", help="Print package version.")

    args = parser.parse_args(argv)

    if args.cmd == "init":
        return main_init(path=args.path, force=args.force)
    if args.cmd == "check":
        return main_check()
    if args.cmd == "version":
        return main_version()
    return 2


if __name__ == "__main__":
    sys.exit(main())