from __future__ import annotations

from pathlib import Path

from nimo.application.container import ApplicationContainer
from nimo.cli.common import config_from_args, print_json, user_service_from_args
from nimo.users.workspace import slugify_user_name


def register(subparsers):
    parser = subparsers.add_parser("import", help="Import a CSV bank statement")
    parser.add_argument("user")
    parser.add_argument("statement", type=Path)
    parser.add_argument("--account-name")
    parser.add_argument("--account-type")
    parser.add_argument("--json", action="store_true")
    parser.set_defaults(handler=run)


def run(args) -> int:
    config = config_from_args(args)
    users = user_service_from_args(args)
    if slugify_user_name(args.user) not in users.list():
        users.create(args.user, source_type="imported")
    container = ApplicationContainer.for_user(
        args.user,
        project_root=config.paths.project_root,
        data_root=config.paths.data_root,
    )
    result = container.ingestion.import_csv(
        args.statement,
        account_name=args.account_name,
        account_type=args.account_type,
    )
    if args.json:
        print_json(result)
    elif result.duplicate_file:
        print("Exact source file already imported; no rows added.")
    else:
        print(f"Imported rows: {result.imported_rows}")
        print(f"Superseded older overlapping rows: {result.superseded_rows}")
        print(f"Coverage: {result.coverage_start} to {result.coverage_end}")
        for warning in result.warnings:
            print(f"Warning: {warning}")
    return 0
