"""Policy-driven seeded random CSV bank-statement generator."""

from __future__ import annotations

import argparse
import random
import sys
from calendar import monthrange
from datetime import date
from pathlib import Path
from typing import Any
import pandas as pd
import yaml
from pydantic import ValidationError

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from nimo.generator.behaviours import build_behavioural_amount
    from nimo.generator.configurations import GeneratorPolicy, Modes
    from nimo.utils import cryptic_id, dump_csv, load_yaml_mapping, normalise_text_aggressive
    from nimo.analysis.statements import analyse_statement_df
else:
    from .generator.behaviours import build_behavioural_amount
    from .generator.configurations import GeneratorPolicy, Modes
    from .utils import cryptic_id, dump_csv, load_yaml_mapping, normalise_text_aggressive
    from .analysis.statements import analyse_statement_df

GENERATOR_VERSION = "5.0.0"


class StatementGenerator:
    def __init__(self, seed: int, policy: GeneratorPolicy) -> None:
        self.seed = seed
        self.policy = policy
        self.rng = random.Random(seed)

    def probability_passes(self, probability: float) -> bool:
        return self.rng.random() < probability

    def positive_normal_int(self) -> int:
        cfg = self.policy.statement_length
        while True:
            value = round(self.rng.gauss(cfg.mean, cfg.std))
            if value >= cfg.minimum:
                return value

    def choose_bank(self, requested_bank: str | None) -> str:
        if requested_bank:
            return requested_bank
        banks = self.policy.default_banks
        return banks if isinstance(banks, str) else self.rng.choice(banks)

    def choose_account_type(self) -> str:
        selected = self.rng.choice(self.policy.account_types)
        if isinstance(selected, list):
            if not selected:
                raise ValueError("account_types contains an empty category")
            return str(self.rng.choice(selected))
        return str(selected)

    def choose_amount_mode(self) -> Modes:
        modes: list[Modes] = ["merge", "split"]
        weights = [
            self.policy.amount_modes.merge,
            self.policy.amount_modes.split,
        ]
        return self.rng.choices(modes, weights=weights, k=1)[0]

    def choose_curency_mode(self) -> Modes:
        modes: list[Modes] = ["merge", "split"]
        weights = [
            self.policy.currency_modes.merge,
            self.policy.currency_modes.split,
        ]
        return self.rng.choices(modes, weights=weights, k=1)[0]

    def choose_descript_mode(self) -> Modes:
        modes: list[Modes] = ["merge", "split"]
        weights = [
            self.policy.descript_modes.merge,
            self.policy.descript_modes.split,
        ]
        return self.rng.choices(modes, weights=weights, k=1)[0]

    def uniform_dates(self, length: int) -> list[pd.Timestamp]:
        lower, upper = self.policy.date_generation.year_range
        year = self.rng.randint(lower, upper)
        month = self.rng.randint(1, 12)
        start = date(year, month, 1)
        end = date(year, month, monthrange(year, month)[1])
        return self.rng.choices(list(pd.date_range(start, end)), k=length)

    def amount_for_date(self, date_value: date, base_amount: float) -> float:
        return build_behavioural_amount(base_amount, date_value, self.rng, self.policy.model_dump(mode="python"))

    def bimodal_amounts(self, length: int) -> list[float]:
        cfg = self.policy.amount_generation
        values: list[float] = []
        while len(values) < length:
            centre = cfg.positive_centre if self.probability_passes(cfg.deposit_probability) else cfg.negative_centre
            amount = round(self.rng.gauss(centre, cfg.positive_std if self.probability_passes(cfg.deposit_probability) else cfg.negative_std), cfg.decimal_places)
            if not cfg.forbid_zero or amount != 0:
                values.append(amount)
        return values

    def account_number_value(self) -> str:
        digits = self.policy.account_number.digits
        return f"{self.rng.randrange(10 ** digits):0{digits}d}"

    def sort_code_value(self) -> str:
        cfg = self.policy.sort_code
        digits = f"{self.rng.randrange(10 ** cfg.digits):0{cfg.digits}d}"
        if self.probability_passes(cfg.hyphen_probability):
            return "-".join(digits[index:index + 2] for index in range(0, cfg.digits, 2))
        return digits

    def choose_nested_value(self, values: list[Any]) -> str:
        if not values:
            raise ValueError("Cannot choose from an empty policy list")
        selected = self.rng.choice(values)
        if isinstance(selected, list):
            if not selected:
                raise ValueError("Policy contains an empty nested alias list")
            selected = self.rng.choice(selected)
        return str(selected)

    def field_is_enabled(self, field: str) -> bool:
        inclusion = self.policy.field_inclusion
        if field in inclusion.required:
            return True
        probability = inclusion.optional_probabilities.get(field)
        return probability is not None and self.probability_passes(probability)

    def build_descript_columns(self, amounts: list[float], mode: Modes) -> dict[str, list[Any]]:
        fmt = self.policy.descript_modes.description_format
        descriptions = self.policy.descriptions
        transaction_types = self.policy.transaction_types

        def choose_for_value(value: float) -> tuple[str, str]:
            primary = "deposit" if value > 0 else "withdrawal"
            descript_choices = list(descriptions.get(primary, []))
            descript_choices.extend(descriptions.get("either", []))
            type_choices = list(transaction_types.get(primary, []))
            type_choices.extend(transaction_types.get("either", []))
            return self.choose_nested_value(type_choices), self.choose_nested_value(descript_choices)

        if mode == "merge":
            values = [choose_for_value(value) for value in amounts]
            return {
                "description": [
                    fmt.format(transaction_type=transaction_type, description=description)
                    for transaction_type, description in values
                ]
            }

        transaction_type_values: list[str] = []
        description_values: list[str] = []
        for value in amounts:
            transaction_type, description = choose_for_value(value)
            transaction_type_values.append(transaction_type)
            description_values.append(description)
        return {
            "transaction_type": transaction_type_values,
            "description": description_values,
        }


    def build_amount_columns(self, amounts: list[float], amount_mode: Modes, currency_mode: Modes) -> dict[str, list[Any]]:
        currency = self.policy.currency_modes.currency
        fmt = self.policy.amount_modes.append_format
        if amount_mode == currency_mode == "merge":
            return {"amount": [fmt.format(amount=value, currency=currency) for value in amounts]}
        elif amount_mode == "split" and currency_mode == "merge":
            return {"deposits": [fmt.format(amount=value, currency=currency) if value > 0 else "" for value in amounts],
                    "withdrawals": [fmt.format(amount=abs(value) if value < 0 else "", currency=currency) for value in amounts]}
        elif amount_mode == currency_mode == "split":
            return{"deposits": [fmt.format(amount=value, currency=currency) if value > 0 else "" for value in amounts],
                   "withdrawals": [fmt.format(amount=abs(value) if value < 0 else "", currency=currency) for value in amounts],
                   "currency": [currency] * len(amounts)}
        return {"amount": amounts, "currency": [currency] * len(amounts)}

    def choose_output_aliases(self, canonical_columns: list[str]) -> dict[str, str]:
        chosen: dict[str, str] = {}
        used: set[str] = set()
        for canonical in canonical_columns:
            candidates = list(self.policy.aliases.get(canonical, [canonical]))
            self.rng.shuffle(candidates)
            alias = next((candidate for candidate in candidates if candidate not in used), None)
            if alias is None:
                raise ValueError(f"No collision-free alias available for {canonical!r}")
            chosen[canonical] = alias
            used.add(alias)
        return chosen

    def build_statement(self, requested_bank: str | None = None) -> tuple[pd.DataFrame, str]:
        length = self.positive_normal_int()
        bank = self.choose_bank(requested_bank)
        dates = self.uniform_dates(length)
        base_amounts = self.bimodal_amounts(length)
        amounts = [self.amount_for_date(day, amount) for day, amount in zip(dates, base_amounts)]
        amount_mode = self.choose_amount_mode()
        currency_mode = self.choose_curency_mode()
        descript_mode = self.choose_descript_mode()

        columns: dict[str, list[Any]] = {"date": dates, "_numeric_amount": amounts}

        scalar_builders: dict[str, Any] = {
            "bank_name": lambda: bank,
            "account_number": self.account_number_value,
            "sort_code": self.sort_code_value,
            "account_type": self.choose_account_type,
        }
        for field, builder in scalar_builders.items():
            if self.field_is_enabled(field):
                columns[field] = [builder()] * length

        columns.update(self.build_descript_columns(amounts, descript_mode))
        columns.update(self.build_amount_columns(amounts, amount_mode, currency_mode))

        frame = pd.DataFrame(columns)
        frame["date"] = pd.to_datetime(frame["date"])
        frame = frame.sort_values("date").reset_index(drop=True)

        if self.field_is_enabled("running_balance"):
            frame["running_balance"] = frame["_numeric_amount"].cumsum().round(
                self.policy.amount_generation.decimal_places
            )

        frame = frame.drop(columns="_numeric_amount")
        canonical_order = [column for column in self.policy.output.column_order if column in frame.columns]
        canonical_order.extend(column for column in frame.columns if column not in canonical_order)
        frame = frame[canonical_order]

        aliases = self.choose_output_aliases(frame.columns.tolist())
        return frame.rename(columns=aliases), bank

    def output_filename(self, bank: str) -> str:
        return self.policy.output.filename_template.format(
            bank=normalise_text_aggressive(bank),
            bank_id=cryptic_id(bank, self.policy.identifiers.bank_id_length),
            seed=self.seed,
            schema_version=self.policy.schema_version,
        )


