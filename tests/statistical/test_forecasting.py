from __future__ import annotations

import numpy as np

from nimo.forecasting.monte_carlo import simulate_forecast, summarise_forecast


PROFILE = {
    "as_of_date": "2026-07-31",
    "initial_balance": 2500.0,
    "income": {"monthly_mean": 3000.0, "monthly_std": 100.0, "zero_probability": 0.0, "monthly_trend": 0.0},
    "categories": {
        "housing": {"monthly_mean": 1200.0, "monthly_std": 0.0, "zero_probability": 0.0, "monthly_trend": 0.0},
        "groceries": {"monthly_mean": 350.0, "monthly_std": 50.0, "zero_probability": 0.0, "monthly_trend": 0.0},
    },
    "global_assumptions": {"annual_inflation_rate": 0.03},
}


def test_forecast_seed_is_reproducible_and_intervals_are_ordered() -> None:
    first = simulate_forecast(PROFILE, horizon_months=12, runs=500, seed=81)
    second = simulate_forecast(PROFILE, horizon_months=12, runs=500, seed=81)
    assert np.array_equal(first.balances, second.balances)
    summary = summarise_forecast(first)
    final = summary["final_balance"]
    assert final["p10"] <= final["median"] <= final["p90"]
    assert summary["probability_negative_balance"] == 0.0
