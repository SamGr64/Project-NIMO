from __future__ import annotations

from pathlib import Path

from nimo.cli.common import container_from_args, print_json, print_table


def register(subparsers):
    parser = subparsers.add_parser("categories", help="Manage transaction categories")
    nested = parser.add_subparsers(dest="category_command", required=True)

    list_parser = nested.add_parser("list")
    list_parser.add_argument("user")
    list_parser.add_argument("--json", action="store_true")
    list_parser.set_defaults(handler=list_categories)

    auto = nested.add_parser("auto")
    auto.add_argument("user")
    auto.set_defaults(handler=auto_categories)

    assign = nested.add_parser("assign")
    assign.add_argument("user")
    assign.add_argument("category")
    assign.add_argument("transaction_ids", nargs="+", type=int)
    assign.set_defaults(handler=assign_category)

    custom = nested.add_parser("custom")
    custom.add_argument("user")
    custom.add_argument("slug")
    custom.add_argument("label")
    custom.add_argument("--direction", choices=["credit", "debit", "either"], default="either")
    custom.set_defaults(handler=create_custom)

    rule = nested.add_parser("rule-add")
    rule.add_argument("user")
    rule.add_argument("name")
    rule.add_argument("pattern")
    rule.add_argument("category")
    rule.add_argument("--regex", action="store_true")
    rule.add_argument("--field", choices=["description", "merchant"], default="description")
    rule.set_defaults(handler=add_rule)

    export = nested.add_parser("export")
    export.add_argument("user")
    export.set_defaults(handler=export_categories)

    import_parser = nested.add_parser("import", help="Import reviewed LLM category suggestions")
    import_parser.add_argument("user")
    import_parser.add_argument("path", type=Path)
    import_parser.add_argument("--override-builtin", action="store_true")
    import_parser.set_defaults(handler=import_categories)


def list_categories(args) -> int:
    service = container_from_args(args, args.user).categorisation
    rows = service.list_categories()
    if args.json:
        print_json(rows)
    else:
        print_table(rows, ["slug", "label", "direction", "is_custom"])
    return 0


def auto_categories(args) -> int:
    result = container_from_args(args, args.user).categorisation.auto_categorise()
    print_json(result)
    return 0


def assign_category(args) -> int:
    count = container_from_args(args, args.user).categorisation.assign_manual(
        args.transaction_ids, args.category
    )
    print(f"Assigned {count} transactions to {args.category}.")
    return 0


def create_custom(args) -> int:
    category_id = container_from_args(args, args.user).categorisation.create_custom_category(
        slug=args.slug,
        label=args.label,
        direction=args.direction,
    )
    print(f"Created/located category id {category_id}.")
    return 0


def add_rule(args) -> int:
    rule_id = container_from_args(args, args.user).categorisation.add_rule(
        name=args.name,
        pattern=args.pattern,
        category_slug=args.category,
        is_regex=args.regex,
        field=args.field,
    )
    print(f"Created category rule {rule_id}.")
    return 0


def export_categories(args) -> int:
    csv_path, prompt_path = container_from_args(args, args.user).categorisation.export_for_llm()
    print(f"Transactions: {csv_path}")
    print(f"Master prompt: {prompt_path}")
    return 0


def import_categories(args) -> int:
    result = container_from_args(args, args.user).categorisation.import_llm_suggestions(
        args.path, override_builtin=args.override_builtin
    )
    print_json(result)
    return 0
