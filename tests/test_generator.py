from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from nimo.generator import StatementGenerator
from nimo.generation.configurations import GeneratorPolicy


def test_build_descript_columns_returns_one_entry_per_amount() -> None:
    policy = GeneratorPolicy.model_validate(
        {
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
        }
    )
    generator = StatementGenerator(seed=1, policy=policy)

    result = generator.build_descript_columns([10.0, -5.0], mode="split")

    assert len(result["description"]) == 2
    assert len(result["transaction_type"]) == 2
