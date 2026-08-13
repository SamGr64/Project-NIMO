from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from nimo.forecasting.monte_carlo import ForecastSimulation


def simulate_goal(
    simulation: ForecastSimulation,
    *,
    current_amount: float,
    target_amount: float,
    monthly_contribution: float,
    surplus_allocation_fraction: float,
) -> dict[str, Any]:
    surplus = np.maximum(0.0, simulation.net_cashflow)
    contributions = max(0.0, float(monthly_contribution)) + surplus * min(1.0, max(0.0, float(surplus_allocation_fraction)))
    paths = float(current_amount) + np.cumsum(contributions, axis=1)
    achieved = paths >= float(target_amount)
    achieved_by_end = achieved[:, -1]
    first_index = np.full(paths.shape[0], -1, dtype=int)
    any_achieved = achieved.any(axis=1)
    first_index[any_achieved] = achieved[any_achieved].argmax(axis=1)
    completion_months = [simulation.months[index] for index in first_index if index >= 0]
    final = paths[:, -1]
    return {
        "probability_achieved": round(float(np.mean(achieved_by_end)), 6),
        "expected_final_amount": round(float(np.mean(final)), 6),
        "median_final_amount": round(float(np.median(final)), 6),
        "p10_final_amount": round(float(np.quantile(final, 0.10)), 6),
        "p90_final_amount": round(float(np.quantile(final, 0.90)), 6),
        "most_likely_completion_month": _mode(completion_months),
        "completion_month_p10": _completion_quantile(completion_months, 0.10),
        "completion_month_median": _completion_quantile(completion_months, 0.50),
        "completion_month_p90": _completion_quantile(completion_months, 0.90),
        "expected_total_contribution": round(float(contributions.sum(axis=1).mean()), 6),
    }


def months_until(as_of_date: str, target_date: str) -> int:
    start = pd.Timestamp(as_of_date).to_period("M")
    target = pd.Timestamp(target_date).to_period("M")
    return max(1, int(target.ordinal - start.ordinal))


def _mode(values: list[str]) -> str | None:
    if not values:
        return None
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return max(counts, key=counts.get)


def _completion_quantile(values: list[str], quantile: float) -> str | None:
    if not values:
        return None
    ordinals = np.asarray([pd.Period(value, freq="M").ordinal for value in values], dtype=float)
    return str(pd.Period(ordinal=int(round(float(np.quantile(ordinals, quantile)))), freq="M"))
