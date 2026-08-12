from __future__ import annotations

from datetime import date

from nimo.cli.common import container_from_args, print_json, print_table


def register(subparsers):
    analyse = subparsers.add_parser("analyse", help="Run basic analysis for a user")
    analyse.add_argument("user")
    analyse.add_argument("--start", type=date.fromisoformat)
    analyse.add_argument("--end", type=date.fromisoformat)
    analyse.add_argument("--refresh", action="store_true")
    analyse.add_argument("--json", action="store_true")
    analyse.set_defaults(handler=run_analysis)

    accounts = subparsers.add_parser("accounts", help="Show account summaries")
    accounts.add_argument("user")
    accounts.add_argument("--json", action="store_true")
    accounts.set_defaults(handler=run_accounts)

    transactions = subparsers.add_parser("transactions", help="Show normalised transactions")
    transactions.add_argument("user")
    transactions.add_argument("--limit", type=int, default=30)
    transactions.add_argument("--json", action="store_true")
    transactions.set_defaults(handler=run_transactions)


def run_analysis(args) -> int:
    container = container_from_args(args, args.user)
    if args.refresh:
        container.analysis.refresh()
    metrics = container.analysis.overview(start_date=args.start, end_date=args.end)
    if args.json:
        print_json(metrics.as_dict())
        return 0
    rows = [
        {"metric": "Total balance", "value": metrics.total_balance},
        {"metric": "Income", "value": metrics.total_income},
        {"metric": "External spend", "value": metrics.total_spend},
        {"metric": "Net cash flow", "value": metrics.net_cash_flow},
        {"metric": "Savings rate", "value": None if metrics.savings_rate is None else metrics.savings_rate * 100},
        {"metric": "Current month spend", "value": metrics.current_month_spend},
        {"metric": "Projected month end", "value": metrics.projected_month_end_spend},
        {"metric": "Weighted monthly spend", "value": metrics.weighted_monthly_spend},
        {"metric": "Uncategorised", "value": metrics.uncategorised_count},
    ]
    print_table(rows, ["metric", "value"])
    return 0


def run_accounts(args) -> int:
    container = container_from_args(args, args.user)
    frame = container.analysis.accounts()
    rows = frame.to_dict(orient="records")
    if args.json:
        print_json(rows)
    else:
        print_table(rows, ["account_id", "account_name", "account_type", "balance", "income", "spend", "transaction_count"])
    return 0


def run_transactions(args) -> int:
    container = container_from_args(args, args.user)
    frame = container.analysis.transaction_frame().sort_values(["booking_date", "id"], ascending=False).head(args.limit)
    rows = frame.to_dict(orient="records")
    if args.json:
        print_json(rows)
    else:
        print_table(rows, ["id", "booking_date", "account_name", "description_raw", "amount", "category_slug", "transfer_group_id"])
    return 0
