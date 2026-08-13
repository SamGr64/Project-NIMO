from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from nimo.cli.common import container_from_args


def register(subparsers):
    parser = subparsers.add_parser("export", help="Export normalised active transactions")
    parser.add_argument("user")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--format", choices=["csv", "json"], default="csv")
    parser.set_defaults(handler=run)


def run(args) -> int:
    c = container_from_args(args, args.user)
    frame = c.analysis.transaction_frame()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = args.output or c.workspace.exports_dir / f"normalised_transactions_{timestamp}.{args.format}"
    output.parent.mkdir(parents=True, exist_ok=True)
    if args.format == "csv":
        frame.to_csv(output, index=False)
    else:
        output.write_text(frame.to_json(orient="records", date_format="iso", indent=2), encoding="utf-8")
    print(output)
    return 0
