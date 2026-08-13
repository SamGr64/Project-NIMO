from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from nimo.forecasting.monte_carlo import simulate_forecast
from nimo.forecasting.profile_builder import build_default_forecast_profile


def rolling_backtest(
    frame: pd.DataFrame,
    *,
    opening_balance: float,
    config: dict[str, Any],
    holdout_months: int = 3,
    runs: int = 1000,
    seed: int = 99173,
) -> dict[str, Any]:
    if frame.empty:
        return {"status": "no_data", "periods": []}
    work = frame.copy()
    work["booking_date"] = pd.to_datetime(work["booking_date"])
    periods = sorted(work["booking_date"].dt.to_period("M").unique())
    minimum_training = int(config.get("backtesting", {}).get("minimum_training_months", 6))
    if len(periods) < minimum_training + 1:
        return {"status": "insufficient_history", "periods": [], "history_months": len(periods)}
    selected = periods[-min(holdout_months, len(periods) - minimum_training):]
    results: list[dict[str, Any]] = []
    for index, period in enumerate(selected):
        training = work.loc[work["booking_date"].dt.to_period("M") < period].copy()
        actual = work.loc[work["booking_date"].dt.to_period("M") == period].copy()
        profile = build_default_forecast_profile(training, {}, opening_balance=opening_balance, config=config)
        simulation = simulate_forecast(profile, horizon_months=1, runs=runs, seed=seed + index)
        predicted = simulation.net_cashflow[:, 0]
        actual_external = actual.loc[actual["transfer_group_id"].isna()]
        actual_net = float(actual_external["amount"].sum())
        p25, p75 = np.quantile(predicted, [0.25, 0.75])
        p05, p95 = np.quantile(predicted, [0.05, 0.95])
        results.append(
            {
                "month": str(period),
                "actual_net": round(actual_net, 6),
                "predicted_median": round(float(np.median(predicted)), 6),
                "p25": round(float(p25), 6),
                "p75": round(float(p75), 6),
                "p05": round(float(p05), 6),
                "p95": round(float(p95), 6),
                "inside_50": bool(p25 <= actual_net <= p75),
                "inside_90": bool(p05 <= actual_net <= p95),
                "absolute_error": round(abs(actual_net - float(np.median(predicted))), 6),
            }
        )
    return {
        "status": "complete",
        "periods": results,
        "coverage_50": round(float(np.mean([row["inside_50"] for row in results])), 6),
        "coverage_90": round(float(np.mean([row["inside_90"] for row in results])), 6),
        "median_absolute_error": round(float(np.median([row["absolute_error"] for row in results])), 6),
        "note": "Coverage is diagnostic rather than a guarantee; short histories can make calibration unstable.",
    }
