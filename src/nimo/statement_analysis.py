"""Analyse generated seeded CSV bank statements."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from nimo.analysis.statements import analyse_statement_file
else:
    from .analysis.statements import analyse_statement_file


ANALYSIS_VERSION = "2.0.2"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyse a generated CSV bank statement")
    parser.add_argument("path", type=Path, help="CSV statement to analyse")
    parser.add_argument("-c", "--config", type=Path, default=None)
    parser.add_argument("-o", "--plot-dir", type=Path, default=None)
    parser.add_argument("--no-show", action="store_true", help="Do not open plot windows")
    parser.add_argument("--version", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.version:
        print(f"Generator analysis version\t{ANALYSIS_VERSION}")
        return 0

    repo_root = Path(__file__).resolve().parents[2]
    config_path = args.config or repo_root / "config" / "generator_policy.yaml"
    if not config_path.is_absolute():
        config_path = (Path.cwd() / config_path).resolve()

    try:
        analyse_statement_file(
            args.path,
            config_path,
            plot_dir=args.plot_dir,
            show_plots=False if args.no_show else None,
        )
    except (OSError, TypeError, ValueError, KeyError) as exc:
        print(f"Analysis error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())