from __future__ import annotations

import json

from nimo.cli.common import container_from_args, print_json, print_table


def register(subparsers):
    root = subparsers.add_parser("invest", help="Use the educational investing sandbox")
    actions = root.add_subparsers(dest="invest_action", required=True)
    assets = actions.add_parser("assets")
    assets.add_argument("user")
    assets.add_argument("--json", action="store_true")
    assets.set_defaults(handler=run_assets)
    stats = actions.add_parser("stats")
    stats.add_argument("user")
    stats.add_argument("symbols", nargs="*")
    stats.add_argument("--json", action="store_true")
    stats.set_defaults(handler=run_stats)
    portfolios = actions.add_parser("portfolios")
    portfolios.add_argument("user")
    portfolios.add_argument("--json", action="store_true")
    portfolios.set_defaults(handler=run_portfolios)
    create = actions.add_parser("create")
    create.add_argument("user")
    create.add_argument("name")
    create.add_argument("allocations_json", nargs="?", help='Optional JSON, for example {"GLOBAL_EQ":0.6,"BOND":0.4}')
    create.add_argument("--allocation", action="append", default=[], metavar="SYMBOL=WEIGHT", help="Repeat for a PowerShell-friendly portfolio definition")
    create.add_argument("--rule", choices=["fixed", "percent_income", "percent_surplus", "threshold", "goal_aware"], default="fixed")
    create.add_argument("--monthly", "--amount", dest="amount", type=float, default=100.0)
    create.add_argument("--fraction", type=float, default=0.25)
    create.add_argument("--cash-threshold", type=float, default=5000.0)
    create.add_argument("--minimum-cash", type=float, default=5000.0)
    create.set_defaults(handler=run_create)
    simulate = actions.add_parser("simulate")
    simulate.add_argument("user")
    simulate.add_argument("--portfolio", default="Balanced Learning Portfolio")
    simulate.add_argument("--scenario", default="Baseline")
    simulate.add_argument("--years", type=int)
    simulate.add_argument("--runs", type=int)
    simulate.add_argument("--seed", type=int, default=44021)
    simulate.add_argument("--stress", choices=["market_drop", "income_drop", "unexpected_expense"])
    simulate.add_argument("--json", action="store_true")
    simulate.set_defaults(handler=run_simulate)


def run_assets(args) -> int:
    rows = container_from_args(args, args.user).investing.assets()
    if args.json:
        print_json(rows)
    else:
        print_table(rows, ["symbol", "name", "asset_type", "latest_date", "latest_price", "is_synthetic"])
    return 0


def run_stats(args) -> int:
    rows = container_from_args(args, args.user).investing.statistics(args.symbols or None)
    if args.json:
        print_json(rows)
    else:
        print_table(rows, ["symbol", "annualised_return", "annualised_volatility", "maximum_drawdown", "one_year_return", "five_year_annualised_return"])
    return 0


def run_portfolios(args) -> int:
    rows = container_from_args(args, args.user).investing.portfolios()
    if args.json:
        print_json(rows)
    else:
        print_table([{"id": row["id"], "name": row["name"], "allocations": row["allocations"], "contribution_rule": row["contribution_rule"]} for row in rows])
    return 0


def run_create(args) -> int:
    allocations = _allocations(args.allocations_json, args.allocation)
    rule = {"type": args.rule, "amount": args.amount}
    if args.rule in {"percent_income", "percent_surplus", "threshold"}:
        rule["fraction"] = args.fraction
    if args.rule == "threshold":
        rule["cash_threshold"] = args.cash_threshold
    if args.rule == "goal_aware":
        rule["minimum_cash"] = args.minimum_cash
    print_json(
        container_from_args(args, args.user).investing.create_portfolio(
            args.name,
            allocations=allocations,
            contribution_rule=rule,
        )
    )
    return 0


def run_simulate(args) -> int:
    result = container_from_args(args, args.user).investing.simulate(args.portfolio, scenario=args.scenario, horizon_years=args.years, runs=args.runs, seed=args.seed, stress_name=args.stress)
    if args.json:
        print_json(result)
    else:
        final = result["final_value"]
        print_table([{"portfolio": result["portfolio"]["name"], "median_final": final["median"], "p10": final["p10"], "p90": final["p90"], "negative_cash_probability": result["probability_negative_cash"], "stress": result["stress_name"]}])
    return 0


def _allocations(json_value: str | None, pairs: list[str]) -> dict[str, float]:
    if json_value and pairs:
        raise ValueError("Use either allocations_json or repeated --allocation values, not both")
    if json_value:
        payload = json.loads(json_value)
        if not isinstance(payload, dict):
            raise ValueError("Portfolio allocation JSON must be an object")
        return {str(key).upper(): float(value) for key, value in payload.items()}
    if not pairs:
        raise ValueError("Provide allocation JSON or at least one --allocation SYMBOL=WEIGHT")
    result: dict[str, float] = {}
    for item in pairs:
        if "=" not in item:
            raise ValueError(f"Invalid allocation {item!r}; expected SYMBOL=WEIGHT")
        symbol, value = item.split("=", 1)
        symbol = symbol.strip().upper()
        if not symbol:
            raise ValueError("Allocation symbol cannot be empty")
        result[symbol] = float(value)
    return result
