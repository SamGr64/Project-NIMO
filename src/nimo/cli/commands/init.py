from __future__ import annotations

from datetime import date

from nimo.application.container import ApplicationContainer
from nimo.cli.common import config_from_args
from nimo.domain.models import GenerationRequest


def register(subparsers):
    parser = subparsers.add_parser("init", help="Initialise the NIMO data directory")
    parser.add_argument("--sample", action="store_true", help="Build the sample_user demonstration profile")
    parser.add_argument("--sample-seed", type=int, default=42)
    parser.set_defaults(handler=run)


def run(args) -> int:
    config = config_from_args(args)
    config.paths.data_root.mkdir(parents=True, exist_ok=True)
    print(f"Initialised NIMO data root: {config.paths.data_root}")
    if args.sample:
        container = ApplicationContainer.for_user(
            "sample_user",
            project_root=config.paths.project_root,
            data_root=config.paths.data_root,
            create=True,
            display_name="Sample User",
            source_type="generated",
        )
        result = container.generation.generate(
            GenerationRequest(
                user_name="sample_user",
                seed=args.sample_seed,
                start_date=date(2024, 1, 1),
                end_date=date(2026, 7, 31),
            )
        )
        print(
            f"Built sample_user: {result.imported_rows} rows across {result.account_count} accounts "
            f"using archetype {result.archetype}."
        )
    return 0
