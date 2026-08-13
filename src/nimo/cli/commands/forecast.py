from __future__ import annotations

from datetime import date

from nimo.cli.common import container_from_args, parse_value, print_json, print_table


def register(subparsers):
    root = subparsers.add_parser("forecast", help="Build default forecasts and user scenarios")
    actions = root.add_subparsers(dest="forecast_action", required=True)

    profile = actions.add_parser("profile", help="Show the inferred default forecast profile")
    profile.add_argument("user")
    profile.add_argument("--refresh", action="store_true")
    profile.add_argument("--json", action="store_true")
    profile.set_defaults(handler=run_profile)

    scenarios = actions.add_parser("scenarios", help="List scenarios")
    scenarios.add_argument("user")
    scenarios.add_argument("--json", action="store_true")
    scenarios.set_defaults(handler=run_scenarios)

    create = actions.add_parser("create", help="Create a scenario")
    create.add_argument("user")
    create.add_argument("name")
    create.add_argument("--description", default="")
    create.add_argument("--copy-from", default="Baseline")
    create.set_defaults(handler=run_create)

    override = actions.add_parser("set", help="Set a scenario override using a dotted profile path")
    override.add_argument("user")
    override.add_argument("scenario")
    override.add_argument("path")
    override.add_argument("value")
    override.set_defaults(handler=run_set)

    event = actions.add_parser("event-add", help="Add a planned future event")
    event.add_argument("user")
    event.add_argument("scenario")
    event.add_argument("name")
    event.add_argument("date", type=date.fromisoformat)
    event.add_argument("amount", type=float, help="Positive for income, negative for cost")
    event.add_argument("--uncertainty", type=float, default=0.0)
    event.add_argument("--probability", type=float, default=1.0)
    event.add_argument("--repeat-months", type=int, default=0)
    event.set_defaults(handler=run_event)

    run_parser = actions.add_parser("run", help="Run a Monte Carlo forecast")
    run_parser.add_argument("user")
    run_parser.add_argument("--scenario", default="Baseline")
    run_parser.add_argument("--months", type=int)
    run_parser.add_argument("--runs", type=int)
    run_parser.add_argument("--seed", type=int, default=202601)
    run_parser.add_argument("--threshold", type=float)
    run_parser.add_argument("--json", action="store_true")
    run_parser.set_defaults(handler=run_forecast)

    compare = actions.add_parser("compare", help="Compare named scenarios")
    compare.add_argument("user")
    compare.add_argument("scenarios", nargs="+")
    compare.add_argument("--months", type=int)
    compare.add_argument("--runs", type=int)
    compare.add_argument("--seed", type=int, default=202601)
    compare.add_argument("--json", action="store_true")
    compare.set_defaults(handler=run_compare)

    backtest = actions.add_parser("backtest", help="Run rolling historical calibration")
    backtest.add_argument("user")
    backtest.add_argument("--holdout-months", type=int)
    backtest.add_argument("--runs", type=int)
    backtest.add_argument("--json", action="store_true")
    backtest.set_defaults(handler=run_backtest)


def run_profile(args) -> int:
    c = container_from_args(args, args.user)
    payload = c.forecasting.ensure_default_profile(force=args.refresh)
    if args.json:
        print_json(payload)
    else:
        profile = payload["profile"]
        rows = [{"assumption": "Income", "mean": profile["income"]["monthly_mean"], "std": profile["income"]["monthly_std"], "source": profile["income"]["source"]}]
        rows.extend({"assumption": value["label"], "mean": value["monthly_mean"], "std": value["monthly_std"], "source": value["source"]} for value in profile["categories"].values())
        print_table(rows, ["assumption", "mean", "std", "source"])
    return 0


def run_scenarios(args) -> int:
    rows = container_from_args(args, args.user).forecasting.scenarios()
    if args.json:
        print_json(rows)
    else:
        print_table([{"id": row["id"], "name": row["name"], "baseline": row["is_baseline"], "overrides": len(row["overrides"]), "events": len(row["events"])} for row in rows])
    return 0


def run_create(args) -> int:
    print_json(container_from_args(args, args.user).forecasting.create_scenario(args.name, description=args.description, copy_from=args.copy_from))
    return 0


def run_set(args) -> int:
    print_json(container_from_args(args, args.user).forecasting.set_override(args.scenario, args.path, parse_value(args.value)))
    return 0


def run_event(args) -> int:
    print_json(container_from_args(args, args.user).forecasting.add_event(args.scenario, name=args.name, event_date=args.date, amount=args.amount, uncertainty=args.uncertainty, probability=args.probability, repeat_months=args.repeat_months))
    return 0


def run_forecast(args) -> int:
    result = container_from_args(args, args.user).forecasting.run(scenario=args.scenario, horizon_months=args.months, runs=args.runs, seed=args.seed, threshold=args.threshold)
    if args.json:
        print_json(result)
    else:
        final = result["final_balance"]
        print_table([{"scenario": result["scenario"], "median_final_balance": final["median"], "p10": final["p10"], "p90": final["p90"], "negative_balance_probability": result["probability_negative_balance"]}])
    return 0


def run_compare(args) -> int:
    rows = container_from_args(args, args.user).forecasting.compare(args.scenarios, horizon_months=args.months, runs=args.runs, seed=args.seed)
    if args.json:
        print_json(rows)
    else:
        print_table(rows)
    return 0


def run_backtest(args) -> int:
    result = container_from_args(args, args.user).forecasting.backtest(holdout_months=args.holdout_months, runs=args.runs)
    if args.json:
        print_json(result)
    else:
        print_table(result.get("periods", []), ["month", "actual_net", "predicted_median", "inside_50", "inside_90", "absolute_error"])
        print(f"50% coverage: {float(result.get('coverage_50', 0)):.1%}; 90% coverage: {float(result.get('coverage_90', 0)):.1%}")
    return 0
