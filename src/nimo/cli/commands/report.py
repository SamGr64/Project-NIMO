from __future__ import annotations

from datetime import date

from nimo.cli.common import container_from_args, print_json, print_table


def register(subparsers):
    root = subparsers.add_parser("report", help="Build evidence-controlled reports")
    actions = root.add_subparsers(dest="report_action", required=True)
    build = actions.add_parser("build")
    build.add_argument("user")
    build.add_argument("--start", type=date.fromisoformat)
    build.add_argument("--end", type=date.fromisoformat)
    build.add_argument("--format", action="append", dest="formats", choices=["html", "md", "pdf", "docx"])
    build.add_argument("--llm", action="store_true", help="Use the optional OpenAI narrative provider")
    build.add_argument("--model")
    build.add_argument("--no-forecast", action="store_true")
    build.add_argument("--no-budget", action="store_true")
    build.add_argument("--no-investing", action="store_true")
    build.add_argument("--json", action="store_true")
    build.set_defaults(handler=run_build)
    listing = actions.add_parser("list")
    listing.add_argument("user")
    listing.add_argument("--json", action="store_true")
    listing.set_defaults(handler=run_list)


def run_build(args) -> int:
    result = container_from_args(args, args.user).reporting.build(period_start=args.start, period_end=args.end, formats=args.formats, use_llm=args.llm, model=args.model, include_forecast=not args.no_forecast, include_budget=not args.no_budget, include_investing=not args.no_investing)
    if args.json:
        print_json(result)
    else:
        print_table([{"format": key, "path": value} for key, value in result["outputs"].items()])
    return 0


def run_list(args) -> int:
    rows = container_from_args(args, args.user).reporting.list()
    if args.json:
        print_json(rows)
    else:
        print_table(rows, ["id", "period_start", "period_end", "provider", "model", "created_at"])
    return 0
