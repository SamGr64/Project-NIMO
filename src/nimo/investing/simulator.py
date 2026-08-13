from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from nimo.forecasting.monte_carlo import ForecastSimulation


@dataclass(slots=True)
class InvestmentSimulation:
    months: list[str]
    portfolio_values: np.ndarray
    contributions: np.ndarray
    adjusted_cash_balances: np.ndarray
    portfolio_returns: np.ndarray


def simulate_portfolio(
    *,
    history: pd.DataFrame,
    allocations: dict[str, float],
    cashflow: ForecastSimulation,
    contribution_rule: dict[str, Any],
    annual_fee_rate: float,
    seed: int,
    stress: dict[str, Any] | None = None,
) -> InvestmentSimulation:
    weights = _normalise_weights(allocations)
    symbols = list(weights)
    pivot = history.loc[history["symbol"].isin(symbols)].pivot_table(index="date", columns="symbol", values="monthly_return", aggfunc="last").dropna()
    if pivot.empty or any(symbol not in pivot.columns for symbol in symbols):
        raise ValueError("Insufficient joint history for selected portfolio")
    rng = np.random.default_rng(seed)
    runs, horizon = cashflow.balances.shape
    row_indices = rng.integers(0, len(pivot), size=(runs, horizon))
    joint = pivot[symbols].to_numpy(dtype=float)
    sampled = joint[row_indices]
    weight_vector = np.asarray([weights[symbol] for symbol in symbols], dtype=float)
    returns = np.einsum("rha,a->rh", sampled, weight_vector)
    returns -= float(annual_fee_rate) / 12.0
    stress = stress or {}
    if horizon and "first_month_return_shock" in stress:
        returns[:, 0] += float(stress["first_month_return_shock"])

    contributions = contribution_schedule(cashflow, contribution_rule)
    adjusted_cash = cashflow.balances - np.cumsum(contributions, axis=1)
    if horizon and "one_off_cashflow" in stress:
        adjusted_cash[:, 0:] += float(stress["one_off_cashflow"])
    values = np.zeros((runs, horizon), dtype=float)
    initial = max(0.0, float(contribution_rule.get("initial_amount", 0.0)))
    previous = np.full(runs, initial)
    for index in range(horizon):
        previous = previous * (1.0 + returns[:, index]) + contributions[:, index]
        values[:, index] = np.maximum(0.0, previous)
    return InvestmentSimulation(
        months=cashflow.months,
        portfolio_values=values,
        contributions=contributions,
        adjusted_cash_balances=adjusted_cash,
        portfolio_returns=returns,
    )


def contribution_schedule(cashflow: ForecastSimulation, rule: dict[str, Any]) -> np.ndarray:
    rule_type = str(rule.get("type", "fixed"))
    if rule_type == "fixed":
        return np.full_like(cashflow.net_cashflow, max(0.0, float(rule.get("amount", 0.0))))
    if rule_type == "percent_income":
        return np.maximum(0.0, cashflow.income * max(0.0, min(1.0, float(rule.get("fraction", 0.0)))))
    if rule_type == "percent_surplus":
        return np.maximum(0.0, cashflow.net_cashflow) * max(0.0, min(1.0, float(rule.get("fraction", 0.0))))
    if rule_type == "threshold":
        threshold = float(rule.get("cash_threshold", 0.0))
        fraction = max(0.0, min(1.0, float(rule.get("fraction", 1.0))))
        return _sequential_threshold_schedule(cashflow, threshold=threshold, fraction=fraction)
    if rule_type == "goal_aware":
        fixed = max(0.0, float(rule.get("amount", 0.0)))
        minimum_cash = float(rule.get("minimum_cash", 0.0))
        return _sequential_goal_aware_schedule(cashflow, amount=fixed, minimum_cash=minimum_cash)
    raise ValueError(f"Unknown contribution rule: {rule_type}")


def summarise_investment(simulation: InvestmentSimulation) -> dict[str, Any]:
    final = simulation.portfolio_values[:, -1]
    contributed = simulation.contributions.sum(axis=1)
    return {
        "months": [
            {
                "month": month,
                "portfolio_median": round(float(np.median(simulation.portfolio_values[:, index])), 6),
                "portfolio_p10": round(float(np.quantile(simulation.portfolio_values[:, index], 0.10)), 6),
                "portfolio_p90": round(float(np.quantile(simulation.portfolio_values[:, index], 0.90)), 6),
                "cash_median": round(float(np.median(simulation.adjusted_cash_balances[:, index])), 6),
            }
            for index, month in enumerate(simulation.months)
        ],
        "final_value": _quantiles(final),
        "total_contributed": _quantiles(contributed),
        "median_growth_over_contributions": round(float(np.median(final - contributed)), 6),
        "probability_loss_vs_contributions": round(float(np.mean(final < contributed)), 6),
        "probability_negative_cash": round(float(np.mean(np.min(simulation.adjusted_cash_balances, axis=1) < 0)), 6),
        "maximum_simulated_drawdown_median": round(float(np.median(_path_drawdown(simulation.portfolio_values))), 6),
    }


def _normalise_weights(allocations: dict[str, float]) -> dict[str, float]:
    clean = {symbol.upper(): max(0.0, float(weight)) for symbol, weight in allocations.items() if float(weight) > 0}
    total = sum(clean.values())
    if total <= 0:
        raise ValueError("Portfolio must contain at least one positive allocation")
    return {symbol: weight / total for symbol, weight in clean.items()}


def _sequential_threshold_schedule(
    cashflow: ForecastSimulation,
    *,
    threshold: float,
    fraction: float,
) -> np.ndarray:
    """Invest cash above a threshold without repeatedly allocating the same cash."""

    schedule = np.zeros_like(cashflow.net_cashflow)
    cumulative = np.zeros(cashflow.balances.shape[0], dtype=float)
    for month in range(cashflow.balances.shape[1]):
        available = cashflow.balances[:, month] - cumulative
        contribution = np.maximum(0.0, available - threshold) * fraction
        schedule[:, month] = contribution
        cumulative += contribution
    return schedule


def _sequential_goal_aware_schedule(
    cashflow: ForecastSimulation,
    *,
    amount: float,
    minimum_cash: float,
) -> np.ndarray:
    """Apply a fixed contribution only when it preserves the selected cash floor."""

    schedule = np.zeros_like(cashflow.net_cashflow)
    cumulative = np.zeros(cashflow.balances.shape[0], dtype=float)
    for month in range(cashflow.balances.shape[1]):
        available = cashflow.balances[:, month] - cumulative
        contribution = np.where(available - amount >= minimum_cash, amount, 0.0)
        schedule[:, month] = contribution
        cumulative += contribution
    return schedule


def _quantiles(values: np.ndarray) -> dict[str, float]:
    return {
        "mean": round(float(np.mean(values)), 6),
        "median": round(float(np.median(values)), 6),
        "p10": round(float(np.quantile(values, 0.10)), 6),
        "p90": round(float(np.quantile(values, 0.90)), 6),
    }


def _path_drawdown(values: np.ndarray) -> np.ndarray:
    padded = np.maximum(values, 1e-9)
    peaks = np.maximum.accumulate(padded, axis=1)
    return np.min(padded / peaks - 1.0, axis=1)
