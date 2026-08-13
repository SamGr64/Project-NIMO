from __future__ import annotations

from typing import Any


def infer_archetype(*, overview: dict[str, Any], behaviour_map: dict[str, Any]) -> dict[str, Any]:
    savings_rate = overview.get("savings_rate")
    income_cv = float(behaviour_map.get("global", {}).get("income", {}).get("monthly_cv", 1.0))
    weekend_bias = float(behaviour_map.get("global", {}).get("weekend_spend_share", 0.0))
    spontaneous_rate = float(behaviour_map.get("global", {}).get("spontaneous_transaction_rate", 0.0))

    income_label = "stable-income" if income_cv < 0.12 else "variable-income" if income_cv > 0.35 else "moderately-variable-income"
    if savings_rate is None:
        saving_label = "unresolved-saver"
    elif savings_rate >= 0.25:
        saving_label = "high saver"
    elif savings_rate >= 0.10:
        saving_label = "moderate saver"
    elif savings_rate >= 0:
        saving_label = "low saver"
    else:
        saving_label = "cash-flow pressured"
    timing_label = "weekend discretionary spender" if weekend_bias >= 0.38 else "evenly timed spender"
    spontaneity_label = "high-spontaneity" if spontaneous_rate >= 0.08 else "low-spontaneity" if spontaneous_rate < 0.025 else "moderate-spontaneity"
    confidence_parts = [
        min(1.0, float(behaviour_map.get("metadata", {}).get("history_months", 0)) / 12.0),
        min(1.0, float(behaviour_map.get("metadata", {}).get("transaction_count", 0)) / 250.0),
        0.8 if savings_rate is not None else 0.4,
    ]
    confidence = sum(confidence_parts) / len(confidence_parts)
    return {
        "label": f"{income_label}, {saving_label}, {timing_label}",
        "short_label": f"{saving_label.title()} / {spontaneity_label.title()}",
        "confidence": round(float(confidence), 6),
        "dimensions": {
            "income_stability": income_label,
            "saving": saving_label,
            "timing": timing_label,
            "spontaneity": spontaneity_label,
        },
        "explanation": "This descriptive label summarises the inferred behavioural map; it is not a financial risk classification or recommendation.",
    }
