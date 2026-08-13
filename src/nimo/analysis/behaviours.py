from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from nimo.analysis.archetypes import infer_archetype
from nimo.analysis.distributions import fit_amount_distributions
from nimo.analysis.outliers import score_outliers
from nimo.analysis.periodicity import detect_periodicity


def build_behavioural_map(
    frame: pd.DataFrame,
    *,
    overview: dict[str, Any],
    config: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], pd.DataFrame]:
    if frame.empty:
        empty = {
            "schema_version": 1,
            "metadata": {"transaction_count": 0, "history_months": 0},
            "global": {},
            "accounts": {},
            "categories": {},
            "merchants": {},
        }
        empty["archetype"] = infer_archetype(overview=overview, behaviour_map=empty)
        return empty, [], pd.DataFrame()

    behaviour_cfg = config.get("behaviour", {})
    minimum_obs = int(behaviour_cfg.get("minimum_observations", 6))
    minimum_distribution = int(behaviour_cfg.get("minimum_distribution_observations", 12))
    candidates = list(behaviour_cfg.get("candidate_distributions", [])) or None
    outlier_cfg = behaviour_cfg.get("outliers", {})
    merchant_min = int(behaviour_cfg.get("merchant_minimum_observations", 5))

    working = frame.copy()
    working["booking_date"] = pd.to_datetime(working["booking_date"])
    working["category_slug"] = working["category_slug"].fillna("uncategorised")
    working["merchant_normalised"] = working["merchant_normalised"].fillna(working["description_raw"]).astype(str)
    external = working.loc[working["transfer_group_id"].isna()].copy()
    outliers = score_outliers(
        external,
        iqr_multiplier=float(outlier_cfg.get("iqr_multiplier", 1.5)),
        robust_z_threshold=float(outlier_cfg.get("robust_z_threshold", 3.5)),
    )

    patterns: list[dict[str, Any]] = []
    category_payload: dict[str, Any] = {}
    debit_frame = external.loc[external["amount"] < 0].copy()
    for category, group in debit_frame.groupby("category_slug"):
        if len(group) < minimum_obs:
            continue
        payload = _scope_payload(
            group,
            outliers.loc[outliers["scope_key"] == str(category)],
            minimum_distribution=minimum_distribution,
            candidates=candidates,
        )
        category_payload[str(category)] = payload
        patterns.append(_pattern_row("category", str(category), group, payload))

    account_payload: dict[str, Any] = {}
    for account_name, group in debit_frame.groupby("account_name"):
        if len(group) < minimum_obs:
            continue
        payload = _scope_payload(group, pd.DataFrame(), minimum_distribution=minimum_distribution, candidates=candidates)
        account_payload[str(account_name)] = payload
        patterns.append(_pattern_row("account", str(account_name), group, payload))

    merchant_payload: dict[str, Any] = {}
    merchant_groups = sorted(debit_frame.groupby("merchant_normalised"), key=lambda item: len(item[1]), reverse=True)
    for merchant, group in merchant_groups[:50]:
        if len(group) < merchant_min:
            continue
        merchant_outliers = outliers.loc[outliers["transaction_id"].isin(group["id"])]
        payload = _scope_payload(group, merchant_outliers, minimum_distribution=minimum_distribution, candidates=candidates)
        merchant_payload[str(merchant)] = payload
        patterns.append(_pattern_row("merchant", str(merchant), group, payload))

    dates = working["booking_date"]
    history_months = len(pd.period_range(dates.min(), dates.max(), freq="M"))
    credits = external.loc[external["amount"] > 0].copy()
    income_monthly = credits.assign(month=credits["booking_date"].dt.to_period("M")).groupby("month")["amount"].sum()
    income_mean = float(income_monthly.mean()) if not income_monthly.empty else 0.0
    income_std = float(income_monthly.std(ddof=1)) if len(income_monthly) > 1 else 0.0
    weekend_spend = debit_frame.loc[debit_frame["booking_date"].dt.weekday >= 5, "amount"].abs().sum()
    total_spend = debit_frame["amount"].abs().sum()
    spontaneous_count = int(outliers["is_outlier"].sum()) if not outliers.empty else 0
    map_payload: dict[str, Any] = {
        "schema_version": 1,
        "metadata": {
            "transaction_count": int(len(working)),
            "external_transaction_count": int(len(external)),
            "history_months": int(history_months),
            "date_start": str(dates.min().date()),
            "date_end": str(dates.max().date()),
        },
        "global": {
            "income": {
                "monthly_mean": round(income_mean, 6),
                "monthly_std": round(income_std, 6),
                "monthly_cv": round(income_std / income_mean, 6) if income_mean > 0 else 0.0,
                "periodicity": detect_periodicity(credits),
            },
            "weekend_spend_share": round(float(weekend_spend / total_spend), 6) if total_spend > 0 else 0.0,
            "spontaneous_transaction_rate": round(spontaneous_count / max(1, len(debit_frame)), 6),
            "category_count": len(category_payload),
            "merchant_count": len(merchant_payload),
        },
        "accounts": account_payload,
        "categories": category_payload,
        "merchants": merchant_payload,
    }
    map_payload["archetype"] = infer_archetype(overview=overview, behaviour_map=map_payload)
    return map_payload, patterns, outliers


