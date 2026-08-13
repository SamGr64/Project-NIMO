from __future__ import annotations

from calendar import monthrange
from typing import Any

import numpy as np
import pandas as pd


def build_default_forecast_profile(
    frame: pd.DataFrame,
    behaviour_map: dict[str, Any],
    *,
    opening_balance: float,
    config: dict[str, Any],
) -> dict[str, Any]:
    defaults = config.get("defaults", {})
    if frame.empty:
        return {
            "schema_version": 1,
            "as_of_date": None,
            "initial_balance": float(opening_balance),
            "history_months": 0,
            "income": _empty_process("income.monthly"),
            "categories": {},
            "global_assumptions": {
                "annual_inflation_rate": float(defaults.get("annual_inflation_rate", 0.025)),
            },
        }
    working = frame.copy()
    working["booking_date"] = pd.to_datetime(working["booking_date"])
    working["category_slug"] = working["category_slug"].fillna("uncategorised")
    external = working.loc[working["transfer_group_id"].isna()].copy()
    as_of = working["booking_date"].max()
    last_period = as_of.to_period("M")
    if as_of.day < monthrange(as_of.year, as_of.month)[1]:
        modelling = external.loc[external["booking_date"].dt.to_period("M") < last_period].copy()
    else:
        modelling = external.copy()
    if modelling.empty:
        modelling = external.copy()
    first_period = modelling["booking_date"].min().to_period("M")
    final_period = modelling["booking_date"].max().to_period("M")
    month_index = pd.period_range(first_period, final_period, freq="M")

    credits = modelling.loc[modelling["amount"] > 0].copy()
    income_monthly = credits.assign(month=credits["booking_date"].dt.to_period("M")).groupby("month")["amount"].sum().reindex(month_index, fill_value=0.0)
    income = _process_from_monthly(
        income_monthly,
        source="inferred",
        provenance="active external credits aggregated by calendar month",
        trend_cap=float(defaults.get("monthly_trend_cap", 0.03)),
    )
    income["assumption_id"] = "income.monthly"

    categories: dict[str, Any] = {}
    debits = modelling.loc[modelling["amount"] < 0].copy()
    category_behaviours = behaviour_map.get("categories", {})
    for category, group in debits.groupby("category_slug"):
        monthly = group.assign(month=group["booking_date"].dt.to_period("M"), spend=-group["amount"]).groupby("month")["spend"].sum().reindex(month_index, fill_value=0.0)
        process = _process_from_monthly(
            monthly,
            source="inferred",
            provenance=f"external debits categorised as {category}",
            trend_cap=float(defaults.get("monthly_trend_cap", 0.03)),
        )
        process["assumption_id"] = f"category.{category}.monthly"
        behaviour = category_behaviours.get(str(category), {})
        process["periodic_score"] = float(behaviour.get("periodic", {}).get("score", 0.0))
        process["distribution_fit"] = behaviour.get("distributional", {}).get("best_fit")
        process["spontaneous_rate"] = float(behaviour.get("spontaneous", {}).get("rate", 0.0))
        process["label"] = str(category).replace("_", " ").title()
        categories[str(category)] = process

    history_months = int(len(month_index))
    return {
        "schema_version": 1,
        "as_of_date": str(as_of.date()),
        "initial_balance": round(float(opening_balance), 6),
        "history_months": history_months,
        "income": income,
        "categories": categories,
        "global_assumptions": {
            "annual_inflation_rate": float(defaults.get("annual_inflation_rate", 0.025)),
            "source": "default",
            "provenance": "config/forecasting.yaml",
        },
        "notes": [
            "The default forecast assumes inferred historical processes continue.",
            "User scenario overrides do not alter the behavioural map or transaction history.",
        ],
    }


def _process_from_monthly(
    series: pd.Series,
    *,
    source: str,
    provenance: str,
    trend_cap: float,
) -> dict[str, Any]:
    values = series.to_numpy(dtype=float)
    positive = values[values > 0]
    mean = float(np.mean(values)) if len(values) else 0.0
    std = float(np.std(values, ddof=1)) if len(values) > 1 else 0.0
    median = float(np.median(values)) if len(values) else 0.0
    zero_probability = float(np.mean(values <= 0)) if len(values) else 1.0
    trend = 0.0
    if len(values) >= 4 and mean > 0:
        slope = float(np.polyfit(np.arange(len(values), dtype=float), values, 1)[0])
        trend = float(np.clip(slope / mean, -trend_cap, trend_cap))
    return {
        "monthly_mean": round(mean, 6),
        "monthly_std": round(std, 6),
        "monthly_median": round(median, 6),
        "zero_probability": round(zero_probability, 6),
        "monthly_trend": round(trend, 8),
        "sample_months": int(len(values)),
        "nonzero_months": int(len(positive)),
        "source": source,
        "provenance": provenance,
        "confidence": round(min(1.0, len(values) / 12.0) * (1.0 - min(0.7, zero_probability * 0.4)), 6),
    }


def _empty_process(assumption_id: str) -> dict[str, Any]:
    return {
        "assumption_id": assumption_id,
        "monthly_mean": 0.0,
        "monthly_std": 0.0,
        "monthly_median": 0.0,
        "zero_probability": 1.0,
        "monthly_trend": 0.0,
        "sample_months": 0,
        "nonzero_months": 0,
        "source": "inferred",
        "provenance": "no usable history",
        "confidence": 0.0,
    }
