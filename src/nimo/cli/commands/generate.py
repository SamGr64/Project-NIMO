from __future__ import annotations

from datetime import date

from nimo.application.container import ApplicationContainer
from nimo.cli.common import config_from_args, print_json, user_service_from_args
from nimo.domain.models import GenerationRequest
from nimo.users.workspace import slugify_user_name


def register(subparsers):
    parser = subparsers.add_parser("generate", help="Generate and import seeded synthetic statements")
    parser.add_argument("user")
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--start", type=date.fromisoformat, required=True)
    parser.add_argument("--end", type=date.fromisoformat, required=True)
    parser.add_argument("--archetype")
    parser.add_argument("--format", default="seeded_random")
    parser.add_argument("--json", action="store_true")
    parser.set_defaults(handler=run)


def run(args) -> int:
    config = config_from_args(args)
    users = user_service_from_args(args)
    if slugify_user_name(args.user) not in users.list():
        users.create(args.user, source_type="generated")
    container = ApplicationContainer.for_user(
        args.user,
        project_root=config.paths.project_root,
        data_root=config.paths.data_root,
    )
    result = container.generation.generate(
        GenerationRequest(
            user_name=container.workspace.slug,
            seed=args.seed,
            start_date=args.start,
            end_date=args.end,
            archetype=args.archetype,
            statement_format=args.format,
        )
    )
    if args.json:
        print_json(result)
    else:
        print(f"Generated user: {result.user_name}")
        print(f"Seed/archetype: {result.seed} / {result.archetype}")
        print(f"Accounts: {result.account_count}")
        print(f"Imported rows: {result.imported_rows}")
        for path in result.statement_paths:
            print(f"Statement: {path}")
        print(f"Manifest: {result.manifest_path}")
    return 0
