#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nimo.application.container import ApplicationContainer
from nimo.domain.models import GenerationRequest


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke benchmark generation, import and Phase 5 analysis")
    parser.add_argument("--users", type=int, default=10)
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / ".benchmark_data")
    args = parser.parse_args()
    if args.output.exists():
        shutil.rmtree(args.output)

    total_rows = 0
    total_transfers = 0
    for seed in range(args.users):
        user = f"benchmark_{seed}"
        container = ApplicationContainer.for_user(
            user,
            project_root=PROJECT_ROOT,
            data_root=args.output,
            create=True,
            source_type="generated",
        )
        result = container.generation.generate(
            GenerationRequest(user, seed, date(2025, 1, 1), date(2025, 12, 31))
        )
        total_rows += result.imported_rows
        total_transfers += int(container.analysis.transaction_frame()["transfer_group_id"].notna().sum() / 2)
    print(f"Users: {args.users}")
    print(f"Rows: {total_rows}")
    print(f"Transfer pairs: {total_transfers}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