class StatementValidationError(ValueError):
    pass


def validate_statement(df: pd.DataFrame, policy: GeneratorPolicy) -> None:
    if df.empty:
        raise StatementValidationError("Generated statement is empty")
    if df.columns.duplicated().any():
        raise StatementValidationError("Generated statement contains duplicate output aliases")

    alias_to_canonical = {
        alias: canonical
        for canonical, aliases in policy.aliases.items()
        for alias in aliases
    }
    canonical_present = {alias_to_canonical.get(column, column) for column in df.columns}

    for required in policy.field_inclusion.required:
        if required == "amount":
            amount_shape_present = "amount" in canonical_present or {
                "deposits", "withdrawals"
            }.issubset(canonical_present)
            if not amount_shape_present:
                raise StatementValidationError("Required amount representation is missing")
        elif required not in canonical_present:
            raise StatementValidationError(f"Required field is missing: {required}")


def load_policy(path: Path) -> tuple[GeneratorPolicy, bool]:
    try:
        payload = load_yaml_mapping(path)
        return GeneratorPolicy.model_validate(payload), False
    except FileNotFoundError:
        return GeneratorPolicy.model_validate({
            "schema_version": "1.0",
            "statement_length": {},
            "date_generation": {},
            "amount_generation": {},
            "amount_modes": {},
            "currency_modes": {},
            "descript_modes": {},
            "field_inclusion": {},
            "account_number": {},
            "sort_code": {},
            "identifiers": {},
            "output": {},
            "analysis": {},
            "transaction_types": {
                "deposit": ["CR"],
                "withdrawal": ["DR"],
                "either": ["TR"],
            },
            "descriptions": {
                "deposit": ["Credit transaction"],
                "withdrawal": ["Debit transaction"],
                "either": ["Account transaction"],
            },
        }), True
    except (ValidationError, TypeError, yaml.YAMLError) as exc:
        raise ValueError(f"Invalid generator policy {path}:\n{exc}") from exc


