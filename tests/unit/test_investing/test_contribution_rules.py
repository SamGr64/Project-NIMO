from __future__ import annotations

import numpy as np

from nimo.forecasting.monte_carlo import ForecastSimulation
from nimo.investing.simulator import contribution_schedule


def _cashflow() -> ForecastSimulation:
    balances = np.asarray([[6000.0, 6200.0, 6400.0], [5200.0, 5250.0, 5300.0]])
    return ForecastSimulation(
        months=["2027-01", "2027-02", "2027-03"],
        balances=balances,
        income=np.zeros_like(balances),
        spending=np.zeros_like(balances),
        net_cashflow=np.zeros_like(balances),
        category_spending={},
        resolved_profile={"initial_balance": 5000.0},
        events=[],
    )


def test_threshold_rule_does_not_reinvest_the_same_cash() -> None:
    schedule = contribution_schedule(
        _cashflow(),
        {"type": "threshold", "cash_threshold": 5000.0, "fraction": 1.0},
    )
    assert np.allclose(schedule[0], [1000.0, 200.0, 200.0])
    assert np.allclose(schedule[1], [200.0, 50.0, 50.0])


def test_goal_aware_rule_preserves_minimum_cash() -> None:
    schedule = contribution_schedule(
        _cashflow(),
        {"type": "goal_aware", "amount": 500.0, "minimum_cash": 5000.0},
    )
    assert np.allclose(schedule[0], [500.0, 500.0, 0.0])
    assert np.allclose(schedule[1], [0.0, 0.0, 0.0])
