from datetime import date
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from nimo.generator.behaviours import apply_inflation, choose_behaviour_for_date
from nimo.generator.configurations import GeneratorPolicy


def build_policy() -> GeneratorPolicy:
    return GeneratorPolicy.model_validate(
        {
            "schema_version": "1.0",
            "statement_length": {},
            "date_generation": {},
            "amount_generation": {"inflation_rate": 0.1},
            "amount_modes": {},
            "currency_modes": {},
            "descript_modes": {},
            "field_inclusion": {},
            "account_number": {},
            "sort_code": {},
            "identifiers": {},
            "output": {},
            "analysis": {},
            "behaviour_modes": {
                "periodic": {"enabled": True, "weekly_probability": 1.0, "monthly_probability": 1.0, "yearly_probability": 1.0},
                "spontaneous": {"enabled": True, "weekly_probability": 0.0, "monthly_probability": 0.0, "yearly_probability": 0.0},
                "distributional": {"enabled": True, "weekly_probability": 0.0, "monthly_probability": 0.0, "yearly_probability": 0.0},
            },
        }
    )


def test_choose_behaviour_for_date_prefers_periodic_when_configured() -> None:
    policy = build_policy()
    behavior = choose_behaviour_for_date(date(2024, 1, 2), random.Random(1), policy)

    assert behavior == "periodic"


def test_apply_inflation_compounds_yearly() -> None:
    policy = build_policy()
    inflated = apply_inflation(100.0, date(2024, 1, 1), policy)

    assert inflated > 100.0
