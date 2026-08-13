from __future__ import annotations

from datetime import date

from nimo.cli.common import container_from_args, print_json, print_table


def register(subparsers):
    root = subparsers.add_parser("goal", help="Build and simulate savings goals")
    actions = root.add_subparsers(dest="goal_action", required=True)
    listing = actions.add_parser("list")
    listing.add_argument("user")
    listing.add_argument("--json", action="store_true")
    listing.set_defaults(handler=run_list)
    add = actions.add_parser("add")
    add.add_argument("user")
    add.add_argument("name")
    add.add_argument("target", type=float)
    add.add_argument("target_date", type=date.fromisoformat)
    add.add_argument("--current", type=float, default=0.0)
    add.add_argument("--priority", type=int, default=3)
    add.add_argument("--monthly", type=float, default=0.0)
    add.add_argument("--surplus-fraction", type=float, default=0.0)
    add.set_defaults(handler=run_add)
    simulate = actions.add_parser("simulate")
    simulate.add_argument("user")
    simulate.add_argument("goal")
    simulate.add_argument("--scenario", default="Baseline")
    simulate.add_argument("--runs", type=int)
    simulate.add_argument("--seed", type=int, default=8321)
    simulate.add_argument("--json", action="store_true")
    simulate.set_defaults(handler=run_simulate)
    intervention = actions.add_parser("intervention")
    intervention.add_argument("user")
    intervention.add_argument("goal")
    intervention.add_argument("category")
    intervention.add_argument("reduction_percent", type=float)
    intervention.add_argument("--scenario", default="Baseline")
    intervention.add_argument("--runs", type=int)
    intervention.set_defaults(handler=run_intervention)


def run_list(args) -> int:
    rows = container_from_args(args, args.user).planning.goals()
    if args.json:
        print_json(rows)
    else:
        print_table(rows, ["id", "name", "current_amount", "target_amount", "target_date", "priority", "monthly_contribution"])
    return 0


def run_add(args) -> int:
    print_json(container_from_args(args, args.user).planning.add_goal(name=args.name, target_amount=args.target, target_date=args.target_date, current_amount=args.current, priority=args.priority, monthly_contribution=args.monthly, surplus_allocation_fraction=args.surplus_fraction))
    return 0


def run_simulate(args) -> int:
    result = container_from_args(args, args.user).planning.simulate_goal(args.goal, scenario=args.scenario, runs=args.runs, seed=args.seed)
    if args.json:
        print_json(result)
    else:
        print_table([{"goal": result["goal"]["name"], "probability": result["probability_achieved"], "median_final": result["median_final_amount"], "completion_median": result["completion_month_median"]}])
    return 0


def run_intervention(args) -> int:
    print_json(container_from_args(args, args.user).planning.intervention(args.goal, category_slug=args.category, reduction_fraction=args.reduction_percent / 100.0, scenario=args.scenario, runs=args.runs))
    return 0
