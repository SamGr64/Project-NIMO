from __future__ import annotations

import getpass
import os
from pathlib import Path

from nimo.cli.common import config_from_args, container_from_args, print_json
from nimo.hardening import restore_backup, verify_backup


def register(subparsers):
    root = subparsers.add_parser("backup", help="Create, verify and restore user backups")
    actions = root.add_subparsers(dest="backup_action", required=True)
    create = actions.add_parser("create")
    create.add_argument("user")
    create.add_argument("--output", type=Path)
    create.add_argument("--include-cache", action="store_true")
    create.add_argument("--encrypt", action="store_true")
    create.add_argument("--passphrase-env", default="NIMO_BACKUP_PASSPHRASE")
    create.set_defaults(handler=run_create)
    verify = actions.add_parser("verify")
    verify.add_argument("path", type=Path)
    verify.add_argument("--encrypted", action="store_true")
    verify.add_argument("--passphrase-env", default="NIMO_BACKUP_PASSPHRASE")
    verify.set_defaults(handler=run_verify)
    restore = actions.add_parser("restore")
    restore.add_argument("path", type=Path)
    restore.add_argument("--user")
    restore.add_argument("--overwrite", action="store_true")
    restore.add_argument("--encrypted", action="store_true")
    restore.add_argument("--passphrase-env", default="NIMO_BACKUP_PASSPHRASE")
    restore.set_defaults(handler=run_restore)


def _passphrase(args, required: bool) -> str | None:
    value = os.getenv(args.passphrase_env)
    if value:
        return value
    if required:
        return getpass.getpass("Backup passphrase: ")
    return None


def run_create(args) -> int:
    c = container_from_args(args, args.user)
    path = c.backups.create(output_path=args.output, include_cache=args.include_cache, passphrase=_passphrase(args, args.encrypt))
    print(path)
    return 0


def run_verify(args) -> int:
    print_json(verify_backup(args.path, passphrase=_passphrase(args, args.encrypted)))
    return 0


def run_restore(args) -> int:
    config = config_from_args(args)
    workspace = restore_backup(args.path, data_root=config.paths.data_root, user_name=args.user, passphrase=_passphrase(args, args.encrypted), overwrite=args.overwrite)
    print(workspace.root)
    return 0
