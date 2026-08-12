from __future__ import annotations

from datetime import date


def inflation_factor(event_date: date, start_date: date, annual_rate: float) -> float:
    years = max(0.0, (event_date - start_date).days / 365.2425)
    return float((1.0 + annual_rate) ** years)
