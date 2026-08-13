from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import numpy as np
import pandas as pd


@dataclass(slots=True)
class ForecastSimulation:
    months: list[str]
    balances: np.ndarray
    income: np.ndarray
    spending: np.ndarray
    net_cashflow: np.ndarray
    category_spending: dict[str, np.ndarray]
    resolved_profile: dict[str, Any]
    events: list[dict[str, Any]]


def simulate_forecast(
    profile: dict[str, Any],
    *,
    events: list[dict[str, Any]] | None = None,
    horizon_months: int,
    runs: int,
    seed: int,
) -> ForecastSimulation:
    if horizon_months <= 0 or runs <= 0:
        raise ValueError("Forecast horizon and run count must be positive")
    rng = np.random.default_rng(seed)
    as_of = pd.Timestamp(profile.get("as_of_date") or date.today())
    periods = pd.period_range(as_of.to_period("M") + 1, periods=horizon_months, freq="M")
    months = [str(period) for period in periods]
    inflation = float(profile.get("global_assumptions", {}).get("annual_inflation_rate", 0.0))
    monthly_inflation = (1.0 + inflation) ** (1.0 / 12.0) - 1.0

    income = np.zeros((runs, horizon_months), dtype=float)
    spending = np.zeros((runs, horizon_months), dtype=float)
    category_spending: dict[str, np.ndarray] = {}
    income_process = profile.get("income", {})
    for month_index in range(horizon_months):
        income[:, month_index] = _sample_process(income_process, month_index, rng, runs, inflation_rate=0.0)

    for category, process in profile.get("categories", {}).items():
        samples = np.zeros((runs, horizon_months), dtype=float)
        for month_index in range(horizon_months):
            samples[:, month_index] = _sample_process(
                process,
                month_index,
                rng,
                runs,
                inflation_rate=monthly_inflation,
            )
        category_spending[str(category)] = samples
        spending += samples

    event_list = list(events or [])
    event_cashflow = np.zeros((runs, horizon_months), dtype=float)
    period_lookup = {period: index for index, period in enumerate(periods)}
    for event in event_list:
        event_period = pd.Timestamp(event["date"]).to_period("M")
        repeat_months = int(event.get("repeat_months", 0) or 0)
        occurrence_probability = float(event.get("probability", 1.0))
        amount = float(event.get("amount", 0.0))
        uncertainty = max(0.0, float(event.get("uncertainty", 0.0)))
        current = event_period
        while current in period_lookup:
            index = period_lookup[current]
            occurs = rng.random(runs) <= occurrence_probability
            sampled = rng.normal(amount, uncertainty, runs) if uncertainty > 0 else np.full(runs, amount)
            event_cashflow[:, index] += np.where(occurs, sampled, 0.0)
            if repeat_months <= 0:
                break
            current += repeat_months
    net = income - spending + event_cashflow
    initial_balance = float(profile.get("initial_balance", 0.0))
    balances = initial_balance + np.cumsum(net, axis=1)
    return ForecastSimulation(
        months=months,
        balances=balances,
        income=income,
        spending=spending,
        net_cashflow=net,
        category_spending=category_spending,
        resolved_profile=profile,
        events=event_list,
    )


def summarise_forecast(simulation: ForecastSimulation, *, threshold: float | None = None) -> dict[str, Any]:
    monthly: list[dict[str, Any]] = []
    for index, month in enumerate(simulation.months):
        balance = simulation.balances[:, index]
        income = simulation.income[:, index]
        spending = simulation.spending[:, index]
        net = simulation.net_cashflow[:, index]
        monthly.append(
            {
                "month": month,
                **_quantiles(balance, prefix="balance"),
                **_quantiles(income, prefix="income"),
                **_quantiles(spending, prefix="spend"),
                **_quantiles(net, prefix="net"),
            }
        )
    final = simulation.balances[:, -1]
    summary: dict[str, Any] = {
        "months": monthly,
        "horizon_months": len(simulation.months),
        "simulation_runs": int(simulation.balances.shape[0]),
        "final_balance": _quantiles(final, prefix=""),
        "expected_total_income": round(float(simulation.income.sum(axis=1).mean()), 6),
        "expected_total_spend": round(float(simulation.spending.sum(axis=1).mean()), 6),
        "expected_net_cashflow": round(float(simulation.net_cashflow.sum(axis=1).mean()), 6),
        "probability_negative_balance": round(float(np.mean(np.min(simulation.balances, axis=1) < 0)), 6),
        "category_totals": {
            category: _quantiles(values.sum(axis=1), prefix="")
            for category, values in simulation.category_spending.items()
        },
    }
    if threshold is not None:
        summary["threshold"] = float(threshold)
        summary["probability_below_threshold"] = round(float(np.mean(final < threshold)), 6)
    return summary


def _sample_process(
    process: dict[str, Any],
    month_index: int,
    rng: np.random.Generator,
    runs: int,
    *,
    inflation_rate: float,
) -> np.ndarray:
    mean = max(0.0, float(process.get("monthly_mean", 0.0)))
    std = max(0.0, float(process.get("monthly_std", 0.0)))
    trend = float(process.get("monthly_trend", 0.0))
    zero_probability = min(1.0, max(0.0, float(process.get("zero_probability", 0.0))))
    expected = mean * ((1.0 + trend) ** month_index) * ((1.0 + inflation_rate) ** month_index)
    scale_ratio = std / mean if mean > 1e-9 else 0.0
    std_expected = max(0.0, expected * scale_ratio)
    if expected <= 0:
        samples = np.zeros(runs, dtype=float)
    elif std_expected <= 1e-9:
        samples = np.full(runs, expected, dtype=float)
    else:
        variance = std_expected**2
        sigma2 = np.log1p(variance / max(expected**2, 1e-12))
        sigma = np.sqrt(max(0.0, sigma2))
        mu = np.log(max(expected, 1e-12)) - sigma2 / 2.0
        samples = rng.lognormal(mu, sigma, runs)
    if zero_probability > 0:
        samples = np.where(rng.random(runs) < zero_probability, 0.0, samples / max(1e-9, 1.0 - zero_probability))
    return np.maximum(0.0, samples)


def _quantiles(values: np.ndarray, *, prefix: str) -> dict[str, float]:
    labels = {"p05": 0.05, "p10": 0.10, "p25": 0.25, "median": 0.50, "p75": 0.75, "p90": 0.90, "p95": 0.95}
    result = {label: round(float(np.quantile(values, quantile)), 6) for label, quantile in labels.items()}
    result["mean"] = round(float(np.mean(values)), 6)
    if prefix:
        return {f"{prefix}_{key}": value for key, value in result.items()}
    return result
