from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from nimo import __version__
from nimo.cli.commands import COMMAND_MODULES


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nimo",
        description="Project NIMO: local-first financial data generation and analysis",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--project-root", type=Path, help="Path containing pyproject.toml and config/")
    parser.add_argument("--data-root", type=Path, help="Override the configured user-data directory")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for module in COMMAND_MODULES:
        module.register(subparsers)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except (FileNotFoundError, KeyError, ValueError, TypeError) as exc:
        print(f"NIMO error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
