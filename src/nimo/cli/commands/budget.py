from __future__ import annotations

from nimo.cli.common import container_from_args, print_json, print_table


def register(subparsers):
    root = subparsers.add_parser("budget", help="Create and evaluate budgets")
    actions = root.add_subparsers(dest="budget_action", required=True)
    show = actions.add_parser("show")
    show.add_argument("user")
    show.add_argument("--budget", default="NIMO Baseline")
    show.add_argument("--refresh", action="store_true")
    show.add_argument("--json", action="store_true")
    show.set_defaults(handler=run_show)
    create = actions.add_parser("create")
    create.add_argument("user")
    create.add_argument("name")
    create.add_argument("--mode", default="category")
    create.add_argument("--empty", action="store_true")
    create.set_defaults(handler=run_create)
    set_line = actions.add_parser("set")
    set_line.add_argument("user")
    set_line.add_argument("budget")
    set_line.add_argument("category")
    set_line.add_argument("amount", type=float)
    set_line.add_argument("--label")
    set_line.add_argument("--essential", action="store_true")
    set_line.set_defaults(handler=run_set)
    evaluate = actions.add_parser("evaluate")
    evaluate.add_argument("user")
    evaluate.add_argument("--budget", default="NIMO Baseline")
    evaluate.add_argument("--scenario", default="Baseline")
    evaluate.add_argument("--runs", type=int)
    evaluate.add_argument("--json", action="store_true")
    evaluate.set_defaults(handler=run_evaluate)


def run_show(args) -> int:
    c = container_from_args(args, args.user)
    if args.refresh:
        c.planning.ensure_default_budget(force=True)
    budgets = c.planning.budgets()
    payload = next((item for item in budgets if item["name"] == args.budget or str(item["id"]) == args.budget), None)
    if payload is None:
        raise KeyError(args.budget)
    if args.json:
        print_json(payload)
    else:
        print_table(payload["lines"], ["category_slug", "label", "amount", "source", "is_essential"])
    return 0


def run_create(args) -> int:
    print_json(container_from_args(args, args.user).planning.create_budget(args.name, mode=args.mode, copy_default=not args.empty))
    return 0


def run_set(args) -> int:
    print_json(container_from_args(args, args.user).planning.set_line(args.budget, args.category, args.amount, label=args.label, essential=args.essential))
    return 0


def run_evaluate(args) -> int:
    result = container_from_args(args, args.user).planning.evaluate(args.budget, scenario=args.scenario, runs=args.runs)
    if args.json:
        print_json(result)
    else:
        print_table(result["lines"], ["label", "amount", "current_period_actual", "forecast_median", "probability_within_budget"])
    return 0
