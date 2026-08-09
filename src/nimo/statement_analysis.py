"""Analyse generated seeded CSV bank statements."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Mapping
import matplotlib.pyplot as plt
import pandas as pd

from utils import (
    canonical_amount_series,
    find_field_name,
    flatten_nested_strings,
    load_csv,
    load_yaml_mapping,
    normalise_text_aggressive,
)

from analysis.statements import analyse_statement_file


ANALYSIS_VERSION = "2.0.0"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyse a generated CSV bank statement")
    parser.add_argument("path", type=Path, help="CSV statement to analyse")
    parser.add_argument("-c", "--config", type=Path, default=Path("generator_policy.yaml"))
    parser.add_argument("-o", "--plot-dir", type=Path, default=None)
    parser.add_argument("--no-show", action="store_true", help="Do not open plot windows")
    parser.add_argument("--version", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.version:
        print(f"Generator analysis version\t{ANALYSIS_VERSION}")
        return 0
    try:
        analyse_statement_file(
            args.path,
            args.config,
            plot_dir=args.plot_dir,
            show_plots=False if args.no_show else None,
        )
    except (OSError, TypeError, ValueError, KeyError) as exc:
        print(f"Analysis error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())