from __future__ import annotations

from pathlib import Path

from nimo.cli.common import container_from_args, print_json, print_table


def register(subparsers):
    parser = subparsers.add_parser("doctor", help="Check database, provenance and cache integrity")
    parser.add_argument("user")
    parser.add_argument("--json", action="store_true")
    parser.set_defaults(handler=run)


def run(args) -> int:
    result = container_from_args(args, args.user).backups.doctor()
    if args.json:
        print_json(result)
    else:
        print_table(result["checks"], ["name", "passed", "detail"])
        print("Healthy" if result["healthy"] else "One or more checks failed")
    return 0 if result["healthy"] else 2
