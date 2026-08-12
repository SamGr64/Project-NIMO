from __future__ import annotations

from nimo.cli.common import container_from_args, print_json, print_table


def register(subparsers):
    parser = subparsers.add_parser("cashflow", help="Show external and internal money flows")
    parser.add_argument("user")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--confirm", nargs=2, type=int, metavar=("DEBIT_ID", "CREDIT_ID"))
    parser.add_argument("--unmatch", metavar="TRANSFER_GROUP_ID")
    parser.set_defaults(handler=run)


def run(args) -> int:
    container = container_from_args(args, args.user)
    if args.confirm:
        group_id = container.transfer_detector.confirm_pair(args.confirm[0], args.confirm[1])
        print(f"Confirmed transfer group: {group_id}")
    if args.unmatch:
        removed = container.transfer_detector.unmatch_group(args.unmatch)
        print("Transfer match rejected." if removed else "Transfer group was not found.")
    payload = container.analysis.cashflow()
    if args.json:
        print_json(payload)
    else:
        print_table(
            [
                {
                    "source": link["source_label"],
                    "target": link["target_label"],
                    "value": link["value"],
                    "type": link["flow_type"],
                    "confidence": link["confidence"],
                }
                for link in payload["links"]
            ],
            ["source", "target", "value", "type", "confidence"],
        )
    return 0
