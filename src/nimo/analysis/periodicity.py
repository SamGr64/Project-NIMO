from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd


def detect_periodicity(frame: pd.DataFrame) -> dict[str, Any]:
    """Describe recurring timing without assuming one transaction per period."""
    if frame.empty:
        return _empty_result()
    dates = pd.to_datetime(frame["booking_date"]).sort_values()
    count = int(len(dates))
    start = dates.min()
    end = dates.max()
    total_days = max(1, int((end - start).days) + 1)
    total_weeks = max(1.0, total_days / 7.0)
    total_months = max(1, len(pd.period_range(start=start, end=end, freq="M")))
    total_years = max(1.0, total_days / 365.2425)

    weekday_counts = dates.dt.weekday.value_counts().reindex(range(7), fill_value=0).astype(float)
    weekday_probabilities = (weekday_counts / max(1.0, weekday_counts.sum())).to_numpy()
    dominant_weekday = int(np.argmax(weekday_probabilities))
    dominant_weekday_share = float(weekday_probabilities[dominant_weekday])
    weekday_bias = float(max(0.0, (dominant_weekday_share - 1.0 / 7.0) / (6.0 / 7.0)))

    months = dates.dt.to_period("M")
    active_months = int(months.nunique())
    month_coverage = float(active_months / total_months)
    events_per_active_month = float(count / max(1, active_months))
    day_values = dates.dt.day.to_numpy(dtype=float)
    day_median = float(np.median(day_values))
    day_mad = float(np.median(np.abs(day_values - day_median)))
    monthly_single_event_factor = float(min(1.0, 1.5 / max(1.0, events_per_active_month)))
    monthly_timing = float(math.exp(-day_mad / 4.5))
    monthly_score = month_coverage * monthly_timing * monthly_single_event_factor

    active_weeks = int(dates.dt.to_period("W-MON").nunique())
    week_coverage = float(min(1.0, active_weeks / total_weeks))
    weekly_score = float(min(1.0, 0.55 * week_coverage + 0.75 * weekday_bias))

    month_of_year = dates.dt.month.value_counts().reindex(range(1, 13), fill_value=0).astype(float)
    month_probabilities = (month_of_year / max(1.0, month_of_year.sum())).to_numpy()
    dominant_month = int(np.argmax(month_probabilities)) + 1
    dominant_month_share = float(month_probabilities[dominant_month - 1])
    annual_concentration = float(max(0.0, (dominant_month_share - 1.0 / 12.0) / (11.0 / 12.0)))
    annual_score = float(min(1.0, annual_concentration * min(1.0, total_years / 2.0)))

    magnitudes = np.abs(pd.to_numeric(frame["amount"], errors="coerce").dropna().to_numpy())
    mean_amount = float(np.mean(magnitudes)) if len(magnitudes) else 0.0
    std_amount = float(np.std(magnitudes, ddof=1)) if len(magnitudes) > 1 else 0.0
    amount_cv = float(std_amount / mean_amount) if mean_amount > 0 else 0.0
    amount_stability = float(1.0 / (1.0 + amount_cv))

    cadence_scores = {
        "weekly": weekly_score,
        "monthly": float(monthly_score),
        "yearly": annual_score,
    }
    cadence = max(cadence_scores, key=cadence_scores.get)
    score = float(max(cadence_scores.values()))
    if score < 0.25:
        cadence = "irregular"

    intervals = dates.diff().dt.days.dropna().to_numpy(dtype=float)
    return {
        "score": round(score, 6),
        "cadence": cadence,
        "cadence_scores": {key: round(value, 6) for key, value in cadence_scores.items()},
        "frequency": {
            "per_week": round(count / total_weeks, 6),
            "per_month": round(count / total_months, 6),
            "per_year": round(count / total_years, 6),
        },
        "weekly": {
            "dominant_weekday": dominant_weekday,
            "dominant_weekday_name": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][dominant_weekday],
            "dominant_share": round(dominant_weekday_share, 6),
            "weekday_bias": round(weekday_bias, 6),
            "probabilities": [round(float(value), 6) for value in weekday_probabilities],
        },
        "monthly": {
            "coverage": round(month_coverage, 6),
            "events_per_active_month": round(events_per_active_month, 6),
            "typical_day": round(day_median, 2),
            "day_mad": round(day_mad, 4),
        },
        "yearly": {
            "dominant_month": dominant_month,
            "dominant_share": round(dominant_month_share, 6),
            "probabilities": [round(float(value), 6) for value in month_probabilities],
        },
        "amount_stability": round(amount_stability, 6),
        "interval_days": {
            "median": None if len(intervals) == 0 else round(float(np.median(intervals)), 4),
            "mad": None if len(intervals) == 0 else round(float(np.median(np.abs(intervals - np.median(intervals)))), 4),
        },
    }


def _empty_result() -> dict[str, Any]:
    return {
        "score": 0.0,
        "cadence": "insufficient_data",
        "cadence_scores": {"weekly": 0.0, "monthly": 0.0, "yearly": 0.0},
        "frequency": {"per_week": 0.0, "per_month": 0.0, "per_year": 0.0},
        "weekly": {},
        "monthly": {},
        "yearly": {},
        "amount_stability": 0.0,
        "interval_days": {"median": None, "mad": None},
    }
