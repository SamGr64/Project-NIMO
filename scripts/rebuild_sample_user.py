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
    readme = sample_root / "README.md"
    readme.write_text(
        "# NIMO sample user\n\n"
        "This workspace is fully synthetic and reproducible. It is safe to use for "
        "dashboard, CLI and analysis development.\n\n"
        f"- Seed: `{args.seed}`\n"
        f"- Date range: `{args.start.isoformat()}` to `{args.end.isoformat()}`\n"
        f"- Seed-selected archetype: `{result.archetype}`\n"
        f"- Imported transactions: `{result.imported_rows}`\n"
        f"- Accounts: `{result.account_count}`\n\n"
        "Rebuild from the repository root with:\n\n"
        "```bash\npython scripts/rebuild_sample_user.py\n```\n\n"
        "The analysis code receives only the rendered statement files and normalized "
        "database. Hidden generator truth remains under `synthetic/` for future "
        "validation and must not be read by analysis services.\n",
        encoding="utf-8",
    )
    print(f"Rebuilt {result.user_name}: {result.imported_rows} rows, {result.account_count} accounts")
    print(f"Archetype: {result.archetype}")
    print(f"Manifest: {result.manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
