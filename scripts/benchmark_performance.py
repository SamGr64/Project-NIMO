#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import time
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nimo.application.container import ApplicationContainer
from nimo.domain.models import GenerationRequest


def timed(label, function):
    start = time.perf_counter()
    result = function()
    return result, {"operation": label, "seconds": round(time.perf_counter() - start, 6)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a local NIMO performance smoke benchmark")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--forecast-runs", type=int, default=2000)
    parser.add_argument("--investment-runs", type=int, default=2000)
    parser.add_argument("--keep", type=Path, help="Keep benchmark data in this directory")
    args = parser.parse_args()
    temp = Path(tempfile.mkdtemp(prefix="nimo_benchmark_")) if args.keep is None else args.keep.resolve()
    temp.mkdir(parents=True, exist_ok=True)
    rows = []
    try:
        app = ApplicationContainer.for_user("benchmark_user", project_root=PROJECT_ROOT, data_root=temp, create=True, source_type="generated")
        generation, timing = timed(
            "generation_and_import",
            lambda: app.generation.generate(GenerationRequest("benchmark_user", args.seed, date(2024, 1, 1), date(2026, 7, 31))),
        )
        rows.append({**timing, "rows": generation.imported_rows})
        _, timing = timed("behaviour_inference", lambda: app.behaviours.refresh(force=True))
        rows.append(timing)
        forecast, timing = timed("forecast", lambda: app.forecasting.run(horizon_months=24, runs=args.forecast_runs, seed=1))
        rows.append({**timing, "runs": forecast["simulation_runs"]})
        investment, timing = timed("investment", lambda: app.investing.simulate(horizon_years=10, runs=args.investment_runs, seed=2))
        rows.append({**timing, "runs": investment["simulation_runs"]})
        result = {"data_root": str(temp), "results": rows, "doctor": app.backups.doctor()}
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["doctor"]["healthy"] else 2
    finally:
        if args.keep is None:
            shutil.rmtree(temp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
