from __future__ import annotations

from nimo.cli.common import container_from_args, print_json, print_table


def register(subparsers):
    parser = subparsers.add_parser("behaviours", help="Infer and inspect user behaviour")
    parser.add_argument("user")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--scope", choices=["category", "merchant", "account"])
    parser.add_argument("--outliers", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.set_defaults(handler=run)


def run(args) -> int:
    container = container_from_args(args, args.user)
    payload = container.behaviours.refresh(force=args.refresh) if args.refresh else container.behaviours.current()
    if args.outliers:
        rows = container.behaviours.outliers_frame().to_dict(orient="records")
        if args.json:
            print_json(rows)
        else:
            print_table(rows, ["transaction_id", "scope_key", "robust_z", "surprise_score"])
        return 0
    if args.scope:
        frame = container.behaviours.patterns_frame(scope_type=args.scope)
        rows = frame.to_dict(orient="records")
        if args.json:
            print_json(rows)
        else:
            print_table(rows, ["scope_key", "sample_count", "periodic_score", "distributional_score", "spontaneous_score"])
        return 0
    if args.json:
        print_json(payload)
    else:
        archetype = payload.get("archetype", {})
        print(f"Archetype: {archetype.get('label', 'Unavailable')}")
        print(f"Confidence: {float(archetype.get('confidence', 0)):.1%}")
        rows = [
            {
                "category": key,
                "observations": value.get("sample_count"),
                "periodic": value.get("periodic", {}).get("score"),
                "distribution": value.get("distributional", {}).get("best_fit", {}).get("family") if value.get("distributional", {}).get("best_fit") else None,
                "spontaneous": value.get("spontaneous", {}).get("score"),
            }
            for key, value in payload.get("categories", {}).items()
        ]
        print_table(rows, ["category", "observations", "periodic", "distribution", "spontaneous"])
    return 0
