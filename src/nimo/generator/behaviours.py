from __future__ import annotations

import math
import random
from datetime import date, datetime
from typing import Any, Mapping

from nimo.utils import normalise_text_aggressive


Behaviour = str


def _behaviour_config(policy: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    behaviour_modes = policy.get("behaviour_modes", {})
    if not isinstance(behaviour_modes, Mapping):
        return {}
    config = behaviour_modes.get(name, {})
    return config if isinstance(config, Mapping) else {}


def _probability_for_scale(config: Mapping[str, Any], scale: str) -> float:
    key = {
        "weekly": "weekly_probability",
        "monthly": "monthly_probability",
        "yearly": "yearly_probability",
    }.get(scale, "monthly_probability")
    value = config.get(key, 0.0)
    return float(value)


def choose_behaviour_for_date(target_date: date, rng: random.Random, policy: Mapping[str, Any]) -> Behaviour:
    """Choose one of the three behavioural modes for a transaction date."""
    scale = _scale_for_date(target_date)
    candidates: list[tuple[Behaviour, float]] = []
    for name in ("periodic", "spontaneous", "distributional"):
        cfg = _behaviour_config(policy, name)
        if not cfg.get("enabled", True):
            continue
        probability = _probability_for_scale(cfg, scale)
        if probability > 0:
            candidates.append((name, probability))

    if not candidates:
        return "distributional"

    total = sum(weight for _, weight in candidates)
    threshold = rng.random() * total
    running = 0.0
    for name, weight in candidates:
        running += weight
        if running >= threshold:
            return name
    return candidates[-1][0]


def _scale_for_date(target_date: date) -> str:
    day = target_date.day
    month = target_date.month
    if day in {1, 15} or month in {1, 7}:
        return "monthly"
    if month == 1 and day == 1:
        return "yearly"
    return "weekly"


def apply_inflation(amount: float, target_date: date, policy: Mapping[str, Any]) -> float:
    """Apply a simple compounded annual inflation factor to an amount."""
    inflation_rate = float(policy.get("amount_generation", {}).get("inflation_rate", 0.0))
    if inflation_rate <= 0:
        return float(amount)
    year_delta = max(0, target_date.year - 2020)
    return float(amount) * math.pow(1.0 + inflation_rate, year_delta)


def build_behavioural_amount(base_amount: float, target_date: date, rng: random.Random, policy: Mapping[str, Any]) -> float:
    """Create a signed amount that reflects the selected behavioural mode."""
    behaviour = choose_behaviour_for_date(target_date, rng, policy)
    amount = base_amount
    if behaviour == "spontaneous":
        amount *= 1.5 + rng.random() * 2.0
    elif behaviour == "distributional":
        amount *= 0.8 + rng.random() * 0.4
    amount = apply_inflation(amount, target_date, policy)
    if rng.random() < 0.5:
        amount = -abs(amount)
    else:
        amount = abs(amount)
    return round(amount, 2)