def build_parser(policy: GeneratorPolicy) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Policy-driven seeded random CSV statement generator")
    parser.add_argument("-c", "--config", type=Path, default=Path("generator_policy.yaml"))
    parser.add_argument("-s", "--seed", type=int, default=policy.default_seed)
    parser.add_argument("-b", "--bank", type=str, default=None)
    parser.add_argument("-p", "--path", type=Path, default=policy.default_path)
    parser.add_argument("-d", "--diagnose", action="store_true")
    parser.add_argument("-a", "--analyse", action="store_true", help="Analyse the generated statement")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--version", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    bootstrap = argparse.ArgumentParser(add_help=False)
    bootstrap.add_argument("-c", "--config", type=Path, default=None)
    bootstrap_args, _ = bootstrap.parse_known_args(argv)

    repo_root = Path(__file__).resolve().parents[2]
    config_path = bootstrap_args.config
    if config_path is None:
        config_path = repo_root / "config" / "simple_generator_policy.yaml"
        if not config_path.exists():
            config_path = Path("generator_policy.yaml")
    elif not config_path.is_absolute():
        config_path = (Path.cwd() / config_path).resolve()

    try:
        policy, fallback_used = load_policy(config_path)
    except ValueError as exc:
        print(exc)
        return 2

    args = build_parser(policy).parse_args(argv)

    if args.version:
        print(f"Generator version\t{GENERATOR_VERSION}")
        print(f"Policy schema version\t{policy.schema_version}")
        return 0

    generator = StatementGenerator(args.seed, policy)
    try:
        statement, bank = generator.build_statement(args.bank)
        validate_statement(statement, policy)
    except (ValueError, KeyError, StatementValidationError) as exc:
        print(f"Generation error: {exc}")
        return 1

    if fallback_used:
        print(f"Policy not found at {bootstrap_args.config}; used built-in fallback policy.")

    if args.verbose or args.diagnose:
        print(f"Seed: {args.seed}")
        print(f"Bank: {bank}")
        print(f"Rows: {len(statement)}")
        print(f"Columns: {statement.columns.tolist()}")
        print(statement.head().to_string(index=False))

    if args.analyse:
        try:

            plot_dir = policy.analysis.plot_directory if policy.analysis.save_plots else None
            analyse_statement_df(
                statement,
                policy.model_dump(mode="python"),
                source_name=generator.output_filename(bank),
                plot_dir=plot_dir,
                show_plots=policy.analysis.show_plots,
            )
        except (ImportError, OSError, TypeError, ValueError, KeyError) as exc:
            print(f"Analysis error: {exc}")
            return 4

    if args.diagnose:
        print("Diagnosis passed; no file written.")
        return 0

    output_path = args.path / generator.output_filename(bank)
    overwrite = args.overwrite or not policy.output.prevent_overwrite
    try:
        dump_csv(output_path, statement, overwrite=overwrite)
    except OSError as exc:
        print(f"Output error: {exc}")
        return 3

    print(f"Saved to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())