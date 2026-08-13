from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from nimo.application.container import ApplicationContainer
from nimo.cli.common import config_from_args, print_json, user_service_from_args
from nimo.domain.models import GenerationRequest
from nimo.users.workspace import slugify_user_name


def register(subparsers):
    parser = subparsers.add_parser("generate", help="Generate and import seeded synthetic statements")
    parser.add_argument("user")
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--start", type=date.fromisoformat, required=True)
    parser.add_argument("--end", type=date.fromisoformat, required=True)
    parser.add_argument("--archetype")
    parser.add_argument(
        "--answer",
        action="append",
        default=[],
        metavar="QUESTION=ANSWER",
        help="Financial-twin questionnaire answer; repeat for multiple answers",
    )
    parser.add_argument(
        "--questionnaire-file",
        type=Path,
        help="JSON or YAML mapping of questionnaire question IDs to answer IDs",
    )
    parser.add_argument("--format", default="seeded_random")
    parser.add_argument("--json", action="store_true")
    parser.set_defaults(handler=run)


def run(args) -> int:
    config = config_from_args(args)
    users = user_service_from_args(args)
    if slugify_user_name(args.user) not in users.list():
        users.create(args.user, source_type="generated")
    container = ApplicationContainer.for_user(
        args.user,
        project_root=config.paths.project_root,
        data_root=config.paths.data_root,
    )
    questionnaire = _questionnaire_answers(args.questionnaire_file, args.answer)
    result = container.generation.generate(
        GenerationRequest(
            user_name=container.workspace.slug,
            seed=args.seed,
            start_date=args.start,
            end_date=args.end,
            archetype=args.archetype,
            questionnaire=questionnaire or None,
            statement_format=args.format,
        )
    )
    if args.json:
        print_json(result)
    else:
        print(f"Generated user: {result.user_name}")
        print(f"Seed/archetype: {result.seed} / {result.archetype}")
        if questionnaire:
            print(f"Questionnaire answers: {len(questionnaire)}")
        print(f"Accounts: {result.account_count}")
        print(f"Imported rows: {result.imported_rows}")
        for path in result.statement_paths:
            print(f"Statement: {path}")
        print(f"Manifest: {result.manifest_path}")
    return 0


def _questionnaire_answers(path: Path | None, pairs: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    if path is not None:
        payload = _load_questionnaire_file(path)
        source = payload.get("answers", payload) if isinstance(payload, dict) else payload
        if not isinstance(source, dict):
            raise TypeError("Questionnaire file must contain a mapping or an 'answers' mapping")
        result.update({str(key): str(value) for key, value in source.items()})
    for pair in pairs:
        if "=" not in pair:
            raise ValueError(f"Invalid questionnaire answer {pair!r}; expected QUESTION=ANSWER")
        question, answer = pair.split("=", 1)
        question, answer = question.strip(), answer.strip()
        if not question or not answer:
            raise ValueError(f"Invalid questionnaire answer {pair!r}; both IDs are required")
        result[question] = answer
    return result


def _load_questionnaire_file(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(path)
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        return json.loads(text)
    return yaml.safe_load(text)
