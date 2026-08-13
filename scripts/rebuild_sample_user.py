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
    parser = argparse.ArgumentParser(description="Rebuild the reproducible NIMO sample_user")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--start", type=date.fromisoformat, default=date(2024, 1, 1))
    parser.add_argument("--end", type=date.fromisoformat, default=date(2026, 7, 31))
    parser.add_argument("--archetype")
    parser.add_argument("--skip-derived", action="store_true", help="Generate/import statements only")
    parser.add_argument("--include-pdf", action="store_true", help="Also render a sample PDF report (requires reports extra)")
    parser.add_argument("--forecast-runs", type=int, default=1000)
    parser.add_argument("--investment-runs", type=int, default=1000)
    args = parser.parse_args()

    root = args.project_root.resolve()
    data_root = (args.data_root or root / "data").resolve()
    sample_root = data_root / "sample_user"
    if sample_root.exists():
        shutil.rmtree(sample_root)

    container = ApplicationContainer.for_user(
        "sample_user",
        project_root=root,
        data_root=data_root,
        create=True,
        display_name="Sample User",
        source_type="generated",
    )
    result = container.generation.generate(
        GenerationRequest(
            user_name="sample_user",
            seed=args.seed,
            start_date=args.start,
            end_date=args.end,
            archetype=args.archetype,
        )
    )

    derived_lines: list[str] = []
    if not args.skip_derived:
        behaviour = container.behaviours.refresh(force=True)
        forecast = container.forecasting.run(
            horizon_months=12,
            runs=args.forecast_runs,
            seed=7291,
        )
        budget = container.planning.ensure_default_budget(force=True)
        goal = container.planning.add_goal(
            name="Emergency buffer",
            target_amount=18000.0,
            current_amount=6000.0,
            target_date=date(2028, 12, 31),
            priority=1,
            monthly_contribution=150.0,
            surplus_allocation_fraction=0.20,
        )
        goal_result = container.planning.simulate_goal(goal["id"], runs=args.forecast_runs, seed=91001)
        container.investing.ensure_default_portfolio()
        investment = container.investing.simulate(
            horizon_years=10,
            runs=args.investment_runs,
            seed=44021,
        )
        report_formats = ["html", "md"] + (["pdf"] if args.include_pdf else [])
        report = container.reporting.build(formats=report_formats, use_llm=False)
        derived_lines = [
            f"- Inferred archetype: `{behaviour.get('archetype', {}).get('label', 'unknown')}`",
            f"- Forecast horizon/runs: `12 months / {forecast['simulation_runs']}`",
            f"- Default budget lines: `{len(budget['lines'])}`",
            f"- Demo goal probability: `{float(goal_result['probability_achieved']):.1%}`",
            f"- Investment horizon/runs: `10 years / {investment['simulation_runs']}`",
            f"- Included sample reports: `{', '.join(report['outputs'])}`",
        ]

    readme = sample_root / "README.md"
    readme.write_text(
        "# NIMO sample user\n\n"
        "This workspace is fully synthetic and reproducible. It is safe to use for "
        "dashboard, CLI, forecasting, planning, reporting and investing-sandbox development.\n\n"
        f"- Seed: `{args.seed}`\n"
        f"- Date range: `{args.start.isoformat()}` to `{args.end.isoformat()}`\n"
        f"- Seed-selected archetype: `{result.archetype}`\n"
        f"- Imported transactions: `{result.imported_rows}`\n"
        f"- Accounts: `{result.account_count}`\n"
        + ("\n" + "\n".join(derived_lines) + "\n" if derived_lines else "")
        + "\nRebuild from PowerShell at the repository root with:\n\n"
        "```powershell\npython .\\scripts\\rebuild_sample_user.py\n```\n\n"
        "Add `--include-pdf` when the reports extra is installed. The analysis code receives "
        "only rendered statement files and the normalised database. Hidden generator truth "
        "remains under `synthetic/` for explicit validation tools and is never read by normal "
        "analysis services.\n",
        encoding="utf-8",
    )
    print(f"Rebuilt {result.user_name}: {result.imported_rows} rows, {result.account_count} accounts")
    print(f"Archetype: {result.archetype}")
    print(f"Manifest: {result.manifest_path}")
    if derived_lines:
        print("Derived sample features completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
