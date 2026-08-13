from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd


def dataframe_records(frame: pd.DataFrame, *, limit: int = 50) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    clean = frame.head(limit).copy()
    for column in clean.columns:
        if pd.api.types.is_datetime64_any_dtype(clean[column]):
            clean[column] = clean[column].astype(str)
    return clean.where(pd.notna(clean), None).to_dict(orient="records")


def build_evidence(
    *,
    user_name: str,
    period_start: date | None,
    period_end: date | None,
    overview: dict[str, Any],
    accounts: pd.DataFrame,
    categories: pd.DataFrame,
    monthly: pd.DataFrame,
    behaviour_map: dict[str, Any],
    forecast: dict[str, Any] | None,
    budget: dict[str, Any] | None,
    goals: list[dict[str, Any]],
    investment: dict[str, Any] | None,
    source_data_version: str,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "user": user_name,
        "period": {
            "start": None if period_start is None else period_start.isoformat(),
            "end": None if period_end is None else period_end.isoformat(),
        },
        "source_data_version": source_data_version,
        "historical_facts": {
            "overview": overview,
            "accounts": dataframe_records(accounts, limit=20),
            "categories": dataframe_records(categories.sort_values("spend", ascending=False) if not categories.empty and "spend" in categories else categories, limit=20),
            "monthly": dataframe_records(monthly, limit=36),
        },
        "inferred_behaviour": {
            "archetype": behaviour_map.get("archetype", {}),
            "global": behaviour_map.get("global", {}),
            "categories": dict(list(behaviour_map.get("categories", {}).items())[:20]),
        },
        "forecast": forecast,
        "budget": budget,
        "goals": goals,
        "investment": investment,
        "evidence_rules": [
            "Historical facts are computed from active canonical transactions.",
            "Inferred behaviour is probabilistic and can be wrong.",
            "Forecasts, goals and investments are simulations rather than promises.",
            "User overrides and planned events must be described as assumptions, not observations.",
        ],
    }
