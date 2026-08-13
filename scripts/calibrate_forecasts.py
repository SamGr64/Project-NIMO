#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nimo.application.container import ApplicationContainer


def main() -> int:
    parser = argparse.ArgumentParser(description="Run NIMO rolling forecast calibration diagnostics")
    parser.add_argument("user", nargs="?", default="sample_user")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--holdout-months", type=int, default=6)
    parser.add_argument("--runs", type=int, default=1000)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    app = ApplicationContainer.for_user(args.user, project_root=args.project_root.resolve(), data_root=args.data_root)
    result = app.forecasting.backtest(holdout_months=args.holdout_months, runs=args.runs)
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
        print(args.output)
    else:
        print(text)
    return 0 if result.get("status") in {"complete", "insufficient_history"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
