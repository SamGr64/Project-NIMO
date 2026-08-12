from __future__ import annotations

from nimo.cli.common import print_table, user_service_from_args


def register(subparsers):
    parser = subparsers.add_parser("user", help="Create and list user workspaces")
    nested = parser.add_subparsers(dest="user_command", required=True)

    create = nested.add_parser("create", help="Create a user workspace")
    create.add_argument("name")
    create.add_argument("--display-name")
    create.add_argument("--source-type", choices=["imported", "generated"], default="imported")
    create.set_defaults(handler=create_user)

    list_parser = nested.add_parser("list", help="List user workspaces")
    list_parser.set_defaults(handler=list_users)


def create_user(args) -> int:
    service = user_service_from_args(args)
    workspace = service.create(
        args.name,
        display_name=args.display_name,
        source_type=args.source_type,
    )
    print(f"Created user workspace: {workspace.slug} ({workspace.root})")
    return 0


def list_users(args) -> int:
    service = user_service_from_args(args)
    print_table([{"user": user} for user in service.list()], ["user"])
    return 0
