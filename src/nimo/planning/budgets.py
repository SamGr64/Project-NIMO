from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

ESSENTIAL_CATEGORIES = {"housing", "bills", "groceries", "transport", "health", "debt", "insurance"}


def infer_budget_lines(frame: pd.DataFrame, *, config: dict[str, Any]) -> list[dict[str, Any]]:
    defaults = config.get("defaults", {})
    lookback = int(defaults.get("lookback_months", 6))
    quantile = float(defaults.get("category_quantile", 0.60))
    rounding = max(1.0, float(defaults.get("round_to", 5)))
    reserve_fraction = float(defaults.get("irregular_expense_reserve_fraction", 0.05))
    if frame.empty:
        return []
    work = frame.loc[(frame["amount"] < 0) & frame["transfer_group_id"].isna()].copy()
    if work.empty:
        return []
    work["booking_date"] = pd.to_datetime(work["booking_date"])
    work["category_slug"] = work["category_slug"].fillna("uncategorised")
    work["category_label"] = work["category_label"].fillna(work["category_slug"].str.replace("_", " ").str.title())
    work["month"] = work["booking_date"].dt.to_period("M")
    latest_months = sorted(work["month"].unique())[-lookback:]
    work = work.loc[work["month"].isin(latest_months)]
    month_index = pd.PeriodIndex(latest_months, freq="M")
    lines: list[dict[str, Any]] = []
    for category, group in work.groupby("category_slug"):
        monthly = group.assign(spend=-group["amount"]).groupby("month")["spend"].sum().reindex(month_index, fill_value=0.0)
        raw = float(monthly.quantile(quantile))
        amount = float(np.ceil(raw / rounding) * rounding)
        label = str(group["category_label"].dropna().iloc[0]) if group["category_label"].notna().any() else str(category).title()
        lines.append(
            {
                "category_slug": str(category),
                "label": label,
                "amount": amount,
                "source": "inferred",
                "is_essential": str(category) in ESSENTIAL_CATEGORIES,
                "settings": {
                    "historical_mean": round(float(monthly.mean()), 6),
                    "historical_median": round(float(monthly.median()), 6),
                    "historical_std": round(float(monthly.std(ddof=1)) if len(monthly) > 1 else 0.0, 6),
                    "lookback_months": len(month_index),
                    "quantile": quantile,
                },
            }
        )
    irregular_base = sum(line["amount"] for line in lines if not line["is_essential"])
    if irregular_base > 0 and reserve_fraction > 0:
        lines.append(
            {
                "category_slug": "irregular_reserve",
                "label": "Irregular expense reserve",
                "amount": float(np.ceil(irregular_base * reserve_fraction / rounding) * rounding),
                "source": "default",
                "is_essential": True,
                "settings": {"reserve_fraction": reserve_fraction},
            }
        )
    return sorted(lines, key=lambda item: (not item["is_essential"], item["label"]))