def _scope_payload(
    group: pd.DataFrame,
    outliers: pd.DataFrame,
    *,
    minimum_distribution: int,
    candidates: list[str] | None,
) -> dict[str, Any]:
    amounts = group["amount"].abs().to_numpy(dtype=float)
    periodicity = detect_periodicity(group)
    distribution = fit_amount_distributions(amounts, candidates=candidates, minimum_observations=minimum_distribution)
    if outliers.empty:
        spontaneous_count = 0
        top_outliers: list[dict[str, Any]] = []
    else:
        flagged = outliers.loc[outliers["is_outlier"]].sort_values("surprise_score", ascending=False)
        spontaneous_count = int(len(flagged))
        top_outliers = flagged.head(5)[["transaction_id", "amount_magnitude", "robust_z", "surprise_score"]].to_dict(orient="records")
    spontaneous_score = min(1.0, spontaneous_count / max(1.0, len(group) * 0.08))
    dates = pd.to_datetime(group["booking_date"])
    monthly = group.assign(month=dates.dt.to_period("M"), spend=group["amount"].abs()).groupby("month")["spend"].sum()
    weekly = group.assign(week=dates.dt.to_period("W-MON"), spend=group["amount"].abs()).groupby("week")["spend"].sum()
    yearly = group.assign(year=dates.dt.year, spend=group["amount"].abs()).groupby("year")["spend"].sum()
    return {
        "sample_count": int(len(group)),
        "total_amount": round(float(np.sum(amounts)), 6),
        "typical_amount": round(float(np.median(amounts)), 6),
        "periodic": periodicity,
        "distributional": distribution,
        "spontaneous": {
            "score": round(float(spontaneous_score), 6),
            "count": spontaneous_count,
            "rate": round(spontaneous_count / max(1, len(group)), 6),
            "top_outliers": top_outliers,
        },
        "timescales": {
            "weekly": _series_summary(weekly),
            "monthly": _series_summary(monthly),
            "yearly": _series_summary(yearly),
        },
    }


def _series_summary(series: pd.Series) -> dict[str, Any]:
    if series.empty:
        return {"periods": 0, "mean": 0.0, "median": 0.0, "std": 0.0}
    return {
        "periods": int(len(series)),
        "mean": round(float(series.mean()), 6),
        "median": round(float(series.median()), 6),
        "std": round(float(series.std(ddof=1)) if len(series) > 1 else 0.0, 6),
        "minimum": round(float(series.min()), 6),
        "maximum": round(float(series.max()), 6),
    }


def _pattern_row(scope_type: str, scope_key: str, group: pd.DataFrame, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "scope_type": scope_type,
        "scope_key": scope_key,
        "account_id": int(group["account_id"].iloc[0]) if scope_type == "account" and group["account_id"].nunique() == 1 else None,
        "category_id": int(group["category_id"].dropna().iloc[0]) if scope_type == "category" and group["category_id"].notna().any() else None,
        "sample_count": int(len(group)),
        "periodic_score": float(payload["periodic"].get("score", 0.0)),
        "spontaneous_score": float(payload["spontaneous"].get("score", 0.0)),
        "distributional_score": float(payload["distributional"].get("distributional_score", 0.0)),
        "payload": payload,
    }
